# T2 — Harden the structural render: controlled roles, proper-noun scrub, residue metric

**Priority:** P1
**Design refs:** §3.3, §3.3a, §6.2 stage 3, §10.1, §10.5, §11.2.3
**Depends on:** T1 (analog fixture verifies the outcome), T4 (render change = version bump + re-embed epoch)
**Effort:** M

## Problem

The render is "the perceptual bottleneck of the whole discovery apparatus"
(§10) and it currently leaks identity into the analogy signal:

- Actor roles are free text ("President", "Banker") — not the §3.3 controlled
  vocabulary — so equivalent structural positions get different tokens and
  never cluster.
- `initiating_conditions` / `escalation_mechanics` are rendered as raw prose;
  proper nouns ("Lehman Brothers", "Germany") flow straight into the
  structural embedding, undermining place-blindness.
- Nothing measures how well the role vocabulary fits the corpus, so the §10.5
  vocabulary-evolution loop has no input signal.

## Scope

### 2a. Controlled role vocabulary (`extraction/roles.py`)

- `ActorRole` str-enum, ~50 roles, versioned via `CURRENT_ROLE_VOCAB_VERSION`
  (same convention as `CURRENT_TAXONOMY_VERSION`):
  - Political-economy (§3.3): RISING_POWER, INCUMBENT_HEGEMON, CREDITOR_CLASS,
    DEBTOR_CLASS, FINANCIER, SPECULATOR, REGULATOR, CENTRAL_AUTHORITY,
    COUNTER_ELITE, ASPIRANT_ELITE, …
  - Political-dramatic (§10.1): USURPER, PRETENDER, REGENT, KINGMAKER,
    COURT_FAVORITE, HEIR_APPARENT, PURGED_FACTION, …
  - Proppian-functional: PATRON, DISPATCHER, FALSE_HERO, HELPER, TRAITOR_WITHIN
  - Social/religious: PARVENU, DECLINING_HOUSE, DISPOSSESSED_CLASS,
    PROPHET_FIGURE, HERESIARCH, TRUE_BELIEVER_MOVEMENT, APOSTATE
  - Admission test per §10.1: "would two episodes a thousand years apart share
    this token in a way that reveals shape?" Document each role with one line.
- `Actor` model: add `canonical_role: str | None` and
  `role_fit_confidence: float | None`. Keep existing free-text `role` as the
  raw extraction output (it becomes the residue signal, and existing rows stay
  valid). Migration adds the two columns to `actors`.
- Extraction prompt: instruct classification of each actor into the vocabulary
  with a confidence; explicitly note roles can be filled by collective actors
  (§10.1a). Below `NE_TAU_ROLE` (default 0.5, untuned — same caveat discipline
  as τ_class) → `canonical_role=None`, mention counts as residue.

### 2b. Deterministic proper-noun scrub in the render (`retrieval/embeddings.py`)

The render is deterministic code (§6.2 stage 3), so the place-blind guarantee
belongs here, not in the prompt:

- ROLES line uses `canonical_role` tokens; fall back to `UNRESOLVED_ACTOR`
  (not the free-text role) when unresolved — free text must never reach the
  structural embedding again.
- Scrub pass over conditions/mechanics/tension lines, in order:
  1. Replace every actor mention name/alias appearing in the text with its
     role token.
  2. Replace `episode.location` and scope name/aliases (via T5 registry) with
     `<PLACE>`.
  3. Strip 4-digit years and month names with `<DATE>`.
- Unit tests: golden renders for 3 episodes asserting no proper noun from the
  source record survives; property: render(episode) == render(episode with all
  names/dates/places permuted).

### 2c. Residue metric (§10.5 step 1)

- `role_residue(episodes) -> {source_id | era: fraction_unresolved}` in
  `taxonomy/` (discovery owns vocabulary health).
- Persist per-extraction-run residue in `ExtractionRecord` output so trend is
  queryable. Modern-source residue is the first-class alarm (§10.5): if
  present-day text renders poorly, forecasts degrade silently.

### 2d. Version bump + re-embed

- Bump `CURRENT_RENDER_VERSION`; re-embed via T4's batch job. Fixture (T1)
  runs before/after; the diff in pair_recall@5 is the first real measurement
  of whether any of this works. Record both numbers in the ticket on close.

## Acceptance criteria

- [ ] Role enum (~50 roles, documented, versioned); Actor carries
      canonical_role + confidence; migration applied.
- [ ] Render contains no free-text roles and no proper nouns (golden +
      permutation tests green).
- [ ] Residue computable per source and era; surfaced in extraction records.
- [ ] Render version bumped; corpus re-embedded; analog fixture recall
      recorded before/after.

## Out of scope

- The §10.2 relation/epistemic template lines (RELATIONS/CONCEALED/REVERSAL/
  STAKES) — separate epoch, separate ticket, after this one proves the
  measurement loop works.
- Full §10.5 vocabulary-evolution loop (LLM-drafted revision proposals);
  this ticket only produces its input signal.

## Risks

- Scrubbing can delete signal (a "central bank" mention matters even when it's
  "the Fed"). Mitigation: replacement (name→role token), not deletion, wherever
  a mention resolves; measure recall impact via the fixture rather than arguing.
- ~50 roles is a hypothesis; residue tells us where it's wrong. Resist growing
  past ~80 (§10.1: roles that appear once never form clusters).
