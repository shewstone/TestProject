"""Run composition fixture validation."""

import asyncio
import sys
sys.path.insert(0, 'tests/fixtures')

from datetime import datetime, timedelta
from composition_fixture import CompositionFixture, validate_composition_pipeline
from narrative_engine.composition import ArcInstance


async def mock_pipeline(episodes):
    """Mock pipeline for testing - groups by scope, then temporal cluster."""
    # Group by scope (hard filter)
    by_scope = {}
    for ep in episodes:
        scope = getattr(ep, 'scope_id', 'default')
        by_scope.setdefault(scope, []).append(ep)
    
    clusters = []
    for scope, scope_eps in by_scope.items():
        sorted_eps = sorted(scope_eps, key=lambda e: e.start_date or datetime.min)
        current_cluster = []
        
        for ep in sorted_eps:
            if not current_cluster:
                current_cluster = [ep]
            else:
                last = current_cluster[-1]
                gap = (ep.start_date or datetime.min) - (last.end_date or datetime.min)
                # 5-year threshold (institutional scale)
                if gap <= timedelta(days=365*5):
                    current_cluster.append(ep)
                else:
                    if len(current_cluster) >= 2:
                        clusters.append(current_cluster)
                    current_cluster = [ep]
        
        if current_cluster and len(current_cluster) >= 2:
            clusters.append(current_cluster)
    
    # Create mock instances
    instances = []
    for cluster in clusters:
        inst = ArcInstance(
            arc_type=cluster[0].arc_type,
            canonical_name=f'{cluster[0].arc_type.value}, {cluster[0].scope_id}',
        )
        instances.append(inst)
    
    return instances


async def main():
    results = await validate_composition_pipeline(mock_pipeline, verbose=True)
    
    print()
    print('='*70)
    print('COMPOSITION FIXTURE RESULTS')
    print('='*70)
    print(f'Positive (should merge):     {results["positive_passed"]}/{results["positive_total"]}')
    print(f'Negative (should NOT merge): {results["negative_passed"]}/{results["negative_total"]}')
    print(f'Edge cases:                  {results.get("edge_passed", 0)}/{results.get("edge_total", 0)}')
    print()
    
    if results['recommendations']:
        print('Threshold Tuning Recommendations:')
        for rec in results['recommendations']:
            print(f'  • {rec}')
        print()
        print('Status: ⚠️  FIXTURE NOT PASSING - tune thresholds')
    else:
        print('Status: ✅ FIXTURE PASSING - thresholds validated!')
    
    # Overall pass/fail
    total_pass = results['positive_passed'] + results['negative_passed']
    total = results['positive_total'] + results['negative_total']
    print(f'Overall: {total_pass}/{total} ({100*total_pass//total}% pass rate)')


if __name__ == "__main__":
    asyncio.run(main())
