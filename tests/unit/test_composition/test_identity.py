"""Regression tests for ArcIdentityResolver / DisambiguationEngine bug fixes.

Both bugs here were latent AttributeError/NameError crashes: the code paths
were never exercised (find_candidate_matches referenced a non-existent
`self.temporal_threshold` singular attribute; detect_false_merge_risk
referenced an undefined `avg_continuity` name). These tests just need to
reach the previously-crashing lines without raising.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from narrative_engine.composition.identity import (
    ArcIdentityResolver,
    DisambiguationEngine,
)
from narrative_engine.models import Actor, ArcPhase, ArcType, Episode


def _episode(**overrides) -> Episode:
    defaults = dict(
        id=uuid4(),
        title="Episode",
        summary="Summary",
        arc_type=ArcType.CREDIT_BOOM_AND_BUST,
    )
    defaults.update(overrides)
    return Episode(**defaults)


class FakeAsyncSession:
    """Minimal async session stand-in: returns no rows for any execute()."""

    async def execute(self, _query):
        class _Result:
            def scalars(self):
                return self

            def all(self):
                return []

        return _Result()


class TestFindCandidateMatches:
    """find_candidate_matches previously crashed with AttributeError on
    `self.temporal_threshold` (singular) which doesn't exist on the resolver.
    """

    @pytest.mark.asyncio
    async def test_does_not_raise_with_end_date(self):
        resolver = ArcIdentityResolver()
        episode = _episode(end_date=datetime(1929, 10, 24))

        matches = await resolver.find_candidate_matches(
            session=FakeAsyncSession(),
            episode=episode,
            arc_type=ArcType.CREDIT_BOOM_AND_BUST,
        )

        assert matches == []


class TestDetectFalseMergeRisk:
    """detect_false_merge_risk previously crashed with NameError on
    `avg_continuity` (undefined; should be `avg_actor_continuity`) whenever
    low actor continuity across a cluster of 3+ episodes triggered that branch.
    """

    def test_low_actor_continuity_branch_does_not_raise(self):
        resolver = ArcIdentityResolver()
        engine = DisambiguationEngine(resolver)

        # Three episodes, each with disjoint actors -> low actor continuity,
        # and len(cluster) > 2, which is what triggers the buggy branch.
        cluster = [
            _episode(
                start_date=datetime(1920, 1, 1),
                end_date=datetime(1920, 6, 1),
                actors=[Actor(name="A", role="RISING_POWER")],
            ),
            _episode(
                start_date=datetime(1921, 1, 1),
                end_date=datetime(1921, 6, 1),
                actors=[Actor(name="B", role="RISING_POWER")],
            ),
            _episode(
                start_date=datetime(1922, 1, 1),
                end_date=datetime(1922, 6, 1),
                actors=[Actor(name="C", role="RISING_POWER")],
            ),
        ]

        result = engine.detect_false_merge_risk(cluster)

        assert "actor_continuity" in result
        assert any("Low actor continuity" in r for r in result["risk_factors"])
