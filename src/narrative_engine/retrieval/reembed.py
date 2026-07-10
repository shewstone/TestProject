"""Batch re-embedding job (T4): bring stale vectors to the current epoch.

Usage:
    python -m narrative_engine.retrieval.reembed [--dry-run] [--batch-size N]

Selects episodes whose surface or structural embedding epoch differs from
the current one (including NULL-epoch rows that have a vector, and rows
with no vector at all but renderable content), regenerates both embeddings
with the pinned model, and stamps the current epochs. Idempotent: a second
run selects nothing. Design refs: Sec 6.3 (re-embedding is a batch job),
Sec 11.4 (v0.7 render change requires a corpus re-embed).
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from narrative_engine.logging_config import get_logger
from narrative_engine.retrieval.epochs import (
    STRUCTURAL_EMBEDDING_EPOCH,
    SURFACE_EMBEDDING_EPOCH,
)
from narrative_engine.storage.orm_models import EpisodeORM

logger = get_logger(__name__)


def _stale_condition():
    """Rows whose vectors are missing or not from the current epochs."""
    return or_(
        EpisodeORM.structural_embedding.is_(None),
        EpisodeORM.surface_embedding.is_(None),
        EpisodeORM.structural_embedding_epoch.is_distinct_from(STRUCTURAL_EMBEDDING_EPOCH),
        EpisodeORM.surface_embedding_epoch.is_distinct_from(SURFACE_EMBEDDING_EPOCH),
    )


async def stale_fraction(session: AsyncSession) -> float:
    """Fraction of episodes not fully embedded at the current epochs.

    The eval harness refuses to run over a corpus with stale_fraction > 0:
    a backtest across mixed embedding epochs is uninterpretable.
    """
    total = (await session.execute(select(func.count(EpisodeORM.id)))).scalar() or 0
    if total == 0:
        return 0.0
    stale = (
        await session.execute(select(func.count(EpisodeORM.id)).where(_stale_condition()))
    ).scalar() or 0
    return stale / total


async def reembed_stale(
    session: AsyncSession,
    embedder=None,
    batch_size: int = 64,
    dry_run: bool = False,
) -> dict:
    """Re-embed every stale episode. Returns {"stale": n, "updated": n}.

    `embedder` is injectable for tests; defaults to the pinned
    EmbeddingGenerator. Processes in id-ordered batches so an interrupted
    run resumes by simply re-running (idempotent selection).
    """
    stale_count = (
        await session.execute(select(func.count(EpisodeORM.id)).where(_stale_condition()))
    ).scalar() or 0

    if dry_run or stale_count == 0:
        logger.info("reembed_scan", stale=stale_count, dry_run=dry_run)
        return {"stale": stale_count, "updated": 0}

    if embedder is None:
        from narrative_engine.retrieval.embeddings import EmbeddingGenerator

        embedder = EmbeddingGenerator()

    # Re-render from the Pydantic model so the render code path is the same
    # one extraction uses (single render implementation, Sec 6.2 stage 3).
    from narrative_engine.storage.repositories import EpisodeRepository

    repo = EpisodeRepository(session)
    updated = 0

    while True:
        result = await session.execute(
            select(EpisodeORM)
            .where(_stale_condition())
            .order_by(EpisodeORM.id)
            .limit(batch_size)
        )
        orm_rows = result.scalars().all()
        if not orm_rows:
            break

        for orm_row in orm_rows:
            episode = repo._from_orm(orm_row)
            orm_row.surface_embedding = embedder.generate_surface_embedding(episode)
            orm_row.surface_embedding_epoch = SURFACE_EMBEDDING_EPOCH
            orm_row.structural_embedding = embedder.generate_structural_embedding(episode)
            orm_row.structural_embedding_epoch = STRUCTURAL_EMBEDDING_EPOCH
            updated += 1

        await session.flush()

    logger.info("reembed_complete", stale=stale_count, updated=updated)
    return {"stale": stale_count, "updated": updated}


async def _main(dry_run: bool, batch_size: int) -> None:
    from narrative_engine.storage.database import db_manager

    async with db_manager.session() as session:
        fraction = await stale_fraction(session)
        result = await reembed_stale(session, batch_size=batch_size, dry_run=dry_run)
        await session.commit()
        print(
            f"stale_fraction={fraction:.3f} stale={result['stale']} "
            f"updated={result['updated']} dry_run={dry_run}"
        )


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report stale counts only")
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args(argv)
    asyncio.run(_main(args.dry_run, args.batch_size))


if __name__ == "__main__":
    main()
