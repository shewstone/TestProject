"""Drop-directory watcher (T7, docs/tickets/T7-drop-directory-watcher.md).

Always-on polling loop: files dropped into the watch directory are hashed,
guarded against duplicates, parsed, chunked, and — when an LLM key is
configured — extracted into episodes, embedded, and composed into arc
instances. Every lifecycle transition lands on a SourceDocument row, which
is what the dashboard (T8) renders as the processing queue.

Polling, not inotify: dependency-free, and it works identically on Linux,
macOS bind mounts, and CI.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from narrative_engine.logging_config import get_logger
from narrative_engine.models import SourceDocument, SourceDocumentStatus
from narrative_engine.storage.repositories import (
    EpisodeRepository,
    SourceDocumentRepository,
)

logger = get_logger(__name__)

IGNORED_SUFFIXES = {".part", ".tmp", ".crdownload", ".swp"}


def llm_configured() -> bool:
    """Extraction only runs when a model key is actually available; without
    one, files still ingest and the row says extraction_ran=False —
    visible degradation, never a silent skip."""
    return any(
        os.getenv(name)
        for name in ("NE_LLM_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")
    )


@dataclass
class WatcherConfig:
    watch_dir: Path
    interval_seconds: float = 3.0
    # Files must be untouched this long before pickup, so half-copied
    # files are never processed.
    settle_seconds: float = 2.0

    @classmethod
    def from_env(cls) -> "WatcherConfig":
        return cls(
            watch_dir=Path(os.getenv("NE_WATCH_DIR", "data/raw")),
            interval_seconds=float(os.getenv("NE_WATCH_INTERVAL", "3.0")),
            settle_seconds=float(os.getenv("NE_WATCH_SETTLE", "2.0")),
        )


class DocumentProcessor:
    """Processes one dropped file end-to-end. Collaborators are injectable
    so tests never need a model download or an API key."""

    def __init__(self, extractor=None, embedder=None) -> None:
        self._extractor = extractor
        self._embedder = embedder

    def _get_extractor(self):
        if self._extractor is None and llm_configured():
            from narrative_engine.extraction.pipeline import ExtractionOrchestrator

            self._extractor = ExtractionOrchestrator()
        return self._extractor

    def _get_embedder(self):
        if self._embedder is None:
            from narrative_engine.retrieval.embeddings import EmbeddingGenerator

            self._embedder = EmbeddingGenerator()
        return self._embedder

    async def process_file(
        self, session: AsyncSession, path: Path
    ) -> Optional[SourceDocument]:
        """Hash, dedupe-guard, and process one file. Returns the document
        row, or None when this (hash, filename) was already recorded."""
        repo = SourceDocumentRepository(session)

        raw = path.read_bytes()
        content_hash = hashlib.sha256(raw).hexdigest()

        if await repo.has_row_for(content_hash, path.name):
            return None  # already recorded (this or a previous run)

        original = await repo.get_original_by_hash(content_hash)
        if original is not None:
            document = SourceDocument(
                filename=path.name,
                content_hash=content_hash,
                size_bytes=len(raw),
                status=SourceDocumentStatus.DUPLICATE,
                duplicate_of=original.id,
                error=f"Same content as {original.filename!r}; not reprocessed",
            )
            await repo.create(document)
            logger.info(
                "duplicate_source_rejected",
                filename=path.name,
                duplicate_of=original.filename,
            )
            return document

        document = SourceDocument(
            filename=path.name,
            content_hash=content_hash,
            size_bytes=len(raw),
        )
        await repo.create(document)

        document.status = SourceDocumentStatus.PROCESSING
        await repo.update(document)
        # Commit checkpoints so the dashboard's polling session sees status
        # transitions and per-chunk progress DURING long LLM runs, not just
        # at the end of the scan (READ COMMITTED hides uncommitted flushes).
        await session.commit()

        try:
            await self._run_pipeline(session, path, document, repo)
            document.status = SourceDocumentStatus.COMPLETED
        except Exception as exc:  # one bad file must not stop the loop
            logger.error("document_processing_failed", filename=path.name, error=str(exc))
            document.status = SourceDocumentStatus.FAILED
            document.error = str(exc)

        await repo.update(document)
        await session.commit()
        return document

    async def _run_pipeline(
        self,
        session: AsyncSession,
        path: Path,
        document: SourceDocument,
        repo: SourceDocumentRepository,
    ) -> None:
        from narrative_engine.ingestion.chunker import SmartChunker
        from narrative_engine.ingestion.parsers import get_parser

        parser = get_parser(path)
        if parser is None:
            raise ValueError(f"No parser for file type: {path.suffix!r}")

        parsed = parser.parse(path)
        chunks = SmartChunker().chunk_document(parsed)
        document.chunks_created = len(chunks)
        await repo.update(document)
        await session.commit()  # total chunk count visible immediately

        extractor = self._get_extractor()
        if extractor is None:
            document.extraction_ran = False
            return

        episode_repo = EpisodeRepository(session)
        embedder = self._get_embedder()
        arc_types_seen = set()

        for chunk in chunks:
            result = await extractor.process_text(
                text=chunk.content,
                source_chunk_id=chunk.chunk_id,
                session=session,
            )
            for episode in result.episodes:
                await episode_repo.update_embedding(
                    episode.id,
                    embedder.generate_surface_embedding(episode),
                    kind="surface",
                )
                await episode_repo.update_embedding(
                    episode.id,
                    embedder.generate_structural_embedding(episode),
                    kind="structural",
                )
                if episode.arc_type:
                    arc_types_seen.add(episode.arc_type)
            document.episodes_created += len(result.episodes)
            document.chunks_processed += 1
            # Per-chunk checkpoint: progress survives a crash mid-book and
            # the dashboard renders it live. Also makes extracted episodes
            # durable as they land instead of all-or-nothing at file end.
            await repo.update(document)
            await session.commit()

        # Composition pass: stitch the new episodes (plus any existing
        # same-scope ones) into arc instances the dashboard can render.
        if arc_types_seen:
            from narrative_engine.composition.pipeline import CompositionPipeline

            composer = CompositionPipeline(session)
            for arc_type in arc_types_seen:
                instances = await composer.compose_arc_instances(arc_type)
                for instance in instances:
                    await composer.persist_instance(instance, arc_type)

        document.extraction_ran = True


def _settled_files(watch_dir: Path, settle_seconds: float) -> list[Path]:
    if not watch_dir.exists():
        return []
    now = time.time()
    files = []
    for path in sorted(watch_dir.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() in IGNORED_SUFFIXES:
            continue
        if now - path.stat().st_mtime < settle_seconds:
            continue  # still being copied
        files.append(path)
    return files


async def scan_once(
    session: AsyncSession,
    config: WatcherConfig,
    processor: DocumentProcessor,
) -> list[SourceDocument]:
    """One pass over the watch directory. Returns rows touched this scan."""
    touched = []
    for path in _settled_files(config.watch_dir, config.settle_seconds):
        try:
            document = await processor.process_file(session, path)
        except Exception as exc:  # unreadable file etc. — keep scanning
            logger.error("watcher_scan_error", path=str(path), error=str(exc))
            continue
        if document is not None:
            touched.append(document)
    return touched


async def watch_loop(config: Optional[WatcherConfig] = None) -> None:
    """The always-on loop (run as an asyncio task by the API lifespan)."""
    from narrative_engine.storage.database import db_manager

    config = config or WatcherConfig.from_env()
    processor = DocumentProcessor()
    logger.info(
        "watcher_started",
        watch_dir=str(config.watch_dir),
        interval=config.interval_seconds,
        llm_configured=llm_configured(),
    )
    while True:
        try:
            async with db_manager.session() as session:
                touched = await scan_once(session, config, processor)
            if touched:
                logger.info("watcher_scan_complete", processed=len(touched))
        except asyncio.CancelledError:
            logger.info("watcher_stopped")
            raise
        except Exception as exc:  # DB hiccup etc. — the loop survives
            logger.error("watcher_loop_error", error=str(exc))
        await asyncio.sleep(config.interval_seconds)
