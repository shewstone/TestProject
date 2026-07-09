"""Composition layer for building Arc Instances from episodes."""

from narrative_engine.composition.arc_instance import ArcInstance, CompositionStatus
from narrative_engine.composition.identity import (
    ArcIdentityResolver,
    DisambiguationEngine,
    IdentityScore,
)
from narrative_engine.composition.pipeline import CompositionPipeline, CompositionConfig

__all__ = [
    "ArcIdentityResolver",
    "ArcInstance",
    "CompositionConfig",
    "CompositionPipeline",
    "CompositionStatus",
    "DisambiguationEngine",
    "IdentityScore",
]
