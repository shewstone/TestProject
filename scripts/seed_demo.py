"""Seed a demo arc instance through the REAL composition pipeline so the
dashboard has something to render (dev convenience, not fixture data)."""

import asyncio
from datetime import datetime, timezone

from narrative_engine.composition.pipeline import CompositionPipeline
from narrative_engine.models import Actor, ArcPhase, ArcType, Episode
from narrative_engine.storage.database import db_manager
from narrative_engine.storage.repositories import EpisodeRepository

UTC = timezone.utc


def beat(title, phase, start, end, source):
    return Episode(
        title=title,
        summary=f"{title} — demo beat",
        scope_id="us",
        location="United States",
        start_date=datetime(*start, tzinfo=UTC),
        end_date=datetime(*end, tzinfo=UTC),
        arc_type=ArcType.CREDIT_BOOM_AND_BUST,
        arc_phase=phase,
        phase_confidence=0.85,
        actors=[Actor(name="Wall Street", role="Financier", canonical_role="financier",
                      role_fit_confidence=0.9)],
        tension="leverage against liquidity",
        extracted_from=[source],
    )


async def main() -> None:
    episodes = [
        beat("Post-war expansion", ArcPhase.BOOM, (1922, 1, 1), (1927, 6, 1), "galbraith-1929"),
        beat("Margin-fueled euphoria", ArcPhase.EUPHORIA, (1927, 9, 1), (1929, 9, 1), "galbraith-1929"),
        beat("October crash", ArcPhase.PANIC, (1929, 10, 24), (1929, 11, 13), "kindleberger-mania"),
        beat("Liquidation and depression onset", ArcPhase.REVULSION, (1930, 1, 1), (1932, 7, 1), "ahamed-lords"),
    ]
    async with db_manager.session() as session:
        repo = EpisodeRepository(session)
        for episode in episodes:
            await repo.create(episode)

        composer = CompositionPipeline(session)
        instances = await composer.compose_arc_instances(ArcType.CREDIT_BOOM_AND_BUST)
        for instance in instances:
            cycle = await composer.persist_instance(instance, ArcType.CREDIT_BOOM_AND_BUST)
            print(f"persisted arc instance: {cycle.name} ({len(instance.phases)} phases)")


if __name__ == "__main__":
    asyncio.run(main())
