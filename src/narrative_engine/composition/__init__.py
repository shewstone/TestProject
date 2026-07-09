"""Composition layer for building Arc Instances from episodes."""

from narrative_engine.composition.arc_instance import ArcInstance, CompositionStatus
from narrative_engine.composition.identity import (
    ArcIdentityResolver,
    DisambiguationEngine,
    IdentityScore,
)
from narrative_engine.composition.pipeline import (
    CompositionConfig,
    CompositionPipeline,
    compose_arc_instances_from_episodes,
)

__all__ = [
    "ArcIdentityResolver",
    "ArcInstance",
    "CompositionConfig",
    "CompositionPipeline",
    "CompositionStatus",
    "DisambiguationEngine",
    "IdentityScore",
    "compose_arc_instances_from_episodes",
]
