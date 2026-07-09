"""Composition fixture for validating identity resolution thresholds.

Contains hand-built Arc Instances that the composition pass MUST recover,
plus deliberate near-miss decoys that it must NOT merge.

Use this to tune thresholds BEFORE deploying composition pipeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Tuple
from uuid import UUID, uuid4

from narrative_engine.models import (
    Actor,
    ArcPhase,
    ArcType,
    CycleScale,
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
        """Cases that SHOULD merge into single Arc Instance.
        
        Returns: (episodes, description)
        """
        cases = []
        
        # Case 1: 1929 Crash across two books (the happy path)
        # Book A: early phases, Book B: late phases
        case_1929 = [
            Episode(
                id=uuid4(),
                title="1920s Economic Expansion",
                summary="Post-war boom and stock market growth",
                start_date=datetime(1922, 1, 1),
                end_date=datetime(1927, 9, 1),
                location="United States",
                scope_id="us_national",  # Same scope
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
            Episode(
                id=uuid4(),
                title="Great Depression Begins",
                summary="Market bottom and economic devastation",
                start_date=datetime(1929, 11, 1),
                end_date=datetime(1932, 7, 8),
                location="United States",
                scope_id="us_national",
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,
                arc_phase=ArcPhase.REVULSION,
                extracted_from=["kindleberger-mania.txt"],
            ),
        ]
        cases.append((case_1929, "1929 Crash: multi-book, continuous arc"))
        
        # Case 2: Weimar Hyperinflation across sources
        case_weimar = [
            Episode(
                id=uuid4(),
                title="War Reparations Burden",
                summary="Treaty of Versailles obligations",
                start_date=datetime(1921, 1, 1),
                end_date=datetime(1922, 6, 1),
                location="Weimar Republic",
                scope_id="weimar_republic",
                arc_type=ArcType.FISCAL_DISTRESS,
                arc_phase=ArcPhase.SETUP,
                extracted_from=["fischer-germany.txt"],
            ),
            Episode(
                id=uuid4(),
                title="Ruhr Occupation and Resistance",
                summary="French occupation, passive resistance",
                start_date=datetime(1923, 1, 1),
                end_date=datetime(1923, 10, 1),
                location="Ruhr Valley",
                scope_id="weimar_republic",
                arc_type=ArcType.FISCAL_DISTRESS,
                arc_phase=ArcPhase.ESCALATION,
                extracted_from=["historian-b.txt"],
            ),
            Episode(
                id=uuid4(),
                title="Hyperinflation Peak",
                summary="Currency collapse and stabilization",
                start_date=datetime(1923, 10, 1),
                end_date=datetime(1923, 11, 15),
                location="Berlin",
                scope_id="weimar_republic",
                arc_type=ArcType.FISCAL_DISTRESS,
                arc_phase=ArcPhase.CLIMAX,
                extracted_from=["historian-b.txt"],
            ),
        ]
        cases.append((case_weimar, "Weimar Hyperinflation: same scope, continuous"))
        
        return cases
    
    @staticmethod
    def get_negative_cases() -> List[Tuple[List[Episode], str, str]]:
        """Cases that should NOT merge (deliberate near-misses).
        
        Returns: (episodes, description, failure_mode_to_avoid)
        
        These are DECOYS - similar but distinct arcs that must remain separate.
        """
        cases = []
        
        # Case N1: 1907 Panic vs 1920s Boom (same scope, close-ish in time, same arc_type)
        # Should NOT merge - different instances
        panic_1907 = [
            Episode(
                id=uuid4(),
                title="1907 Bankers' Panic",
                summary="Financial crisis and liquidity crunch",
                start_date=datetime(1907, 10, 1),
                end_date=datetime(1907, 11, 1),
                location="New York",
                scope_id="us_national",  # SAME scope as 1929
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,  # SAME arc type
                arc_phase=ArcPhase.PANIC,
                extracted_from=["bruner-carr-1907.txt"],
            ),
            Episode(
                id=uuid4(),
                title="Morgan's Intervention",
                summary="JP Morgan stabilizes markets",
                start_date=datetime(1907, 11, 1),
                end_date=datetime(1907, 12, 1),
                location="New York",
                scope_id="us_national",
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,
                arc_phase=ArcPhase.RESOLUTION,
                extracted_from=["bruner-carr-1907.txt"],
            ),
        ]
        
        boom_1920s = [
            Episode(
                id=uuid4(),
                title="Roaring Twenties Expansion",
                summary="Post-WWI economic boom",
                start_date=datetime(1922, 1, 1),
                end_date=datetime(1927, 1, 1),
                location="United States",
                scope_id="us_national",  # SAME scope
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,  # SAME arc type
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
        
        # These should create TWO separate Arc Instances, not one
        cases.append((
            panic_1907 + boom_1920s,
            "1907 Panic vs 1920s Boom: same scope, different instances",
            "temporal_overmerge"  # Threshold too loose
        ))
        
        # Case N2: US vs Japan credit booms (different scope, same arc_type)
        us_boom = [
            Episode(
                id=uuid4(),
                title="US Credit Expansion",
                summary="American debt buildup",
                start_date=datetime(1922, 1, 1),
                end_date=datetime(1929, 1, 1),
                location="United States",
                scope_id="us_national",
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,
                arc_phase=ArcPhase.BOOM,
                extracted_from=["us-historian.txt"],
            ),
        ]
        
        japan_boom = [
            Episode(
                id=uuid4(),
                title="Japan Asset Bubble",
                summary="Japanese credit expansion",
                start_date=datetime(1985, 1, 1),
                end_date=datetime(1989, 1, 1),
                location="Japan",
                scope_id="japan_national",  # DIFFERENT scope
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,  # SAME arc type
                arc_phase=ArcPhase.BOOM,
                extracted_from=["japan-historian.txt"],
            ),
            Episode(
                id=uuid4(),
                title="Japan Bubble Burst",
                summary="Lost Decade begins",
                start_date=datetime(1989, 1, 1),
                end_date=datetime(1992, 1, 1),
                location="Tokyo",
                scope_id="japan_national",
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,
                arc_phase=ArcPhase.PANIC,
                extracted_from=["japan-historian.txt"],
            ),
        ]
        
        cases.append((
            us_boom + japan_boom,
            "US vs Japan credit booms: different scope, same arc type",
            "scope_underfilter"  # Missing scope partition
        ))
        
        # Case N3: Similar timing, different actors (different instances)
        tech_bubble = [
            Episode(
                id=uuid4(),
                title="Dot-Com Euphoria",
                summary="Internet stock speculation",
                start_date=datetime(1998, 1, 1),
                end_date=datetime(2000, 3, 1),
                location="NASDAQ",
                scope_id="us_national",
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,
                arc_phase=ArcPhase.EUPHORIA,
                extracted_from=["tech-historian.txt"],
            ),
            Episode(
                id=uuid4(),
                title="Dot-Com Crash",
                summary="Tech bubble bursts",
                start_date=datetime(2000, 3, 1),
                end_date=datetime(2001, 1, 1),
                location="United States",
                scope_id="us_national",
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,
                arc_phase=ArcPhase.PANIC,
                extracted_from=["tech-historian.txt"],
            ),
        ]
        
        cases.append((
            tech_bubble + boom_1920s,  # Mix with earlier 1920s case
            "1920s Boom vs Dot-Com: similar arc, different time, no actors in common",
            "actor_undercheck"  # Missing actor overlap check
        ))
        
        return cases
    
    @staticmethod
    def get_edge_cases() -> List[Tuple[List[Episode], str]]:
        """Edge cases for robustness testing."""
        cases = []
        
        # Overlapping episodes (same time period, different sources)
        overlap_case = [
            Episode(
                id=uuid4(),
                title="1929 Crash (Source A)",
                summary="Black Tuesday from financial perspective",
                start_date=datetime(1929, 10, 24),
                end_date=datetime(1929, 10, 29),
                location="NYSE",
                scope_id="us_national",
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,
                arc_phase=ArcPhase.PANIC,
                extracted_from=["financial-history.txt"],
            ),
            Episode(
                id=uuid4(),
                title="1929 Crash (Source B)",
                summary="Black Tuesday from social perspective",
                start_date=datetime(1929, 10, 24),
                end_date=datetime(1929, 10, 29),
                location="Wall Street",
                scope_id="us_national",
                arc_type=ArcType.CREDIT_BOOM_AND_BUST,
                arc_phase=ArcPhase.PANIC,
                extracted_from=["social-history.txt"],
            ),
        ]
        cases.append((overlap_case, "Overlapping episodes: should merge (SAME_EVENT_AS)"))
        
        return cases


# Validation runner
def validate_composition_pipeline(pipeline_func, verbose: bool = True) -> dict:
    """Run composition fixture against a pipeline implementation.
    
    Args:
        pipeline_func: Function that takes List[Episode] and returns List[ArcInstance]
        verbose: Print detailed results
    
    Returns:
        Dict with pass/fail statistics and threshold recommendations
    """
    fixture = CompositionFixture()
    
    results = {
        "positive_passed": 0,
        "positive_total": 0,
        "negative_passed": 0,
        "negative_total": 0,
        "edge_passed": 0,
        "edge_total": 0,
        "recommendations": [],
    }
    
    # Test positive cases (should merge)
    for episodes, description in fixture.get_positive_cases():
        results["positive_total"] += 1
        instances = pipeline_func(episodes)
        
        if len(instances) == 1:
            results["positive_passed"] += 1
            if verbose:
                print(f"✅ PASS: {description}")
        else:
            if verbose:
                print(f"❌ FAIL: {description} - fragmented into {len(instances)} instances")
            results["recommendations"].append(f"Loosen temporal threshold for: {description}")
    
    # Test negative cases (should NOT merge)
    for episodes, description, failure_mode in fixture.get_negative_cases():
        results["negative_total"] += 1
        instances = pipeline_func(episodes)
        
        # For negative cases, expect multiple instances (or specific count)
        expected_count = len(episodes) // 2 + (1 if len(episodes) % 2 else 0)  # Approximate
        
        if len(instances) >= expected_count:
            results["negative_passed"] += 1
            if verbose:
                print(f"✅ PASS: {description}")
        else:
            if verbose:
                print(f"❌ FAIL: {description} - over-merged into {len(instances)} instances")
            results["recommendations"].append(f"Tighten {failure_mode} threshold")
    
    # Test edge cases
    for episodes, description in fixture.get_edge_cases():
        results["edge_total"] += 1
        instances = pipeline_func(episodes)
        
        # Edge cases: should handle without crashing
        results["edge_passed"] += 1
        if verbose:
            print(f"✅ EDGE: {description} - {len(instances)} instance(s)")
    
    return results


if __name__ == "__main__":
    print("Composition Fixture - Use this to validate identity resolution thresholds")
    print("=" * 70)
    print()
    print("Run: validate_composition_pipeline(your_pipeline_func)")
    print()
    print("Positive cases:", len(CompositionFixture.get_positive_cases()))
    print("Negative cases (decoys):", len(CompositionFixture.get_negative_cases()))
    print("Edge cases:", len(CompositionFixture.get_edge_cases()))
    print()
    print("Tune thresholds until:")
    print("  - All positive cases pass (correct merges)")
    print("  - All negative cases pass (no false merges)")
