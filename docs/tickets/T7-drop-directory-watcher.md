# T7 — Always-on drop-directory watcher with duplicate-source guard

**Priority:** P1
**Design refs:** §1 NFR "incremental ingestion", §6.1 (stable chunk IDs, source metadata), §7 (lean v1 stack)
**Depends on:** T3 (round-trip discipline for the new aggregate), T8 (serves the queue it feeds)
**Effort:** M

## Problem

Ingestion is a manual CLI invocation. The workflow the project actually
wants is: drop a book into `data/raw/` and the system picks it up,
chunks it, extracts episodes (when an LLM key is configured), composes
arc instances, and reports progress — continuously, without anyone
running commands. There is also no guard against the same book being
dropped twice (same bytes under a different filename), which would
duplicate every downstream episode and corrupt analog counts (the exact
failure T6 exists to mitigate).

## Scope

### 7a. SourceDocument aggregate

New persisted aggregate tracking each dropped file through its lifecycle:

- `SourceDocument`: filename, `content_hash` (sha256 of raw bytes),
  size_bytes, status (`queued | processing | completed | failed |
  duplicate`), error, chunks_created, episodes_created,
  `extraction_ran` (False when no LLM key — visible degradation, not
  silent skipping), `duplicate_of` (id of the original when status =
  duplicate), timestamps.
- ORM + migration + repository + round-trip test + exclusion-set entry
  (T3 discipline applies to every new aggregate).

### 7b. Duplicate guard

- Content hash computed before any processing; `get_by_hash` lookup.
- Same bytes under any filename → a `duplicate` row pointing at the
  original (visible in the dashboard queue, NOT silently skipped), and
  the processing pipeline never runs.
- Filename-only matches with different bytes process normally (new
  edition ≠ duplicate). Near-duplicate detection (same book, different
  scan/edition) is out of scope — surface-embedding dedup at retrieval
  (T6) is the backstop.

### 7c. Watcher loop (`narrative_engine/watcher.py`)

- Async polling loop (no new dependency; inotify only works on Linux
  and Docker-for-Mac breaks it anyway): scan `NE_WATCH_DIR` every
  `NE_WATCH_INTERVAL` seconds.
- Settle guard: only pick up files whose mtime is older than a few
  seconds, so half-copied files aren't processed.
- Pipeline per file: parse → chunk (existing ingestion machinery) →
  if LLM configured, extraction per chunk + composition pass +
  embeddings → status transitions recorded on the SourceDocument row
  as they happen (the dashboard polls these).
- Every stage failure lands in `status=failed` + `error` — one bad
  file must not stop the loop.
- All collaborators injectable for tests; unit tests run the scan
  function directly with a fake extractor.

## Acceptance criteria

- [ ] Dropping a file creates a row and processes it; progress statuses
      visible via repository/API.
- [ ] Dropping the same bytes twice (any filename) → `duplicate` row,
      no reprocessing (test).
- [ ] Half-written files are not picked up (settle test).
- [ ] A failing file records `failed` + error and the loop continues.
- [ ] No LLM key → file completes with `extraction_ran=False`.
