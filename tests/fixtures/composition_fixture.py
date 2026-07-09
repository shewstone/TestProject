"""Composition fixture for validating identity resolution thresholds.

Contains hand-built Arc Instances that the composition pass MUST recover,
plus deliberate near-miss decoys that it must NOT merge.

Use this to tune thresholds BEFORE deploying composition pipeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Tuple
from uuid import UUID, uuid4

from narrative_engine.models import (
    Actor,
    ArcPhase,
    ArcType,
    Episode,
)


class CompositionFixture:
    """Test fixture for Arc Instance composition validation.
    
    Each case includes:
    - Input episodes (from various "sources")
    - Expected: Should they merge into one Arc Instance?
    - Rationale: Why they should or shouldn't merge
    
    PASS criteria:
    - Recover all POSITIVE cases (merge correctly)
    - Reject all NEGATIVE cases (don't false-merge)
    - Tune thresholds until both criteria met
    """
    
    @staticmethod
    def get_positive_cases() -> List[Tuple[List[Episode], str]]:
        """Cases that SHOULD merge into single Arc Instance."""
        cases = []
        
        # Case 1: 1929 Crash across two books
        case_1929 = [
            Episode(
                id=uuid4(),
                title="1920s Economic Expansion",
                summary="Post-war boom and stock market growth",
                start_date=datetime(1922, 1, 1),
                end_date=datetime(1927, 9, 1),
                location="United States",
                scope_id="us_national",
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,
                arc_phase=ArcPhase.BOOM,
                extracted_from=["galbraith-1929.txt"],
            ),
            Episode(
                id=uuid4(),
                title="Speculative Euphoria",
                summary="Margin trading and irrational exuberance",
                start_date=datetime(1927, 9, 1),
                end_date=datetime(1929, 9, 1),
                location="New York",
                scope_id="us_national",
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,
                arc_phase=ArcPhase.EUPHORIA,
                extracted_from=["galbraith-1929.txt"],
            ),
            Episode(
                id=uuid4(),
                title="Black Tuesday and Crash",
                summary="Market panic and initial collapse",
                start_date=datetime(1929, 10, 24),
                end_date=datetime(1929, 10, 29),
                location="Wall Street",
                scope_id="us_national",
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,
                arc_phase=ArcPhase.PANIC,
                extracted_from=["kindleberger-mania.txt"],
            ),
        ]
        cases.append((case_1929, "1929 Crash: multi-book, continuous arc"))
        
        return cases
    
    @staticmethod
    def get_negative_cases() -> List[Tuple[List[Episode], str, str]]:
        """Cases that should NOT merge (deliberate near-misses)."""
        cases = []
        
        # Case N1: 1907 Panic vs 1920s Boom (same scope, close-ish time)
        panic_1907 = [
            Episode(
                id=uuid4(),
                title="1907 Bankers' Panic",
                summary="Financial crisis",
                start_date=datetime(1907, 10, 1),
                end_date=datetime(1907, 11, 1),
                location="New York",
                scope_id="us_national",
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,
                arc_phase=ArcPhase.PANIC,
                extracted_from=["bruner-carr-1907.txt"],
            ),
        ]
        
        boom_1920s = [
            Episode(
                id=uuid4(),
                title="Roaring Twenties Expansion",
                summary="Post-WWI boom",
                start_date=datetime(1922, 1, 1),
                end_date=datetime(1927, 1, 1),
                location="United States",
                scope_id="us_national",
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,
                arc_phase=ArcPhase.BOOM,
                extracted_from=["galbraith-1929.txt"],
            ),
            Episode(
                id=uuid4(),
                title="1929 Market Crash",
                summary="Great Crash begins",
                start_date=datetime(1929, 10, 24),
                end_date=datetime(1929, 10, 29),
                location="Wall Street",
                scope_id="us_national",
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,
                arc_phase=ArcPhase.PANIC,
                extracted_from=["galbraith-1929.txt"],
            ),
        ]
        
        cases.append((
            panic_1907 + boom_1920s,
            "1907 Panic vs 1920s Boom: same scope, different instances",
            "temporal_overmerge"
        ))
        
        return cases


async def validate_composition_pipeline(
    pipeline_func: Callable,
    verbose: bool = True
) -> Dict[str, Any]:
    """Run composition fixture against a pipeline implementation."""
    
    fixture = CompositionFixture()
    
    results = {
        "positive_passed": 0,
        "positive_total": 0,
        "negative_passed": 0,
        "negative_total": 0,
        "recommendations": [],
    }
    
    # Test positive cases (should merge)
    for episodes, description in fixture.get_positive_cases():
        results["positive_total"] += 1
        instances = await pipeline_func(episodes)
        
        if len(instances) == 1:
            results["positive_passed"] += 1
            if verbose:
                print(f"✅ PASS: {description}")
        else:
            if verbose:
                print(f"❌ FAIL: {description} - fragmented into {len(instances)} instances")
            results["recommendations"].append(f"Loosen threshold for: {description}")
    
    # Test negative cases (should NOT merge)
    for episodes, description, failure_mode in fixture.get_negative_cases():
        results["negative_total"] += 1
        instances = await pipeline_func(episodes)
        
        # Expect 2 separate instances
        if len(instances) >= 2:
            results["negative_passed"] += 1
            if verbose:
                print(f"✅ PASS: {description}")
        else:
            if verbose:
                print(f"❌ FAIL: {description} - over-merged into {len(instances)} instances")
            results["recommendations"].append(f"Tighten {failure_mode} threshold")
    
    return results
