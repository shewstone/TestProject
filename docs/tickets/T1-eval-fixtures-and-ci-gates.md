# T1 — Build the evaluation fixtures and wire them as CI gates

**Priority:** P0 (highest — nothing else is verifiable without it)
**Design refs:** §3.6, §6.3, §6.6, §11.3
**Depends on:** T4 (embedding versioning) recommended first, so fixture scores are comparable across epochs. T2 verification consumes this ticket's fixture.
**Effort:** L (fixture authoring is content work; harness assembly is code work)

## Problem

The design's empirical tiebreaker — "everything must pay rent" — has no rent-collection apparatus:

1. The 30-pair cross-era analog fixture (§6.3) does not exist. Until it does, the
   place-blind structural embedding (the system's core bet) is unverified.
2. The composition fixture has 1 positive and 1 decoy — too small to tune the
   per-scale temporal thresholds it exists to tune (§6.6).
3. The masked-ending primitives exist (`evaluation/masking.py`) but the
   snapshot → forecast → score loop around them was never assembled (§11.3).
4. The doc says fixture failure "blocks embedding-model upgrades" and
   "blocks pipeline-version upgrades" — but no CI job enforces either.

## Scope

### 1a. Analog fixture (`tests/fixtures/analog_fixture.py` + `data/fixtures/analog_pairs.json`)

- 30 hand-built cross-era analog pairs as minimal `Episode` records (title,
  summary, actors+roles, initiating_conditions, escalation_mechanics, tension,
  mechanism_tags, arc_type/phase, scope, dates). Outcome fields present but
  NEVER rendered (§3.3 v0.7).
- Mix per §6.3 and §10.4: financial (Athens/Sparta↔Germany/Britain is the
  canonical example; 1907↔2008; tulip↔South Sea↔dot-com), plus non-financial
  pairs (Sejanus↔Ming court purge; Wars of the Roses↔Sengoku succession;
  French↔Iranian revolution) so the widened-sensorium claim is testable later.
- ≥30 distractor episodes (same era/region as one pair member, different
  story-shape) so top-k rank means something.
- Fixture file carries `fixture_version` and per-pair `expected_rank_k`
  (default k=5).

### 1b. Metric + test (`tests/fixtures/test_analog_fixture.py`)

- Render + embed every fixture episode with the pinned model; for each pair,
  compute the rank of its partner among all fixture episodes by structural
  cosine similarity.
- Metrics: `pair_recall@5` (fraction of pairs where partner ranks top-5) and
  mean reciprocal rank. Emit both to stdout on every run so history is greppable.
- Gate: `pair_recall@5 >= RECALL_FLOOR`. Set `RECALL_FLOOR` empirically —
  first run establishes baseline, floor = baseline − 0.05 slack, ratcheted up
  as the render improves. A hard-coded aspirational floor that fails from day
  one teaches everyone to ignore the gate.
- Marked `@pytest.mark.fixture_gate`.

### 1c. Composition fixture growth (`tests/fixtures/composition_fixture.py`)

- ≥5 positive multi-source instances (e.g. one arc whose beats span 3 synthetic
  "books" with disjoint phase coverage), ≥5 near-miss decoys (same scope +
  arc_type + rough temporal proximity, distinct instances: 1873 vs 1893 panics,
  1907 vs 1929, dot-com vs 2008; plus one cross-scope decoy pair to prove the
  scope partition earns its keep).
- Score: precision/recall on episode→instance assignment. Gate on both ≥ baseline.
- This fixture is the tuning target for the per-scale temporal thresholds —
  add a sweep script (`scripts/tune_thresholds.py`) that grid-searches
  thresholds against the fixture and prints the frontier. Thresholds stay in
  config; the script justifies their values (§6.2 stage 6: "fixture-tuned
  hypotheses, not constants").

### 1d. Masked-ending harness loop (`src/narrative_engine/evaluation/harness.py`)

- `run_backtest(cutoff_year, test_episodes, condition)`:
  1. Snapshot: apply existing data-layer masking (drop post-T, strip outcomes
     from ongoing episodes).
  2. For each test episode (its own outcome masked): run analog retrieval +
     thesis generation against the masked corpus.
  3. Score each thesis against ground truth (existing Brier + outcome-match
     machinery), tagged by `mode` (arc_based scored separately from arc_less, §6.5.8).
  4. Run persistence and bare-LLM baselines (already implemented) on the same
     test set; report skill scores vs both.
- CLI: `python -m narrative_engine.evaluation.harness --cutoff 1929 --k 10`.
- Integration test with a small synthetic corpus proving the loop runs
  end-to-end and that masked data is unreachable (assert a canary: no thesis
  cites a post-cutoff episode; no retrieved analog has a resolution).

### 1e. CI gates (`.github/workflows/ci.yml`)

- New job `fixture-gates`, runs `pytest -m fixture_gate`, required for merge.
- The analog gate is the *embedding-upgrade blocker*; the composition gate is
  the *pipeline-upgrade blocker*. Changing `EmbeddingGenerator.DEFAULT_MODEL`,
  the render template, or `composition/` without green gates must fail CI.

## Acceptance criteria

- [ ] 30 pairs + ≥30 distractors committed as versioned fixture data.
- [ ] `pair_recall@5` computed, printed, and gated in CI.
- [ ] Composition fixture ≥5 positives / ≥5 decoys; precision/recall gated.
- [ ] Threshold sweep script exists and README documents how thresholds were set.
- [ ] `harness.run_backtest` runs end-to-end on a synthetic corpus in CI; leakage
      canary test passes.
- [ ] CI has a required `fixture-gates` job.

## Out of scope

- Taxonomy A/B (needs discovered clusters populated — §3.6) and mechanism-claim
  tests (needs per-scope density): the harness should accept a `condition`
  parameter so these slot in later, but implementing them is not this ticket.
- Real-corpus backtests (1907/1929/1997/2008 per §8 step 2) — requires ingested
  corpus; harness must make them *possible*, not run them.

## Risks

- LLM-knows-the-ending leakage is inherent (§6.6); the harness controls what
  the *system* sees, not what the model remembers. Score analog-selection
  quality separately from narrative plausibility to keep the signal honest.
- Fixture authored by an LLM shares the LLM's priors (§3.2.1). Human review of
  the 30 pairs before they gate anything.
