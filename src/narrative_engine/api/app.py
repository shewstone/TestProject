"""FastAPI app (T8, docs/tickets/T8-dashboard-and-review-ui.md).

Serves the dashboard, the processing-queue/arc-instance/review JSON
endpoints, and runs the drop-directory watcher (T7) as a lifespan task —
one always-on container.

NO AUTH: bind assumption is localhost/dev. Adding auth is a hard
precondition for any non-local deployment.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from importlib import resources
from typing import AsyncGenerator, Optional
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from narrative_engine.logging_config import get_logger
from narrative_engine.storage.orm_models import (
    CycleMembershipORM,
    CycleORM,
    EpisodeLinkORM,
    EpisodeORM,
    SourceDocumentORM,
)
from narrative_engine.storage.repositories import SourceDocumentRepository

logger = get_logger(__name__)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Session dependency; tests override this with their fixture session."""
    from narrative_engine.storage.database import db_manager

    async with db_manager.session() as session:
        yield session


class ReviewDecision(BaseModel):
    decision: str  # "approved" | "rejected"


def create_app(start_watcher: Optional[bool] = None) -> FastAPI:
    if start_watcher is None:
        start_watcher = os.getenv("NE_WATCH_ENABLED", "true").lower() == "true"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        watcher_task = None
        if start_watcher:
            from narrative_engine.watcher import watch_loop

            watcher_task = asyncio.create_task(watch_loop())
        yield
        if watcher_task:
            watcher_task.cancel()
            try:
                await watcher_task
            except asyncio.CancelledError:
                pass

    app = FastAPI(title="Narrative Engine", lifespan=lifespan)

    @app.get("/", response_class=HTMLResponse)
    async def dashboard() -> str:
        return (
            resources.files("narrative_engine.api")
            .joinpath("static/dashboard.html")
            .read_text()
        )

    @app.get("/api/health")
    async def health(session: AsyncSession = Depends(get_session)) -> dict:
        async def count(stmt):
            return (await session.execute(stmt)).scalar() or 0

        return {
            "status": "ok",
            "documents": await count(select(func.count(SourceDocumentORM.id))),
            "episodes": await count(select(func.count(EpisodeORM.id))),
            "arc_instances": await count(
                select(func.count(CycleORM.id)).where(CycleORM.is_arc_instance)
            ),
            "pending_reviews": (
                await count(
                    select(func.count(CycleMembershipORM.id)).where(
                        CycleMembershipORM.review_status == "pending"
                    )
                )
            )
            + (
                await count(
                    select(func.count(EpisodeLinkORM.id)).where(
                        EpisodeLinkORM.review_status == "pending"
                    )
                )
            ),
        }

    @app.get("/api/documents")
    async def documents(session: AsyncSession = Depends(get_session)) -> list:
        repo = SourceDocumentRepository(session)
        return [
            {
                "id": str(d.id),
                "filename": d.filename,
                "status": d.status.value,
                "size_bytes": d.size_bytes,
                "chunks_created": d.chunks_created,
                "chunks_processed": d.chunks_processed,
                "episodes_created": d.episodes_created,
                "extraction_ran": d.extraction_ran,
                "duplicate_of": str(d.duplicate_of) if d.duplicate_of else None,
                "error": d.error,
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat(),
            }
            for d in await repo.list_all()
        ]

    @app.get("/api/arc-instances")
    async def arc_instances(session: AsyncSession = Depends(get_session)) -> list:
        from narrative_engine.composition.pipeline import _infer_expected_phases
        from narrative_engine.models import ArcType

        cycles = (
            (
                await session.execute(
                    select(CycleORM)
                    .where(CycleORM.is_arc_instance)
                    .order_by(CycleORM.created_at.desc())
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )
        if not cycles:
            return []

        cycle_ids = [c.id for c in cycles]
        memberships = (
            (
                await session.execute(
                    select(CycleMembershipORM).where(
                        CycleMembershipORM.cycle_id.in_(cycle_ids)
                    )
                )
            )
            .scalars()
            .all()
        )
        episode_ids = {m.episode_id for m in memberships}
        episodes = {}
        if episode_ids:
            rows = (
                (
                    await session.execute(
                        select(EpisodeORM).where(EpisodeORM.id.in_(episode_ids))
                    )
                )
                .scalars()
                .all()
            )
            episodes = {e.id: e for e in rows}

        by_cycle: dict = {}
        for m in memberships:
            by_cycle.setdefault(m.cycle_id, []).append(m)

        payload = []
        for cycle in cycles:
            arc_value = None
            if cycle.dominant_arc_types:
                arc_value = cycle.dominant_arc_types[0]
            elif cycle.name and "," in cycle.name:
                arc_value = cycle.name.split(",")[0].strip()
            expected_phases = []
            try:
                expected_phases = [
                    p.value for p in _infer_expected_phases(ArcType(arc_value))
                ]
            except (ValueError, TypeError):
                pass

            members = []
            for m in sorted(
                by_cycle.get(cycle.id, []),
                key=lambda m: (
                    episodes[m.episode_id].start_date is None,
                    episodes[m.episode_id].start_date,
                )
                if m.episode_id in episodes
                else (True, None),
            ):
                episode = episodes.get(m.episode_id)
                if episode is None:
                    continue
                members.append(
                    {
                        "id": str(episode.id),
                        "title": episode.title,
                        "phase": episode.arc_phase.value if episode.arc_phase else None,
                        "start_date": episode.start_date.isoformat()
                        if episode.start_date
                        else None,
                        "end_date": episode.end_date.isoformat()
                        if episode.end_date
                        else None,
                        "link_status": m.link_status,
                        "review_status": m.review_status,
                        "membership_id": str(m.id),
                    }
                )

            covered = {m["phase"] for m in members if m["phase"]}
            payload.append(
                {
                    "id": str(cycle.id),
                    "name": cycle.name,
                    "arc_type": arc_value,
                    "scope_id": cycle.scope_id,
                    "start_date": cycle.start_date.isoformat() if cycle.start_date else None,
                    "end_date": cycle.end_date.isoformat() if cycle.end_date else None,
                    "expected_phases": expected_phases,
                    "covered_phases": sorted(covered),
                    "episodes": members,
                }
            )
        return payload

    @app.get("/api/review-queue")
    async def review_queue(session: AsyncSession = Depends(get_session)) -> dict:
        memberships = (
            (
                await session.execute(
                    select(CycleMembershipORM, CycleORM.name, EpisodeORM.title)
                    .join(CycleORM, CycleMembershipORM.cycle_id == CycleORM.id)
                    .join(EpisodeORM, CycleMembershipORM.episode_id == EpisodeORM.id)
                    .where(CycleMembershipORM.review_status == "pending")
                    .limit(100)
                )
            )
            .all()
        )
        links = (
            (
                await session.execute(
                    select(EpisodeLinkORM).where(EpisodeLinkORM.review_status == "pending").limit(100)
                )
            )
            .scalars()
            .all()
        )
        episode_ids = {l.source_episode_id for l in links} | {
            l.target_episode_id for l in links
        }
        titles = {}
        if episode_ids:
            rows = (
                await session.execute(
                    select(EpisodeORM.id, EpisodeORM.title).where(
                        EpisodeORM.id.in_(episode_ids)
                    )
                )
            ).all()
            titles = {row.id: row.title for row in rows}

        return {
            "memberships": [
                {
                    "id": str(m.CycleMembershipORM.id),
                    "cycle": m.name,
                    "episode": m.title,
                    "link_status": m.CycleMembershipORM.link_status,
                }
                for m in memberships
            ],
            "links": [
                {
                    "id": str(l.id),
                    "edge_kind": l.edge_kind,
                    "link_status": l.link_status,
                    "source": titles.get(l.source_episode_id, "?"),
                    "target": titles.get(l.target_episode_id, "?"),
                    "evidence": l.evidence,
                }
                for l in links
            ],
        }

    async def _apply_review(orm_row, decision: str, session: AsyncSession) -> dict:
        if decision not in ("approved", "rejected"):
            raise HTTPException(422, "decision must be 'approved' or 'rejected'")
        orm_row.review_status = decision
        await session.flush()
        await session.commit()
        return {"id": str(orm_row.id), "review_status": decision}

    @app.post("/api/documents/{document_id}/retry")
    async def retry_document(
        document_id: UUID, session: AsyncSession = Depends(get_session)
    ) -> dict:
        """Clear a row so the watcher re-picks the file next scan.

        Retryable: failed rows, and completed rows whose extraction never
        ran (ingested before an LLM key was configured — re-picking them is
        exactly the "key arrived later" path). Fully-extracted work is not
        silently redone, and duplicates were rejected on purpose.
        """
        row = await session.get(SourceDocumentORM, document_id)
        if row is None:
            raise HTTPException(404, "document not found")
        retryable = row.status == "failed" or (
            row.status == "completed" and not row.extraction_ran
        )
        if not retryable:
            raise HTTPException(
                409,
                f"not retryable (status={row.status}, extraction_ran={row.extraction_ran})",
            )
        await session.delete(row)
        await session.flush()
        await session.commit()
        return {"id": str(document_id), "retried": True}

    @app.post("/api/review/membership/{membership_id}")
    async def review_membership(
        membership_id: UUID,
        body: ReviewDecision,
        session: AsyncSession = Depends(get_session),
    ) -> dict:
        row = await session.get(CycleMembershipORM, membership_id)
        if row is None:
            raise HTTPException(404, "membership not found")
        return await _apply_review(row, body.decision, session)

    @app.post("/api/review/link/{link_id}")
    async def review_link(
        link_id: UUID,
        body: ReviewDecision,
        session: AsyncSession = Depends(get_session),
    ) -> dict:
        row = await session.get(EpisodeLinkORM, link_id)
        if row is None:
            raise HTTPException(404, "link not found")
        return await _apply_review(row, body.decision, session)

    return app


app = create_app()
