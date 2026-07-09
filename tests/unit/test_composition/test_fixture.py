"""Composition fixture as a regression gate (design doc Sec 6.6).

Runs the real composition algorithm (compose_arc_instances_from_episodes,
Sec 6.2 stage 6) against the hand-built fixture cases -- including the
1907-panic-vs-1920s-boom near-miss decoy -- and asserts it recovers the
positive case as one instance and keeps the negative decoy split. This is
what the doc means by the fixture "blocking pipeline-version upgrades":
it must run against the actual pipeline, not a parallel mock.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "fixtures"))

from composition_fixture import CompositionFixture, validate_composition_pipeline  # noqa: E402

from narrative_engine.composition import compose_arc_instances_from_episodes  # noqa: E402


async def _real_pipeline(episodes):
    """Adapter: the fixture harness calls pipeline_func(episodes) and
    expects a list of instances back. Every case in the fixture uses a
    single arc_type, so it's safe to key off the first episode's.
    """
    if not episodes:
        return []
    return compose_arc_instances_from_episodes(episodes, arc_type=episodes[0].arc_type)


class TestCompositionFixture:
    def test_positive_cases_recover_as_single_instance(self):
        fixture = CompositionFixture()
        for episodes, description in fixture.get_positive_cases():
            instances = compose_arc_instances_from_episodes(episodes, arc_type=episodes[0].arc_type)
            assert len(instances) == 1, f"{description}: expected 1 instance, got {len(instances)}"

    def test_negative_decoys_stay_split(self):
        fixture = CompositionFixture()
        for episodes, description, failure_mode in fixture.get_negative_cases():
            instances = compose_arc_instances_from_episodes(episodes, arc_type=episodes[0].arc_type)
            assert len(instances) >= 2, (
                f"{description}: over-merged into {len(instances)} instance(s) "
                f"(false-merge mode: {failure_mode})"
            )

    @pytest.mark.asyncio
    async def test_fixture_harness_passes_against_real_pipeline(self):
        """End-to-end check using the fixture's own pass/fail accounting,
        against the real pipeline rather than a mock."""
        results = await validate_composition_pipeline(_real_pipeline, verbose=False)

        assert results["positive_passed"] == results["positive_total"], results["recommendations"]
        assert results["negative_passed"] == results["negative_total"], results["recommendations"]
