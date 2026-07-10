# T4 — Make embedding/render versioning real: stale vectors become invisible, not wrong

**Priority:** P0
**Design refs:** §6.3 (pinned model, batch re-embed), §6.2 (versioned stages), §10.5 (batch epochs), §11.4 (v0.7 re-embed warning)
**Depends on:** nothing (T1/T2 depend on this)
**Effort:** M

## Problem

The design treats renders and embeddings as versioned artifacts with batch-epoch
re-runs; the v0.7 render change explicitly invalidated all existing structural
embeddings (§11.4). But `Episode` carries a bare `version` int, embeddings
carry nothing. Consequences:

- Nothing records which render template or embedding model produced a stored
  vector. After any change, retrieval silently compares vectors from
  incompatible spaces — no error, just quietly garbage similarity scores.
- "Re-embed the corpus" is a manual footgun with no tooling and no way to
  even find stale rows.

## Scope

### 4a. Version constants (`retrieval/embeddings.py`)

- `CURRENT_RENDER_VERSION = "render-v0.7.0"` (the outcome-free render);
  `EMBEDDING_MODEL_VERSION = f"{model_name}"` derived from the pinned model.
- Combined `embedding_epoch` property: `f"{render_version}+{model_version}"`
  for structural; surface embeddings key on model version only (no render
  involved).

### 4b. Schema (`orm_models.py` + migration)

- `episodes.structural_embedding_epoch: str | None`,
  `episodes.surface_embedding_epoch: str | None` — set whenever the
  corresponding vector is written, NULL when vector is NULL.
- Backfill migration: existing non-null embeddings get epoch
  `"render-v0.6.0+all-MiniLM-L6-v2"` (pre-v0.7 render), which is *by design*
  not the current epoch — they are exactly the stale vectors §11.4 warns about
  and must stop matching.

### 4c. Write path

- `EpisodeRepository.update_embedding` and `_to_orm` stamp the epoch matching
  the `kind` being written. It must be impossible to write a vector without
  its epoch (single choke point; keep it that way).

### 4d. Read path

- `search_by_embedding` adds
  `WHERE structural_embedding_epoch = :current_epoch`. Off-epoch episodes are
  invisible to retrieval — a smaller honest analog base beats a larger corrupt
  one (same §6.5.8 ethos as arc-less mode: visible degradation over silent
  wrongness).
- Composition's surface-similarity signal checks epochs match before
  comparing two vectors; mismatch → treat as missing signal (the evidence
  floor already handles missing signals correctly).

### 4e. Re-embed batch job (`scripts/reembed.py` or `python -m narrative_engine.retrieval.reembed`)

- Selects episodes where epoch != current (or NULL vector with renderable
  content), re-renders, re-embeds, stamps. Idempotent, resumable (keyed by
  episode id), logs counts. `--dry-run` prints stale/total.
- Health check: `stale_fraction` queryable; harness (T1) refuses to run a
  backtest if stale_fraction > 0 (a backtest over mixed epochs is
  uninterpretable).

## Acceptance criteria

- [ ] Epoch columns exist, stamped on every write path, backfilled by migration.
- [ ] Retrieval provably excludes off-epoch vectors (test: two episodes, one
      stale, only the current one retrieved).
- [ ] Composition treats epoch mismatch as missing signal (test).
- [ ] Re-embed job runs idempotently on a seeded DB; second run is a no-op.
- [ ] Bumping `CURRENT_RENDER_VERSION` in a test makes the whole corpus stale
      and retrieval returns nothing — proving the failure mode is now loud.

## Out of scope

- Multi-epoch coexistence / blue-green re-embedding. At 10³–10⁴ docs
  (§1 NFRs), re-embed is minutes of compute; complexity not warranted.
- Prompt/pipeline versioning for extraction stages (§6.2's
  (pipeline_version, taxonomy_version, vocab_version) re-run keying) — same
  pattern, separate ticket, different blast radius.
