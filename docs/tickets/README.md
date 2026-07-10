# Implementation-correction tickets (2026-07-10)

Derived from a whole-design review against `docs/narrative-engine-design-v0.7.md`.
Organizing principle: the design's own "everything must pay rent" ethos (§3.6, §6.6)
— build the rent-collection apparatus, protect the signals it measures, and
drift-proof the substrate.

| # | Title | Priority | Effort | Depends on |
|---|-------|----------|--------|------------|
| [T1](T1-eval-fixtures-and-ci-gates.md) | Eval fixtures + CI gates (analog fixture, composition fixture, masked-ending loop) | P0 | L | T4 |
| [T2](T2-structural-render-hardening.md) | Structural render hardening (role vocab, proper-noun scrub, residue metric) | P1 | M | T1, T4, T5 |
| [T3](T3-model-orm-roundtrip-tests.md) | Model↔ORM round-trip tests (drift-as-a-class fix) | P0 | S | — |
| [T4](T4-embedding-render-versioning.md) | Embedding/render epoch versioning + re-embed job | P0 | M | — |
| [T5](T5-scope-registry.md) | Scope registry + alias resolver | P1 | M | — |
| [T6](T6-analog-dedup.md) | Analog dedup at retrieval (counts, not vibes) | P1 | S–M | — |

**Recommended execution order:** T3 → T4 → T5 → T6 → T2 → T1.
T3/T4 first because they protect everything that follows; T5/T6 are independent
risk reducers; T2 is a batch epoch that wants T4's machinery and T5's alias
table; T1 last only in the sense that its gates should land on top of the
corrected substrate — its fixture *authoring* can proceed in parallel anytime.
