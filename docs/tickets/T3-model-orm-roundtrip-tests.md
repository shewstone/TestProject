# T3 — Round-trip property tests: kill Pydantic↔ORM drift as a class

**Priority:** P0 (cheap, protects everything else)
**Design refs:** §4 (schema-first); motivated by the 2026-07-10 drift-fix session
**Depends on:** nothing
**Effort:** S

## Problem

Every entity is defined twice — Pydantic (`models.py`) and ORM
(`orm_models.py`) — with hand-written `_to_orm`/`_from_orm` converters.
That duplication produced the entire 2026-07-10 failure class:
`dominant_continuation` type rot, raw UUIDs in JSON columns, dropped
timestamps, a repository method (`update_embedding`) that existed only in a
test. Nothing structurally prevents recurrence: add a field to a model, forget
the converter, and the bug surfaces months later as a runtime
ValidationError.

## Scope

### 3a. Maximal round-trip tests (`tests/unit/test_roundtrip.py`)

For each persisted aggregate — Episode, Cycle, Thesis, CycleMembership,
EpisodeLink:

- A **maximal instance builder**: every optional field populated with a
  non-default, type-exercising value (UUIDs in lists, nested models, tuples,
  enums, dates, embeddings).
- Test: `created = await repo.create(maximal); fetched = await repo.get_by_id(created.id)`
  then `fetched.model_dump() == maximal.model_dump()` modulo an explicit,
  named exclusion set (`version` counters, server-assigned timestamps if any).
  The exclusion set is an allowlist in the test file — every exclusion needs a
  one-line justification comment.
- A **minimal instance** variant (only required fields) to catch NOT NULL /
  None-handling asymmetries — this is the case that caught the nullable
  `dominant_continuation`.

### 3b. Field-coverage tripwire

- For each pair, assert the converter touches every model field:
  `set(Model.model_fields) - HANDLED_FIELDS == set()` where `HANDLED_FIELDS`
  is declared next to the converter. Adding a model field without updating the
  converter now fails a unit test *by name* instead of silently persisting
  nothing. (Simpler and more honest than AST inspection; the declaration is
  the converter's checklist.)

### 3c. Fold the root-level `test_e2e*.py` strays

`test_e2e.py`, `test_e2e_simple.py`, `test_e2e_composition.py`,
`test_ingestion.py`, `run_fixture_test.py` sit outside `testpaths` and never
run — they are rot in progress. Move anything still valuable under `tests/`,
delete the rest.

## Acceptance criteria

- [ ] Round-trip (maximal + minimal) green for all five aggregates against
      real Postgres in CI.
- [ ] Deliberately adding a dummy field to Episode without touching the
      converter fails the tripwire (verified once, then revert the dummy).
- [ ] No test files outside `tests/`.

## Out of scope

- Merging the two model layers (SQLModel or codegen). Bigger change, unclear
  payoff while the schema is still moving; the tests deliver the safety at 5%
  of the cost.
- Hypothesis-based generation: nice later; hand-built maximal instances are
  deterministic and debuggable, and the failure mode being defended against is
  "field forgotten", not "weird value".
