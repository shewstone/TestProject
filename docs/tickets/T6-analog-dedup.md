# T6 — Deduplicate analogs at retrieval: protect "counts, not vibes"

**Priority:** P1
**Design refs:** §6.5 step 6 (branch frequencies grounded in counts), §9 (narrative fallacy), §11.4 (duplicate narrations unmitigated)
**Depends on:** nothing (interim heuristics); superseded in part by future ActorEntity work
**Effort:** S–M

## Problem

Same-event resolution is name-match-based until entity resolution lands, so
duplicate narrations of one happening (Kindleberger's 1929 and Galbraith's
1929) enter the analog set as independent evidence. Thesis branch frequencies
are explicitly counts over analogs — duplicates directly inflate the
confidence of whatever continuation the most-written-about events had. This
corrupts the product's central numbers and amplifies §9's survivorship bias
(dramatic events are narrated more, so they'd also be *counted* more).

## Scope

### 6a. SAME_EVENT_AS collapse (`retrieval/analog_retrieval.py`)

- After scoring, before ranking: query `episode_links` for SAME_EVENT_AS edges
  among the candidate set; union-find the connected components; keep the
  highest-combined-score member of each component as representative.
- `RetrievedAnalog` gains `duplicate_ids: list[UUID]` (transparency: the
  thesis can disclose "3 narrations of this event").

### 6b. Interim identity heuristic (until ActorEntity lands)

SAME_EVENT_AS edges are sparse today (linking is per-run). Add a conservative
in-set collapse for candidates that agree on ALL of: resolved scope_id,
arc_type, overlapping time_span, AND surface-embedding similarity above the
existing `similarity_threshold` (0.85). Surface embedding is the identity
signal (§3.3a) — never structural. Flag merged-by-heuristic in
`duplicate_ids` provenance the same way; log every heuristic merge.

### 6c. Thesis accounting

- Branch frequencies computed over deduped analogs.
- `ThesisGenerator` per-source cap as defense-in-depth: no single source_id
  contributes more than `max_per_source` (default 3) analogs to one thesis —
  bounds single-book narrative dominance even when identity fails.
- Thesis narrative discloses dedup: "12 analogs (15 retrieved, 3 duplicate
  narrations collapsed)".

## Acceptance criteria

- [ ] Two episodes linked SAME_EVENT_AS never both appear in one analog set
      (test).
- [ ] Heuristic collapse fires on a synthetic duplicate pair (same scope/arc/
      dates, surface sim > 0.85) and does NOT fire on the 1907-vs-1929 decoy
      pair (distinct events, same scope+arc) (test).
- [ ] Branch frequencies change accordingly (test: duplicate inflates
      probability before, not after).
- [ ] Dedup disclosed in thesis output.

## Out of scope

- Writing SAME_EVENT_AS edges (that's the linking stage); this ticket only
  consumes them plus the interim heuristic.
- Survivorship-bias correction generally (§9) — dedup removes double-counting,
  not over-documentation of dramatic events.
