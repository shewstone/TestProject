"""Composition pipeline for building Arc Instances from episodes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from narrative_engine.composition.arc_instance import (
    ArcInstance,
    CompositionStatus,
    PhaseCoverage,
)
from narrative_engine.models import ArcPhase, ArcType, Episode
from narrative_engine.storage.orm_models import EpisodeORM


@dataclass
class CompositionConfig:
    """Configuration for the composition pipeline."""

    # Temporal clustering parameters
    temporal_gap_threshold: timedelta = timedelta(days=365)  # Max gap between episodes
    min_episodes_per_cluster: int = 2

    # Phase matching parameters
    phase_confidence_threshold: float = 0.5
    allow_phase_gaps: bool = True

    # Coverage thresholds
    min_coverage_per_phase: float = 0.3
    complete_coverage_threshold: float = 0.8


class CompositionPipeline:
    """Pipeline for composing Arc Instances from extracted episodes.

    This is the key innovation: stitching phase-adjacent episodes
    across sources to build concrete arc unfoldings.

    Example:
        Book 1 covers phases 1-2 of HUBRIS_NEMESIS
        Book 2 covers phases 3-5 of HUBRIS_NEMESIS
        CompositionPipeline creates unified Arc Instance
    """

    def __init__(
        self,
        session: AsyncSession,
        config: Optional[CompositionConfig] = None,
    ):
        self.session = session
        self.config = config or CompositionConfig()

    async def compose_arc_instances(
        self,
        arc_type: ArcType,
        expected_phases: Optional[List[ArcPhase]] = None,
    ) -> List[ArcInstance]:
        """Build Arc Instances for a given arc type.

        Args:
            arc_type: The arc type to compose instances for
            expected_phases: Expected phases in order (if known)

        Returns:
            List of composed Arc Instances
        """
        # Get all episodes of this arc type
        episodes = await self._get_episodes_by_arc(arc_type)

        if not episodes:
            return []

        # Cluster episodes by temporal proximity
        clusters = self._cluster_by_temporal_proximity(episodes)

        # Build Arc Instance for each cluster
        instances = []
        for cluster in clusters:
            instance = await self._build_instance(
                arc_type, cluster, expected_phases
            )
            if instance:
                instances.append(instance)

        return instances

    async def _get_episodes_by_arc(self, arc_type: ArcType) -> Sequence[EpisodeORM]:
        """Fetch all episodes of a given arc type."""
        result = await self.session.execute(
            select(EpisodeORM)
            .where(EpisodeORM.arc_type == arc_type)
            .options(selectinload(EpisodeORM.source_passages))
            .order_by(EpisodeORM.start_date)
        )
        return result.scalars().unique().all()

    def _cluster_by_temporal_proximity(
        self, episodes: Sequence[EpisodeORM]
    ) -> List[List[EpisodeORM]]:
        """Cluster episodes that are temporally close.

        Episodes within temporal_gap_threshold form a cluster.
        """
        if not episodes:
            return []

        # Sort by start date
        sorted_eps = sorted(
            [e for e in episodes if e.start_date],
            key=lambda e: e.start_date or datetime.min,
        )

        clusters: List[List[EpisodeORM]] = []
        current_cluster: List[EpisodeORM] = []

        for episode in sorted_eps:
            if not current_cluster:
                current_cluster = [episode]
            else:
                last_episode = current_cluster[-1]
                gap = episode.start_date - last_episode.end_date

                if gap <= self.config.temporal_gap_threshold:
                    current_cluster.append(episode)
                else:
                    if len(current_cluster) >= self.config.min_episodes_per_cluster:
                        clusters.append(current_cluster)
                    current_cluster = [episode]

        # Don't forget the last cluster
        if len(current_cluster) >= self.config.min_episodes_per_cluster:
            clusters.append(current_cluster)

        return clusters

    async def _build_instance(
        self,
        arc_type: ArcType,
        cluster: List[EpisodeORM],
        expected_phases: Optional[List[ArcPhase]],
    ) -> Optional[ArcInstance]:
        """Build an Arc Instance from a cluster of episodes."""
        if not cluster:
            return None

        # Generate canonical name
        first_ep = cluster[0]
        last_ep = cluster[-1]

        location = first_ep.location or "Unknown Location"
        start_year = first_ep.start_date.year if first_ep.start_date else "?"
        end_year = last_ep.end_date.year if last_ep.end_date else "?"

        canonical_name = f"{arc_type.value}, {location}, {start_year}–{end_year}"

        instance = ArcInstance(
            arc_type=arc_type,
            canonical_name=canonical_name,
            start_date=first_ep.start_date,
            end_date=last_ep.end_date,
        )

        # Add episodes to phases
        for episode in cluster:
            if episode.arc_phase:
                # Get source IDs from episode.extracted_from (stored on Episode model)
                source_ids = episode.extracted_from if episode.extracted_from else ["unknown"]
                source_id = source_ids[0] if source_ids else "unknown"

                instance.add_episode_to_phase(
                    phase=episode.arc_phase,
                    episode_id=episode.id,
                    source_id=source_id,
                    confidence=episode.phase_confidence or 0.5,
                    date=episode.start_date,
                )

                # Track source coverage
                for sid in source_ids:
                    instance.source_coverage[sid] = instance.source_coverage.get(
                        sid, 0.0
                    ) + (1.0 / len(cluster))

        # Identify gaps
        if expected_phases:
            instance.identify_gaps(expected_phases)
        else:
            # Infer expected phases from arc type
            inferred_phases = self._infer_expected_phases(arc_type)
            instance.identify_gaps(inferred_phases)

        # Update status
        instance.update_status()

        return instance

    def _infer_expected_phases(self, arc_type: ArcType) -> List[ArcPhase]:
        """Infer expected phases from arc type.

        This would ideally come from ArcDefinition, but for now
        we use sensible defaults.
        """
        # Financial/economic arcs
        if arc_type == ArcType.CREDIT_BOOM_AND_BUST:
            return [
                ArcPhase.BOOM,
                ArcPhase.EUPHORIA,
                ArcPhase.DISTRESS,
                ArcPhase.PANIC,
                ArcPhase.REVULSION,
            ]
        # Generic narrative arcs
        elif arc_type in [
            ArcType.RISE_AND_OVEREXTENSION,
            ArcType.HUBRIS_NEMESIS,
        ]:
            return [
                ArcPhase.SETUP,
                ArcPhase.RISING_ACTION,
                ArcPhase.CLIMAX,
                ArcPhase.FALLING_ACTION,
                ArcPhase.RESOLUTION,
            ]
        # Default: all phases
        else:
            return list(ArcPhase)

    async def stitch_across_sources(
        self,
        instance: ArcInstance,
        gap_phases: List[ArcPhase],
    ) -> ArcInstance:
        """Attempt to fill gaps by searching other sources.

        This is the key "composition" step - if Book 1 has phases 1-2
        and Book 2 has phases 3-5, stitch them together.
        """
        for phase in gap_phases:
            # Query for episodes of this phase in same time period
            candidates = await self._find_gap_fillers(instance, phase)

            for candidate in candidates:
                source_ids = [
                    sp.work_id
                    for sp in candidate.source_passages
                    if hasattr(sp, "work_id")
                ]
                source_id = source_ids[0] if source_ids else "unknown"

                instance.add_episode_to_phase(
                    phase=phase,
                    episode_id=candidate.id,
                    source_id=source_id,
                    confidence=candidate.phase_confidence or 0.5,
                    date=candidate.start_date,
                )

        # Re-evaluate gaps
        instance.identify_gaps(list(instance.phases.keys()))
        instance.update_status()

        return instance

    async def _find_gap_fillers(
        self, instance: ArcInstance, phase: ArcPhase
    ) -> Sequence[EpisodeORM]:
        """Find episodes that could fill a gap in an Arc Instance."""
        if not instance.start_date or not instance.end_date:
            return []

        # Look for episodes of the same arc type, in the time window
        buffer = timedelta(days=365 * 2)  # 2 year buffer

        result = await self.session.execute(
            select(EpisodeORM)
            .where(EpisodeORM.arc_type == instance.arc_type)
            .where(EpisodeORM.arc_phase == phase)
            .where(EpisodeORM.start_date >= instance.start_date - buffer)
            .where(EpisodeORM.end_date <= instance.end_date + buffer)
            .order_by(EpisodeORM.phase_confidence.desc())
            .limit(5)
        )

        return result.scalars().all()
