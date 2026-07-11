"""Drop-directory watcher tests (T7, docs/tickets/T7-drop-directory-watcher.md)."""

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from narrative_engine.models import SourceDocument, SourceDocumentStatus
from narrative_engine.storage.repositories import (
    SOURCE_DOCUMENT_FIELDS_EXCLUDED,
    SourceDocumentRepository,
)
from narrative_engine.watcher import (
    DocumentProcessor,
    WatcherConfig,
    llm_configured,
    scan_once,
)
from tests.unit.test_roundtrip import assert_field_coverage

UTC = timezone.utc


class TestSourceDocumentRoundTrip:
    @pytest.mark.asyncio
    async def test_maximal(self, db_session):
        repo = SourceDocumentRepository(db_session)
        original = SourceDocument(filename="orig.txt", content_hash="a" * 64)
        await repo.create(original)

        document = SourceDocument(
            id=uuid4(),
            filename="kindleberger-manias.txt",
            content_hash="b" * 64,
            size_bytes=123456,
            status=SourceDocumentStatus.FAILED,
            error="parser exploded",
            chunks_created=12,
            chunks_processed=5,
            episodes_created=7,
            extraction_ran=True,
            duplicate_of=original.id,
            created_at=datetime(2026, 7, 10, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2026, 7, 10, 12, 0, 0, tzinfo=UTC),
        )
        assert_field_coverage(SourceDocument, document, SOURCE_DOCUMENT_FIELDS_EXCLUDED)

        await repo.create(document)
        fetched = await repo.get_by_id(document.id)

        assert fetched is not None
        assert fetched.model_dump() == document.model_dump()


def _write(tmp_path: Path, name: str, content: bytes, old: bool = True) -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    if old:
        # Make the file look settled (mtime in the past).
        stale = time.time() - 60
        os.utime(path, (stale, stale))
    return path


def _config(tmp_path: Path) -> WatcherConfig:
    return WatcherConfig(watch_dir=tmp_path, settle_seconds=2.0)


class TestDuplicateGuard:
    @pytest.mark.asyncio
    async def test_same_bytes_any_filename_becomes_duplicate_row(self, db_session, tmp_path):
        processor = DocumentProcessor(extractor=None)
        _write(tmp_path, "book.txt", b"the same book content")
        _write(tmp_path, "book-copy-from-other-folder.txt", b"the same book content")

        touched = await scan_once(db_session, _config(tmp_path), processor)

        by_status = {}
        for doc in touched:
            by_status.setdefault(doc.status, []).append(doc)
        assert len(by_status[SourceDocumentStatus.COMPLETED]) == 1
        assert len(by_status[SourceDocumentStatus.DUPLICATE]) == 1

        duplicate = by_status[SourceDocumentStatus.DUPLICATE][0]
        original = by_status[SourceDocumentStatus.COMPLETED][0]
        assert duplicate.duplicate_of == original.id
        assert duplicate.chunks_created == 0  # never processed

    @pytest.mark.asyncio
    async def test_rescan_does_not_rerecord(self, db_session, tmp_path):
        processor = DocumentProcessor(extractor=None)
        _write(tmp_path, "book.txt", b"content that stays in the folder")

        first = await scan_once(db_session, _config(tmp_path), processor)
        second = await scan_once(db_session, _config(tmp_path), processor)

        assert len(first) == 1
        assert second == []  # same (hash, filename): recorded once, forever

    @pytest.mark.asyncio
    async def test_different_bytes_same_name_is_not_duplicate(self, db_session, tmp_path):
        processor = DocumentProcessor(extractor=None)
        _write(tmp_path, "book.txt", b"first edition")
        first = await scan_once(db_session, _config(tmp_path), processor)

        _write(tmp_path, "book.txt", b"second edition, revised")
        second = await scan_once(db_session, _config(tmp_path), processor)

        assert first[0].status == SourceDocumentStatus.COMPLETED
        assert second[0].status == SourceDocumentStatus.COMPLETED  # new edition


class TestSettleGuard:
    @pytest.mark.asyncio
    async def test_fresh_files_are_not_picked_up(self, db_session, tmp_path):
        processor = DocumentProcessor(extractor=None)
        _write(tmp_path, "still-copying.txt", b"partial", old=False)

        touched = await scan_once(db_session, _config(tmp_path), processor)
        assert touched == []

    @pytest.mark.asyncio
    async def test_partial_suffixes_ignored(self, db_session, tmp_path):
        processor = DocumentProcessor(extractor=None)
        _write(tmp_path, "download.part", b"partial browser download")

        touched = await scan_once(db_session, _config(tmp_path), processor)
        assert touched == []


class TestFailureIsolation:
    @pytest.mark.asyncio
    async def test_unparseable_file_fails_visibly_and_loop_continues(
        self, db_session, tmp_path
    ):
        processor = DocumentProcessor(extractor=None)
        _write(tmp_path, "image.xyz", b"\x89PNG not a text format")
        _write(tmp_path, "readable.txt", b"a perfectly fine text file")

        touched = await scan_once(db_session, _config(tmp_path), processor)

        statuses = {d.filename: d.status for d in touched}
        assert statuses["image.xyz"] == SourceDocumentStatus.FAILED
        assert statuses["readable.txt"] == SourceDocumentStatus.COMPLETED
        failed = next(d for d in touched if d.filename == "image.xyz")
        assert failed.error


class FakeEmbedder:
    def generate_surface_embedding(self, episode):
        return [0.1] * 384

    def generate_structural_embedding(self, episode):
        return [0.2] * 384


class FakeExtractor:
    """Creates one real episode per chunk; optionally fails at chunk N."""

    def __init__(self, session, fail_on_call: int | None = None):
        self._session = session
        self._fail_on_call = fail_on_call
        self.calls = 0

    async def process_text(self, text, source_chunk_id, session):
        from types import SimpleNamespace

        from narrative_engine.models import Episode
        from narrative_engine.storage.repositories import EpisodeRepository

        self.calls += 1
        if self._fail_on_call is not None and self.calls == self._fail_on_call:
            raise RuntimeError("LLM exploded mid-book")
        episode = Episode(title=f"ep-{source_chunk_id}", summary="s")
        await EpisodeRepository(session).create(episode)
        return SimpleNamespace(episodes=[episode], errors=[])


def _multi_chunk_file(tmp_path: Path, name: str = "book.txt") -> Path:
    # Large enough to hard-split into several chunks under default config.
    return _write(tmp_path, name, ("word " * 30000).encode())


class TestChunkProgress:
    @pytest.mark.asyncio
    async def test_progress_counts_track_chunks(self, db_session, tmp_path):
        extractor = FakeExtractor(db_session)
        processor = DocumentProcessor(extractor=extractor, embedder=FakeEmbedder())
        _multi_chunk_file(tmp_path)

        touched = await scan_once(db_session, _config(tmp_path), processor)

        doc = touched[0]
        assert doc.status == SourceDocumentStatus.COMPLETED
        assert doc.chunks_created >= 2  # sanity: the fixture actually multi-chunks
        assert doc.chunks_processed == doc.chunks_created == extractor.calls
        assert doc.episodes_created == extractor.calls
        assert doc.extraction_ran is True

    @pytest.mark.asyncio
    async def test_partial_progress_survives_midfile_failure(self, db_session, tmp_path):
        """A crash on chunk 3 must leave chunks 1-2 committed and visible --
        the dashboard shows how far the run got, and the extracted episodes
        are durable rather than all-or-nothing."""
        extractor = FakeExtractor(db_session, fail_on_call=3)
        processor = DocumentProcessor(extractor=extractor, embedder=FakeEmbedder())
        _multi_chunk_file(tmp_path)

        touched = await scan_once(db_session, _config(tmp_path), processor)

        doc = touched[0]
        assert doc.status == SourceDocumentStatus.FAILED
        assert "LLM exploded" in doc.error
        assert doc.chunks_processed == 2
        assert doc.episodes_created == 2
        assert doc.chunks_created > doc.chunks_processed  # gap is visible


class TestExtractionGating:
    @pytest.mark.asyncio
    async def test_no_llm_key_completes_with_extraction_pending(
        self, db_session, tmp_path, monkeypatch
    ):
        for var in ("NE_LLM_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        assert not llm_configured()

        processor = DocumentProcessor()  # no injected extractor either
        _write(tmp_path, "book.txt", b"chapter one. things happened.")

        touched = await scan_once(db_session, _config(tmp_path), processor)

        assert touched[0].status == SourceDocumentStatus.COMPLETED
        assert touched[0].extraction_ran is False
        assert touched[0].chunks_created >= 1
