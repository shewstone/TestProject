"""Tests for the pure, DB-free composition algorithm.

Covers the design doc Sec 6.2 stage 6 staged pipeline directly, plus the
same positive/negative cases as the composition fixture (Sec 6.6) --
duplicated here as fast unit tests, with the fixture-level integration
test added separately (test_fixture.py) as the actual regression gate.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from narrative_engine.composition import compose_arc_instances_from_episodes
from narrative_engine.composition.pipeline import _cluster_within_scope
from narrative_engine.composition.identity import ArcIdentityResolver
from narrative_engine.models import ArcPhase, ArcType, CycleScale, Episode


def _episode(**overrides) -> Episode:
    defaults = dict(
        id=uuid4(),
        title="Episode",
        summary="Summary",
        arc_type=ArcType.CREDIT_BOOM_AND_BUST,
        scope_id="us_national",
    )
    defaults.update(overrides)
    return Episode(**defaults)


class TestScopePartition:
    """Stage 1: hard filter, episodes in different scopes never compare."""

    def test_different_scopes_never_merge_even_if_otherwise_identical(self):
        a = _episode(
            start_date=datetime(1929, 1, 1),
            end_date=datetime(1929, 2, 1),
            arc_phase=ArcPhase.BOOM,
            scope_id="us_national",
        )
        b = _episode(
            start_date=datetime(1929, 2, 1),
            end_date=datetime(1929, 3, 1),
            arc_phase=ArcPhase.EUPHORIA,
            scope_id="uk_national",
        )

        instances = compose_arc_instances_from_episodes([a, b], arc_type=ArcType.CREDIT_BOOM_AND_BUST)

        assert len(instances) == 2
        assert {i.canonical_name for i in instances} != set()

    def test_none_scope_only_merges_with_none_scope(self):
        a = _episode(
            start_date=datetime(1929, 1, 1),
            end_date=datetime(1929, 2, 1),
            arc_phase=ArcPhase.BOOM,
            scope_id=None,
        )
        b = _episode(
            start_date=datetime(1929, 2, 1),
            end_date=datetime(1929, 3, 1),
            arc_phase=ArcPhase.EUPHORIA,
            scope_id="us_national",
        )

        instances = compose_arc_instances_from_episodes([a, b], arc_type=ArcType.CREDIT_BOOM_AND_BUST)

        assert len(instances) == 2


class TestTemporalGate:
    """Stage 4: per-scale gap threshold, hard reject beyond 2x threshold."""

    def test_episodic_scale_rejects_gap_beyond_threshold(self):
        a = _episode(
            start_date=datetime(1907, 10, 1),
            end_date=datetime(1907, 11, 1),
            arc_phase=ArcPhase.PANIC,
        )
        b = _episode(
            start_date=datetime(1922, 1, 1),
            end_date=datetime(1927, 1, 1),
            arc_phase=ArcPhase.BOOM,
        )

        instances = compose_arc_instances_from_episodes(
            [a, b], arc_type=ArcType.CREDIT_BOOM_AND_BUST, scale=CycleScale.EPISODIC
        )

        assert len(instances) == 2

    def test_civilizational_scale_is_more_permissive_than_episodic(self):
        # Same 14-year gap that fails at episodic (2y) scale should pass
        # at civilizational (40y) scale.
        a = _episode(
            start_date=datetime(1907, 10, 1),
            end_date=datetime(1907, 11, 1),
            arc_phase=ArcPhase.BOOM,
        )
        b = _episode(
            start_date=datetime(1922, 1, 1),
            end_date=datetime(1927, 1, 1),
            arc_phase=ArcPhase.EUPHORIA,
        )

        instances = compose_arc_instances_from_episodes(
            [a, b], arc_type=ArcType.CREDIT_BOOM_AND_BUST, scale=CycleScale.CIVILIZATIONAL
        )

        assert len(instances) == 1


class TestPhaseSequenceGate:
    """Stage 5: out-of-order phases hard-reject the merge."""

    def test_out_of_order_phases_split(self):
        # PANIC then BOOM (going backwards) should not merge even though
        # temporally adjacent and same scope/arc_type.
        a = _episode(
            start_date=datetime(1929, 1, 1),
            end_date=datetime(1929, 2, 1),
            arc_phase=ArcPhase.PANIC,
        )
        b = _episode(
            start_date=datetime(1929, 3, 1),
            end_date=datetime(1929, 4, 1),
            arc_phase=ArcPhase.BOOM,
        )

        instances = compose_arc_instances_from_episodes([a, b], arc_type=ArcType.CREDIT_BOOM_AND_BUST)

        assert len(instances) == 2


class TestArcTypeAgreement:
    def test_different_arc_types_are_filtered_before_clustering(self):
        a = _episode(
            start_date=datetime(1929, 1, 1),
            end_date=datetime(1929, 2, 1),
            arc_phase=ArcPhase.BOOM,
            arc_type=ArcType.CREDIT_BOOM_AND_BUST,
        )
        b = _episode(
            start_date=datetime(1929, 2, 1),
            end_date=datetime(1929, 3, 1),
            arc_phase=ArcPhase.RISING_ACTION,
            arc_type=ArcType.HUBRIS_NEMESIS,
        )

        # compose_arc_instances_from_episodes filters to the requested
        # arc_type up front, so the HUBRIS_NEMESIS episode is excluded
        # entirely from a CREDIT_BOOM_AND_BUST composition run.
        instances = compose_arc_instances_from_episodes([a, b], arc_type=ArcType.CREDIT_BOOM_AND_BUST)

        assert len(instances) == 1
        assert instances[0].phases.get(ArcPhase.BOOM) is not None


class TestNoSilentDrops:
    def test_singleton_episode_still_produces_an_instance(self):
        a = _episode(
            start_date=datetime(1907, 10, 1),
            end_date=datetime(1907, 11, 1),
            arc_phase=ArcPhase.PANIC,
        )

        instances = compose_arc_instances_from_episodes([a], arc_type=ArcType.CREDIT_BOOM_AND_BUST)

        assert len(instances) == 1
        assert a.id in instances[0].phases[ArcPhase.PANIC].episode_ids


class TestClusterWithinScope:
    """Direct tests of the sequential merge helper."""

    def test_empty_input_returns_no_clusters(self):
        resolver = ArcIdentityResolver()
        assert _cluster_within_scope([], resolver, CycleScale.EPISODIC) == []
