"""Role-vocabulary residue metrics (T2; design doc Sec 10.5 step 1).

Residue = actor mentions whose free-text role resolved to no controlled-
vocabulary role (canonical_role is None). Residue density per source and
per era is the input signal for vocabulary-revision proposals: a pattern
the role vocabulary cannot express produces no cluster, so high residue is
the discovery apparatus reporting its own blind spots.

Modern-source residue is the first-class alarm: if present-day text
renders poorly, present-day situations retrieve poorly, which is a direct
hit to forecast quality (Sec 6.5 step 1) — not merely a coverage gap.
"""

from typing import Dict, Iterable, Optional

from narrative_engine.models import Episode


def episode_residue(episode: Episode) -> Optional[float]:
    """Fraction of this episode's actor mentions with no canonical role.

    None when the episode has no actors (no mentions to measure — not the
    same thing as zero residue).
    """
    if not episode.actors:
        return None
    unresolved = sum(1 for a in episode.actors if a.canonical_role is None)
    return unresolved / len(episode.actors)


def role_residue_by_source(episodes: Iterable[Episode]) -> Dict[str, float]:
    """Residue fraction per source (first extracted_from chunk id prefix)."""
    counts: Dict[str, list] = {}
    for episode in episodes:
        source = episode.extracted_from[0] if episode.extracted_from else "unknown"
        for actor in episode.actors:
            counts.setdefault(source, [0, 0])
            counts[source][1] += 1
            if actor.canonical_role is None:
                counts[source][0] += 1
    return {
        source: unresolved / total
        for source, (unresolved, total) in counts.items()
        if total
    }


def role_residue_by_era(episodes: Iterable[Episode], bucket_years: int = 50) -> Dict[str, float]:
    """Residue fraction per era bucket (keyed by bucket start year).

    Episodes without dates land in the "undated" bucket — visible, not
    silently dropped.
    """
    counts: Dict[str, list] = {}
    for episode in episodes:
        if episode.start_date:
            start = (episode.start_date.year // bucket_years) * bucket_years
            key = str(start)
        else:
            key = "undated"
        for actor in episode.actors:
            counts.setdefault(key, [0, 0])
            counts[key][1] += 1
            if actor.canonical_role is None:
                counts[key][0] += 1
    return {
        era: unresolved / total
        for era, (unresolved, total) in counts.items()
        if total
    }
