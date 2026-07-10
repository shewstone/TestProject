# Narrative Engine: Technical Design for Qualitative Historical Forecasting

**Status: Draft v0.7 (as-built reconciliation, 2026-07-10)** — aligns the document with the NarrativeGenerator implementation. **§11 (As-Built Status)** records what is implemented, partially implemented, and not yet built. Five fixes landed in code with this revision: (1) unscoped episodes no longer pool into one shared composition partition (§6.2 stage 6 item 1); (2) outcome fields are excluded from the structural render — a change to the §3.3 template; (3) τ_class, the unclassified state, and arc-less theses are now implemented (§6.2 stage 4, §6.5.8); (4) composition requires a minimum count of concrete identity signals — the evidence floor, a new stage-6 guardrail; (5) data-layer corpus masking and persistence/bare-LLM baselines landed in the eval harness (§6.6). A pre-existing retrieval bug (cosine *distance* filtered as if it were similarity, inverting the analog ranking cut) was also fixed. Note: fix (2) changes structural-embedding inputs, so the corpus must be re-embedded — a batch epoch per §6.3.

**Prior status: Draft v0.6 (merge)** — v0.2 added hybrid taxonomy (deductive canon + inductive discovery); v0.3 added polity-scoped cycles, many-to-many episode↔cycle membership, and dyadic/system-level retrieval; v0.4 added the arc-instance layer (multi-source arc composition), persistent actor/cohort entities, a controlled mechanism vocabulary (Turchin-style structural indicators as narrative proxies), mechanism-conditioned transitions, and a formalized external-framework import flow. **Lineage note: two branches followed v0.4 in parallel. v0.4.1 (design branch)** defined the no-fit path: classification confidence floor with an explicit unclassified state, unclassified density as a discovery trigger, an arc-less degraded forecasting mode, and provisional cluster-keyed composition. **v0.5 (implementation branch, cut from v0.4 — did not include v0.4.1)** corrected the composition similarity signal (surface, not structural — §3.3a), specified the identity-resolution pipeline ordering and per-scale temporal thresholds (§6.2 stage 6), schema-tized review state and the causal-attestation invariant (§4), and added near-miss decoys to the composition fixture (§6.6). **v0.6 merges both branches** and reconciles their interaction: provisional composition (v0.4.1) is restated against the v0.5 identity-resolution ordering. **§10 (Future Improvements)** added post-merge: widening the discovery sensorium — role vocabulary, render-template relation/epistemic lines, corpus tranches, story-theory imports (Propp/Booker/Polti/Frye), and a vocabulary-evolution loop.

**Concept:** Treat history as a corpus of stories with recurring arcs. Extract, classify, and structure those arcs at multiple time scales, then forecast by story-completion: given where we are in the arc, how do stories like this usually continue?

---

## 1. Problem Statement & Requirements

Quantitative models consume prices and time series. This system consumes text — histories, articles, primary sources — and builds a structured semantic model of how situations evolve. Core bet: narrative arcs are non-random, and matching a present situation against a library of historical arcs yields predictive signal.

### Functional requirements

1. Ingest long-form text (books, articles, archives) at scale.
2. Decompose text into discrete narrative units (episodes) with actors, tensions, and outcomes.
3. Classify episodes against a three-layer taxonomy: discovered clusters (bottom), canonical arc types (middle), abstract LLM descriptions (top) — **with an explicit no-fit outcome; classification is never a forced choice (v0.4.1, §6.2 stage 4)**. See §3.
4. Compose episodes across sources into arc instances: concrete unfoldings of one arc in one scope, so that book 1 covering phases 1–2 and book 2 covering phases 3–5 stitch into a single instance. (new v0.4)
5. Organize episodes into a fractal cycle hierarchy (civilizational → institutional → generational → episodic).
6. Tag episodes with a controlled mechanism vocabulary (elite overproduction, immiseration, fiscal distress, …) so structural-demographic indicators are queryable, aggregatable features rather than free text. (new v0.4)
7. Given a present-day situation, retrieve historical analogs and generate a forecast thesis with reasoning, frequencies, and cited precedents — **degrading visibly to an arc-less mode when the situation fits no known arc (v0.4.1, §6.5)**.
8. Backtest on held-out history with the ending masked; A/B the taxonomy layers; test mechanism-conditioned transition claims. (extended v0.4)

### Non-functional requirements

- Full provenance: every claim in a thesis traces to source passages. Inferred (non-attested) links are permitted only where explicitly flagged as such (§6.2 stage 6).
- Corpus: 10³–10⁴ documents initially; incremental ingestion.
- Taxonomies, prompts, embeddings, mechanism vocabularies, and framework imports are versioned artifacts; re-running with a new version is a batch job, not a rewrite.

### Non-goals (v1)

- No price-level predictions; output is structural/directional theses with historical base rates.
- No real-time news; batch first.
- No quantitative mechanism measurement. We import the *phase structures* of frameworks like Dalio's debt cycles or Turchin's secular cycles, and narrative *signatures* of their mechanism variables — not their quantitative determinants (debt/GDP, PSI, wage series). A framework-seeded cycle tree is a hypothesis, never a framework-validated result (§3.7).

---

## 2. Core Conceptual Model

**Episode** — atomic narrative unit: a bounded situation with a beginning state, a tension, and a resolution (or open tension). Carries actors (as role-bearing mentions), initiating conditions, escalation mechanics, resolution, consequences, mechanism tags, dates/places, provenance.

**Arc** — an archetypal *shape* with named phases (e.g., boom → euphoria → distress → panic → revulsion). Arcs exist at all three taxonomy layers. An arc is a type, not a happening.

**Arc instance (new v0.4)** — a concrete unfolding of one arc type in one scope: "HUBRIS_NEMESIS, Wilhelmine Germany, 1890–1918, composed of these five episodes." Arc instances are the composition target that lets multiple sources, each covering different phases, contribute beats to the same story. Implemented as episodic-scale `Cycle`s by convention, populated by the composition pass (§6.2 stage 6). Episode→instance membership carries phase coverage, so we can see which phases of an instance are documented and which are gaps.

**Actor entity vs. actor mention (new v0.4)** — episodes carry *mentions* (name + role in this episode); mentions resolve to persistent *entities*: persons, institutions, polities, or **cohorts**. Cohort entities are what allow generational archetypes (Strauss–Howe's Prophet/Nomad/Hero/Artist) to attach to something that persists across episodes; entity resolution also strengthens same-event linking and cross-polity phase correlation.

**Mechanism (new v0.4)** — a controlled-vocabulary structural driver with a recognizable narrative signature: elite overproduction shows up in texts as credential inflation, patronage bottlenecks, counter-elite formation, factional splintering; immiseration as wage complaints, land pressure, urban unrest. Mechanisms tag `initiating_conditions` / `escalation_mechanics`, condition phase transitions in `ArcDefinition`s, and feed the `watch_for` indicators in theses. They are qualitative proxies for structural-demographic variables — Turchin's engine rendered in narrative terms — never quantitative measurements.

**Cycle** — recursive container giving the fractal structure explicitly in the schema. Cycles are scoped: every cycle tree belongs to a polity/civilization (or to the international system itself), so there is no single global "phase of history." Different scopes run asynchronous phase clocks — at any calendar date, the US and China sit at different positions in different cycle trees (1918 is late-imperial-collapse for Austria-Hungary and early-ascendancy for the US). Calendar time is an axis for alignment, never a key.

Episode↔cycle membership is many-to-many: a coupled episode (a trade war, an alliance crisis) belongs to each participating polity's cycle and to the system-scoped cycle, because hegemonic-rivalry arcs are properties of the dyad/system, not of either country alone. Within each membership the episode can carry a different reading — the same trade war may be a REFORM_REACTION beat in one polity's institutional cycle and a RISE_OVEREXTENSION beat in the system cycle.

```
Scope: US ──────────────────┐  Scope: CHINA ────────────────┐  Scope: INTL_SYSTEM ─┐
  Cycle (civilizational)    │    Cycle (civilizational)     │   Cycle (hegemonic   │
  └── Cycle (institutional) │    └── Cycle (institutional)  │        order)        │
      └── Cycle (gen.)      │        └── Cycle (gen.)       │   └── Episode:       │
          └── Episode ──────┼────────────────┼──────────────┼──▶ "US–China trade   │
                            │                └──────────────┼──▶  war" (member of  │
                            └────────────────────────────────┼──▶  all three scopes)│
```

The critical annotation is arc-phase position ("phase 3 of 5 as of 1911"), always relative to a scoped cycle. Forecasting = phase completion conditioned on analogs and, where available, on mechanism indicators (§3.8). Geography is stripped from structural embeddings (so Ming China can analogize a modern Western polity) but preserved in scope metadata — matching is place-blind; context is not.

---

## 3. Taxonomy Architecture: Hybrid Deductive/Inductive

### 3.1 The design tension

A predefined taxonomy (Campbell, Kindleberger, narrative theory) imposes categories on history; pure induction requires a large corpus before anything works, and extraction itself needs a schema to be checkable. Resolution: **bootstrap deductively, discover inductively, promote discoveries into the canon.**

| Layer | Source | Role | Example |
|---|---|---|---|
| Discovered (bottom) | Structural-embedding clusters | Captures diversity; 50+ micro-patterns | Cluster #7: "tech bubble + regulatory crackdown" |
| Canonical (middle) | Versioned predefined set (~14 arcs, evolving) | Interpretability; maps to known theory; extraction scaffold | HUBRIS_NEMESIS |
| Abstract (top) | LLM-generated summaries of clusters/arcs | Bridges layers; human-readable | "Arrogance before fall" |

### 3.2 Honesty caveats (design constraints, not footnotes)

1. **Contaminated emergence.** Episode records and embeddings come from an LLM trained on the very theorists the canon encodes. Clusters will partly rediscover the canon. Therefore: cluster novelty is never accepted as evidence of a new pattern without human review (§3.5), and novelty claims are checked against `similarity_to_canonical`.
2. **Clustering grabs the wrong axis by default.** Naive embedding clustering groups by surface topic (era, region, domain), not story-shape; bag-of-words topic models destroy ordering, and an arc *is* an ordering. Therefore: clustering runs on structural embeddings (§3.3), never raw-prose embeddings. Graph-motif mining (recurring causal subgraphs) is deferred to v2+ — structurally honest but data-hungry.
3. **Framework contamination generalizes caveat 1 (new v0.4).** Post-Turchin and post-Dalio historiography writes framework-shaped narratives; a mechanism signature "found" in a 2019 history of Rome may be the historian's Turchin priors, not Rome. Mechanism-signature validation therefore weights **pre-framework sources** (published before the framework circulated) as the cleaner test of whether the signatures actually recur. Source pub date is already carried as chunk metadata (§6.1); this is where it earns its keep.

### 3.3 Structural embeddings

Each episode gets dual embeddings:

- `surface_embedding`: the raw summary text (used for source dedup / same-event linking).
- `structural_embedding`: an abstraction rendered to a canonical template before embedding — actor mentions replaced by roles (`RISING_POWER`, `INCUMBENT_HEGEMON`, `CREDITOR_CLASS`, `COUNTER_ELITE`, `ASPIRANT_ELITE`, …), places/dates stripped, mechanism tags serialized, and the phase-transition sequence preserved in order:

```
ROLES: rising_power challenges incumbent_hegemon; financier_class funds both
TENSION: security dilemma + trade dependence
MECHANISMS: elite_overproduction, fiscal_distress
SEQUENCE: armament_race -> alliance_hardening -> peripheral_crisis -> commitment_trap
```

**Outcome fields are always excluded from the render (v0.7 — supersedes the earlier "RESOLUTION: (masked in backtests)" line).** Resolution and consequences never enter the structural embedding, for two reasons. (1) *Query/corpus symmetry:* a present-day query has `resolution=None` by definition, so embedding outcomes for corpus episodes but not queries systematically biases every retrieval score by a field only one side has. (2) *Leakage:* retrieval asks "given the situation so far, what followed?" — if the embedding encodes the ending, backtests partially retrieve analogs *by* their endings, defeating §6.6's masking. Outcomes still reach theses through the analogs' stored resolution/consequences fields after retrieval (§6.5 step 5); they just never enter the similarity signal.

Design goal: Athens–Sparta and Wilhelmine Germany–Britain embed near each other; two unrelated 1920s events do not.

### 3.3a Embedding roles: identity vs. analogy (new v0.5 — load-bearing invariant)

The two embedding collections answer two different questions, and consumers must never swap them:

| Question | Embedding | Consumers |
|---|---|---|
| **Identity** — "is this the same happening?" | `surface_embedding` (raw summary) | `SAME_EVENT_AS` resolution (§6.2 stage 5), arc composition (§6.2 stage 6) |
| **Analogy** — "is this the same shape?" | `structural_embedding` (rendered template) | Analog retrieval (§6.5), discovery clustering (§3.4) |

The reason is exactly the structural embedding's design goal: it is place-blind and date-blind *on purpose*, so Athens–Sparta sits next to Germany–Britain. That property is what makes it correct for retrieval and wrong for identity — using structural similarity in composition would happily merge two unrelated credit booms in different scopes and centuries. Any pipeline that decides "same unfolding" or "same event" must score on surface embeddings; arc_type/structural agreement is necessary-but-insufficient context, never the similarity signal.

### 3.4 Discovery pipeline (batch job, run at ≥1000 episodes **or on unclassified-density trigger — v0.4.1, restored v0.6**)

Corpus size is not the only trigger: a growing pool of unclassified episodes (§6.2 stage 4) is direct evidence the canon has a hole. Discovery runs are additionally triggered when the unclassified fraction of new episodes exceeds a threshold (per scope or corpus-wide), and unclassified episodes are prioritized when characterizing new clusters — they are the episodes the canon cannot explain, which is exactly what discovery exists to find.

1. Cluster `structural_embedding`s with HDBSCAN (density-based; no forced k; noise label for one-off episodes). Sweep `min_cluster_size ∈ {5, 8, 12}`; select by stability (bootstrap resampling) not silhouette alone.
2. For each cluster: compute centroid; compute soft membership of each episode to each canonical arc (`similarity_to_canonical: Dict[ArcType, float]` via classifier logits or centroid distance).
3. LLM generates the abstract layer: given 10 representative episodes (nearest centroid + diverse eras), produce name, one-line essence, candidate phase structure, and a distinguishing test ("what makes this NOT hubris–nemesis?").
4. Persist as `DiscoveredArchetype` records; attach `discovered_cluster_id` to episodes. Non-breaking: canonical labels are untouched.

### 3.5 Promotion loop (the taxonomy evolves)

A discovered cluster becomes a promotion candidate when: stable across corpus versions, `max(similarity_to_canonical) < τ` (low overlap with all canonical arcs), size ≥ N, and era/region-diverse (guards against topic clusters masquerading as arcs). Then: LLM drafts arc definition (phases + transition tendencies) → human review → merged into canonical set as a versioned taxonomy change → affected episodes re-classified in batch. **The canon is data, and it grows.** Coherent *provisional arc instances* (§6.2 stage 6) count as supporting evidence in promotion review — a cluster whose episodes compose into believable unfoldings is more likely a real arc than a topic artifact.

### 3.6 The empirical tiebreaker

Discovered archetypes must pay rent. Evaluation harness runs analog retrieval + masked-ending backtests under: (a) canonical-only, (b) canonical + clusters, (c) clusters-only. If (b) doesn't beat (a) on retrieval quality and thesis calibration, discovered layers are decoration and stay out of the forecasting path.

### 3.7 External framework import (new v0.4 — formalizes `provenance="external"`)

Importing an external framework (Dalio, Turchin, Strauss–Howe, I Ching, …) is a versioned, three-part operation. Every import declares **what is imported** and — just as importantly — **what is not**:

| Part | What it is | Lands as |
|---|---|---|
| Arc shapes | Named phase structures + transition tendencies | `ArcDefinition` rows, `provenance="external"` |
| Mechanism terms | The framework's driver variables, as narrative signatures | `Mechanism` vocabulary entries + extraction prompt terms |
| Cycle hypotheses | Scoped cycle trees the framework predicts | `Cycle` rows with `framework_seed` set |

Worked examples:

- **Dalio.** Big Debt Crises ≈ `CREDIT_BOOM_BUST` + a long-term debt cycle at institutional scale; the Changing World Order big cycle ≈ `RISE_OVEREXTENSION` at civilizational scale + the system-scoped hegemonic cycle; his six-stage internal order sequence imports as ordered phases + transitions. **Not imported:** his quantitative determinants (debt/GDP, reserve-currency share). We encode his phase structure; we cannot verify phase *position* his way.
- **Turchin.** Secular cycles (~200y, integrative/disintegrative) at institutional/civilizational scale; the ~50y "fathers and sons" violence cycle at generational scale. Mechanism terms: `elite_overproduction`, `immiseration`, `fiscal_distress` and their narrative signatures. **Not imported:** Seshat-style coded variables, the quantitative PSI. His falsifiable transition claims *are* imported — as mechanism-conditioned `transition_tendencies` the eval harness can test (§6.6).
- **Strauss–Howe.** Saeculum + four turnings at generational scale (`framework_seed="strauss_howe"`). Generational archetypes (Prophet/Nomad/Hero/Artist) attach to **cohort `ActorEntity`s**, which is what makes the archetype dimension representable at all.
- **I Ching (v2+).** A 64-state labeled state machine over scenarios; slots in as an `ArcDefinition` set with external provenance. No mechanism terms; pure shape.

A framework-seeded tree is a **hypothesis label, never a validation claim**. Theses record which framework imports (and versions) were active when generated; disagreements between seeded trees and bottom-up clustering are a first-class research output (§8 step 4).

### 3.8 Mechanism vocabulary (new v0.4)

A small controlled vocabulary (~10–20 terms at bootstrap; versioned like the taxonomy) of structural drivers with defined narrative signatures. Each entry: `id`, `definition`, `narrative_signatures` (what extraction looks for), `source_framework`, `version`. Bootstrap set drawn from Turchin (`elite_overproduction`, `immiseration`, `state_fiscal_distress`, `counter_elite_formation`, `credential_inflation`) and credit-cycle theory (`leverage_buildup`, `credit_contraction`, `collateral_spiral`).

Uses downstream:

1. **Extraction:** mechanisms are first-class tags on `initiating_conditions` / `escalation_mechanics` — queryable and aggregatable per scope and era, not free text.
2. **Transitions:** `ArcDefinition.transition_tendencies` extends from bare `phase → [next phases]` to transitions optionally conditioned on mechanism presence ("distress → panic is more frequent when `leverage_buildup` was tagged in prior phases").
3. **Theses:** `watch_for` indicators draw from the mechanism vocabulary instead of ad-hoc free text — a principled branch-separating indicator set, currently the vaguest part of thesis output.
4. **Per-scope mechanism density over time** becomes a crude narrative-derived index — not Turchin's PSI, but a checkable qualitative analog of it, surfaced alongside per-scope episode density as a thesis confidence input.

---

## 4. Data Model (schema-first; Pydantic-style)

```python
class ArcType(str, Enum):        # canonical layer — versioned, evolving via promotion
    HUBRIS_NEMESIS = "hubris_nemesis"
    CREDIT_BOOM_BUST = "credit_boom_bust"
    RISE_OVEREXTENSION = "rise_overextension"
    REFORM_REACTION = "reform_reaction"
    # ... ~14 at bootstrap; grows via §3.5

class Mechanism(BaseModel):      # NEW v0.4 — controlled structural-driver vocabulary (§3.8)
    id: str                      # "elite_overproduction", "immiseration", ...
    definition: str
    narrative_signatures: list[str]   # what extraction looks for in text
    source_framework: str | None      # "turchin_sdt", "dalio_debt", None = home-grown
    vocabulary_version: str

class ArcDefinition(BaseModel):  # taxonomy-as-data
    arc_type: str
    taxonomy_version: str
    phases: list[str]                                 # ordered
    transition_tendencies: list[TransitionTendency]   # EXTENDED v0.4 (was dict[str, list[str]])
    distinguishing_test: str
    provenance: Literal["canonical", "promoted", "external"]
    source_framework: str | None      # NEW v0.4 — set when provenance="external"

class TransitionTendency(BaseModel):  # NEW v0.4 — mechanism-conditioned transitions
    from_phase: str
    to_phase: str
    base_weight: float                # unconditioned tendency
    conditioning_mechanisms: list[str] = []   # mechanism ids; empty = unconditional
    conditioned_weight: float | None = None   # tendency when mechanisms present
    # Turchin-style falsifiable claims live here: "disintegrative follows
    # elite_overproduction at lag L" is a TransitionTendency the harness can score (§6.6)

class Scope(BaseModel):          # what a cycle tree belongs to
    id: str
    kind: Literal["polity", "civilization", "region", "system", "dyad"]
    name: str                    # "US", "China", "Sinosphere", "INTL_SYSTEM", "US–CHINA"
    parent_scope_id: str | None  # polities can nest under civilizations
    aliases: list[str] = []      # "United States", "USA" — entity resolution target

class Cycle(BaseModel):
    id: str
    scope_id: str                # every cycle tree is scoped; no global phase clock
    scale: Literal["civilizational", "institutional", "generational", "episodic"]
    parent_cycle_id: str | None  # nesting within the SAME scope only
    framework_seed: str | None   # e.g. "turchin_secular", "strauss_howe" — hypothesis label
    framework_import_version: str | None   # NEW v0.4 — which import produced the seed (§3.7)
    time_span: tuple[date | None, date | None]
    phase_annotations: list[ArcAssignment] = []
    is_arc_instance: bool = False   # NEW v0.4 — episodic-scale cycles acting as arc
                                    # instances by convention (§2); set by composition pass
    provisional: bool = False       # v0.4.1, restored v0.6 — instance keyed on
                                    # discovered_cluster_id rather than arc_type
                                    # (§6.2 stage 6); no phase machinery

class CycleMembership(BaseModel):   # many-to-many episode↔cycle, with per-scope reading
    episode_id: str
    cycle_id: str
    reading: ArcAssignment | None   # same episode, different arc role per scope (§2)
    salience: float                 # how central the episode is to this cycle
    phase_coverage: list[int] = []  # NEW v0.4 — which phases of an arc instance this
                                    # episode documents; gaps become visible
    link_status: Literal["attested", "inferred"] = "attested"   # NEW v0.4 (§6.2 stage 6)
                                    # evidentiary standing ONLY — edge *kind* lives in the
                                    # edge type (COMPOSES, CAUSES, ...), never in this field
    review_status: Literal["pending", "approved", "rejected", "auto"] = "auto"
                                    # NEW v0.5 — human review state, orthogonal to
                                    # link_status; "auto" = below review threshold

class ActorEntity(BaseModel):    # NEW v0.4 — persistent identity across episodes (§2)
    id: str
    kind: Literal["person", "institution", "polity", "cohort", "class"]
    name: str
    aliases: list[str] = []
    scope_id: str | None         # entities resolve to scopes where applicable
    cohort_span: tuple[date | None, date | None] | None = None   # birth-year range
    archetype: str | None = None # e.g. Strauss–Howe "prophet" — framework-tagged, versioned

class ActorMention(BaseModel):   # RENAMED v0.4 (was Actor) — per-episode appearance
    name: str                    # as it appears in this episode
    role: str                    # controlled vocab: RISING_POWER, INCUMBENT_HEGEMON,
                                 # COUNTER_ELITE, ASPIRANT_ELITE, ...  (extended v0.4)
    entity_id: str | None        # resolves to ActorEntity; this edge + entity.scope_id
                                 # is what correlates two polities' phase clocks

class ArcAssignment(BaseModel):
    arc_type: str
    phase_index: int
    confidence: float
    rationale: str               # short; stored for audit

class Episode(BaseModel):
    id: str
    title: str
    time_span: tuple[date | None, date | None]
    actors: list[ActorMention]                # UPDATED v0.4
    initiating_conditions: list[str]
    escalation_mechanics: list[str]           # ordered
    mechanism_tags: list[str] = []            # NEW v0.4 — Mechanism ids present (§3.8)
    resolution: str | None                    # None = ongoing / masked
    consequences: list[str]
    arc_assignments: list[ArcAssignment]      # multi-label; may be EMPTY (v0.4.1)
    classification_state: Literal["classified", "unclassified"] = "classified"
                                              # v0.4.1, restored v0.6 — "unclassified" when no
                                              # canonical arc clears τ_class (§6.2 stage 4);
                                              # no forced fit
    discovered_cluster_id: int | None = None
    similarity_to_canonical: dict[str, float] = {}
    cycle_memberships: list[CycleMembership] = []   # many-to-many; includes arc instances
    structural_render: str                    # §3.3 template text
    surface_embedding_id: str
    structural_embedding_id: str
    provenance: list[SourceSpan]              # doc id + char offsets
    pipeline_version: str

class DiscoveredArchetype(BaseModel):
    cluster_id: int
    corpus_version: str
    centroid_embedding_id: str
    size: int
    stability: float             # bootstrap agreement
    llm_name: str; llm_essence: str
    candidate_phases: list[str]
    max_canonical_similarity: float
    promotion_status: Literal["candidate", "promoted", "rejected", "unreviewed"]

class Thesis(BaseModel):
    id: str; created_at: datetime
    situation_episode_id: str
    analog_ids: list[str]
    dominant_continuation: str
    branches: list[Branch]                    # continuation + analog frequency
    watch_for: list[str]                      # UPDATED v0.4 — drawn from Mechanism
                                              # vocabulary where possible, not free text
    resolution_criteria: str                  # so it can be scored later
    taxonomy_condition: Literal["canonical", "hybrid", "clusters"]   # for A/B (§3.6)
    mode: Literal["arc_based", "arc_less"] = "arc_based"
                                              # v0.4.1, restored v0.6 — degraded path (§6.5.8)
    active_framework_imports: list[str] = []  # NEW v0.4 — import versions in effect (§3.7)
    scope_registry_version: str               # NEW v0.4 — promoted from §9 open question
```

**Graph edges** (edge tables in Postgres to start): `CONTAINS` (cycle→cycle, same scope), `MEMBER_OF` (episode→cycle, cross-scope, carries the per-scope reading and link_status), `COMPOSES` (episode→arc-instance cycle, carries phase_coverage — new v0.4, a specialization of MEMBER_OF for is_arc_instance cycles), `PRECEDES`, `CAUSES`, `INSTANTIATES`, `SAME_EVENT_AS`, `MENTION_OF` (actor mention→actor entity — new v0.4), `ACTOR_SCOPE` (entity→scope) — all timestamped, all carrying pipeline_version. `MEMBER_OF` + `ACTOR_SCOPE` are what make cross-polity phase correlation queryable: two scopes' clocks are linked wherever one scope appears as an actor in the other's episodes.

**Attested vs. inferred (v0.4; sharpened v0.5):** `PRECEDES`/`CAUSES` edges still require textual evidence spans. But two books that never reference each other's events can each document beats of one arc — the composition pass may therefore create `COMPOSES`/`MEMBER_OF` links on **surface-embedding similarity plus entity/scope agreement (§3.3a — never structural similarity)**, flagged `link_status="inferred"`. Inferred links never carry causal claims; they claim only "same unfolding." Theses must distinguish which of their supporting links are attested vs. inferred.

**Two orthogonal axes, enforced in schema (new v0.5).** *What kind of edge* is carried by the edge type (`CAUSES`, `COMPOSES`, …); *how we know it* is carried by `link_status`; *whether a human has ratified it* is carried by `review_status`. These never collapse into one enum — a value like `"causal"` alongside `attested`/`inferred` would make the field unanswerable for a causal edge and would break the invariant below. The invariant is a validator/check constraint, not prose:

```python
# edge-level invariants (enforced at write time)
assert not (edge.kind == "CAUSES" and edge.link_status == "inferred")
# equivalently: CAUSES ⇒ attested ⇒ evidence spans present;
# the composition pass can therefore never emit a causal edge
```

---

## 5. High-Level Architecture

```
┌────────────┐   ┌───────────────────┐   ┌─────────────────────────┐
│ Ingestion  │──▶│ Narrative         │──▶│ Knowledge Store         │
│ books/     │   │ Extraction (LLM)  │   │ Postgres:               │
│ articles   │   │ segment→extract→  │   │  episodes/cycles/edges  │
└────────────┘   │ classify→link→    │   │  actor entities         │
                 │ COMPOSE (v0.4)    │   │  pgvector (dual embeds) │
                 └───────────────────┘   │  raw passages           │
                        ▲                └───────────┬─────────────┘
                        │ two-pass                   │
                ┌───────┴──────────┐     ┌───────────▼───────────┐
                │ Taxonomy +       │◀────│ Discovery Pipeline    │
                │ Mechanism Vocab  │     │ HDBSCAN on structural │
                │ versioned arcs + │     │ embeds → archetypes;  │
                │ promotion loop + │     │ unclassified-density  │
                │ framework imports│     │ trigger (v0.4.1)      │
                └──────────────────┘     └───────────────────────┘
┌────────────┐   ┌────────────────────┐
│ Query:     │──▶│ Analog Retrieval + │──▶ Thesis (stored, scoreable;
│ present    │   │ Thesis Generation  │     arc_based | arc_less mode)
│ situation  │   │ (arc-less fallback)│
└────────────┘   └────────────────────┘   ┌────────────────────┐
                                          │ Eval / Backtesting │
                                          │ masked endings +   │
                                          │ taxonomy A/B +     │
                                          │ mechanism claims + │
                                          │ composition fixture│
                                          └────────────────────┘
```

---

## 6. Component Implementation Detail

### 6.1 Ingestion

Format normalization (EPUB/PDF/OCR) → structure-aware parsing (chapters kept as metadata) → narrative-boundary chunking (~2–8k tokens, chapter/section aware). Metadata per chunk: work, author, publication date (load-bearing for pre/post-framework weighting, §3.2.3), historiographic school where known (bias made visible, not laundered). Stable chunk IDs.

### 6.2 Extraction pipeline (staged; each stage = versioned prompt + JSON schema)

1. **Segment:** chunk → candidate episode boundaries + one-liners (cheap model).
2. **Extract:** episode → full Episode record minus classifications (strong model, schema-constrained output). Mechanism tagging happens here, against the versioned vocabulary's narrative signatures (§3.8).
3. **Render:** deterministic code (not LLM) builds `structural_render` from the record — role substitution via controlled vocabulary, mechanism serialization, ordered sequence serialization. Deterministic rendering keeps embeddings comparable across pipeline versions.
4. **Classify (two-pass, with a "none of the above" — v0.4.1, restored v0.6):** pass 1 zero-shot against canonical arcs; pass 2 re-classifies showing k nearest already-labeled neighbors (label stabilization across the corpus; **unclassified episodes are excluded from the neighbor pool, so low-confidence labels never propagate**). Classification is **not a forced choice**: if no canonical arc clears a confidence floor τ_class after pass 2, the episode gets **no** `ArcAssignment` and is marked `classification_state="unclassified"` rather than shoehorned into its least-bad label. Unclassified episodes stay out of the phase-conditioned analog base (§6.5), feed the discovery trigger (§3.4), and are re-attempted on every taxonomy version bump — a promotion (§3.5) is often exactly what claims them.
5. **Link:** same-event resolution via surface embeddings + date/actor overlap; actor mentions resolve to `ActorEntity`s (create-or-match, alias-aware — persons, institutions, cohorts); causal edges proposed by LLM, kept only with textual evidence spans. Cross-source agreement raises confidence; disagreement is preserved as competing narrations.
6. **Compose (v0.4; specified v0.5; extended v0.6):** merge phase-adjacent episodes into arc-instance cycles (`is_arc_instance=True`) across sources, without requiring in-text cross-references — this is what stitches book 1's phases 1–2 to book 2's phases 3–5. Composition is an **identity** decision, so its similarity signal is the surface embedding, never the structural one (§3.3a). The identity-resolution pipeline runs in a fixed, load-bearing order:

   1. **Hard filter — scope partition.** Candidates are partitioned by `scope_id` before anything else; US and Japan episodes are never in the same pool, which eliminates the "two unrelated credit booms" false-merge class by construction. (Scope, not raw location: arcs travel with polities and institutions, not coordinates — a US credit boom has beats in New York and London. Location is only an input to scope resolution.) **Unscoped episodes never merge (v0.7).** An episode with no `scope_id` must not fall into a shared "no scope" pool — that would put an unscoped Japanese and an unscoped US credit boom in the same candidate pool, recreating exactly the false-merge class this filter exists to kill. Unscoped episodes surface as singleton instances (visible, not silently dropped) until scope resolution assigns them; the same rule applies to gap-filling, which may only pull episodes from the instance's own scope.
   2. **Hard-ish filter — actor-entity overlap** above a threshold, on resolved `ActorEntity` ids (alias-normalized name match is acceptable interim debt until entity resolution lands, and must be flagged as such).
   3. **Soft signal — surface-embedding similarity** score.
   4. **Temporal clustering** with per-scale gap thresholds (see below), plus arc_type agreement.
   5. **Phase-sequence continuity check** (phases must be orderable into the arc's phase structure).

   **Per-scale temporal gap thresholds (new v0.5).** A single global gap threshold is wrong by construction: a panic's beats sit weeks–months apart; a civilizational arc's documented beats can sit decades apart, and a global threshold either fragments long arcs or over-merges short ones. Thresholds are parameters per scale (overridable per `ArcDefinition`), and the current values — episodic 2y, institutional 5y, generational 10y, civilizational 40y — are **fixture-tuned hypotheses, not constants**; they are validated (and re-tuned) against the composition fixture (§6.6) and must never be hard-coded.

   **Provisional composition for misfits (v0.4.1, restored v0.6; restated against the v0.5 ordering).** Unclassified episodes have no `arc_type` for step 4's agreement gate and no phase structure for step 5 — under a strict reading they could never compose, even when five unclassified episodes are obviously beats of one unfolding. Under the hybrid condition, composition may therefore alternatively key on shared `discovered_cluster_id`: steps 1–3 apply unchanged (scope partition, entity overlap, surface similarity — identity discipline is not relaxed), step 4's agreement gate uses cluster co-membership in place of arc_type, and step 5 is skipped (clusters have only *candidate* phases). Resulting instances are marked `provisional=True`, carry no phase machinery, and double as evidence in the promotion queue (§3.5) — a coherent provisional instance is a strong argument that its cluster is a real arc. On promotion, provisional instances are re-composed under the new canonical arc_type.

   **Guardrails:** links created without textual evidence are `link_status="inferred"`; inference distance is capped (no merging across large temporal/phase gaps even within threshold chains); instances above a size threshold get `review_status="pending"` and enter the review queue (§6.4, §9); the pass can never emit `CAUSES` edges (invariant, §4). Records per-episode `phase_coverage`, making documentation gaps in an instance visible.

   **Evidence floor (new v0.7).** The identity gates treat missing data as a neutral pass (an acceptable convention for any *single* missing signal), which left a degenerate case open: a pair with no dates, no actors, no embeddings, and no phases passed every gate, making the worst-documented episodes the *easiest* to merge. `is_match` therefore additionally requires a minimum count of signals computed from data actually present on both sides (default 2 of: temporal, actor overlap, surface similarity, phase sequence). Identity is an evidence claim; absence of evidence must never behave like weak evidence for it.

Idempotent stages, checkpointed per document; re-runs keyed by (pipeline_version, taxonomy_version, mechanism_vocabulary_version).

### 6.3 Embedding service

Two collections in pgvector: surface (raw summary) and structural (rendered template). Embedding model pinned per corpus_version; re-embedding is a batch job. Sanity metric maintained as a fixture test: a hand-built set of ~30 cross-era analog pairs (Athens–Sparta ↔ Germany–Britain, etc.) must rank in top-k structural neighbors; failure blocks embedding-model upgrades.

### 6.4 Discovery + promotion (batch)

As §3.4–3.5. Runs per corpus_version; outputs `DiscoveredArchetype` rows and episode back-links. Promotion is a human-in-the-loop admin flow: candidate queue → LLM-drafted `ArcDefinition` → review UI → taxonomy version bump → batch re-classification. The same review UI hosts the arc-instance review queue (§6.2 stage 6) and the framework-import flow (§3.7) — three flavors of "human ratifies structure the machine proposed."

### 6.5 Analog retrieval & thesis generation

1. Present-day text runs through the same extraction pipeline (resolution=None) → structural embedding + phase estimate + mechanism tags.
2. Resolve the situation's scope(s) via mention→entity→scope resolution, and read off the cycle-state vector for each: where each participating scope sits in its own civilizational/institutional/generational clocks. Same-date situations in different scopes produce different vectors by construction — "US, 2026" and "China, 2026" are different retrieval keys.
3. Retrieve k analogs from the structural index; boost/filter by graph context: same arc family, similar cycle-state, and shared mechanism tags — the same arc inside a declining civilizational cycle behaves differently than inside a rising one; this is where the fractal hierarchy earns its keep. Under the hybrid condition, cluster co-membership adds a retrieval feature. Where analogs belong to composed arc instances, retrieval can pull the whole instance, not just the matching episode — **the analog is the story, not the beat.**
4. Dyadic/system queries for coupled situations: because episodes carry many-to-many scoped memberships, retrieval can condition on relative phase — "polity in phase X of arc A facing a rival in phase Y of arc B" — which is a strictly stronger query than matching either side alone. Participating scopes are not independent samples; their clocks are correlated through shared `MEMBER_OF` / `ACTOR_SCOPE` edges, and the retrieval layer exploits rather than ignores that.
5. Pull analogs' phase transitions from their `ArcDefinition` + recorded outcomes: from phase N, what followed, over what timescale, conditioned on what — including mechanism-conditioned tendencies where the situation's mechanism tags match.
6. Strong model synthesizes the `Thesis`: dominant continuation, branch frequencies grounded in the analog set (counts, not vibes), watch-for indicators drawn from the mechanism vocabulary, full citations, attested/inferred link disclosure, active framework-import versions.
7. Thesis stored with resolution criteria and taxonomy_condition for later scoring.
8. **Arc-less degraded mode (v0.4.1, restored v0.6):** if the situation itself fails the classification floor, there is no phase and therefore no phase-completion forecast — and the system says so rather than shoehorning. Fallback: pure structural nearest-neighbor retrieval ("what followed situations shaped like this"), no phase-conditioned transition statistics, cycle-state used only as soft context. The thesis is emitted with `mode="arc_less"`, wider stated uncertainty, and no mechanism-conditioned branch weights. Silent failure and silent shoehorning are both prohibited outcomes; a visible degraded answer is the only honest one. Arc-less theses are scored separately in the harness — they are also a running measure of how much predictive value the arc machinery itself adds over bare structural similarity.

### 6.6 Evaluation & backtesting (build early — this is where the idea lives or dies)

- **Masked-ending harness:** corpus snapshot truncated at year T (resolutions and post-T episodes masked at the data layer, not the prompt layer); system produces theses; scored against ground truth. *(As-built v0.7: the data-layer masking primitives exist — post-T episodes dropped, ongoing episodes returned as copies with resolution/consequences/end_date stripped, so downstream code physically cannot read them. The full snapshot-and-score loop around them is still to be assembled. Known residual leakage, stated honestly: episode summaries are prose written by historians who knew the ending, and the LLM itself remembers famous endings — masking controls what the system sees, not what the model knows.)*
- **Leakage control (the hard problem — the LLM already knows how WWI ended):** score analog-selection quality separately from narrative plausibility; judge sees only thesis + ground truth; prefer obscure regional histories for test cases; strongest tests use genuinely post-training-cutoff events.
- **Baselines:** persistence ("things continue"), bare LLM with no retrieval system, simple reference-class forecasting. If the machinery can't beat the bare LLM, the structure isn't paying rent. *(As-built v0.7: persistence and bare-LLM baselines implemented; reference-class forecasting not yet.)*
- **Taxonomy A/B (§3.6):** canonical vs hybrid vs clusters-only on (i) retrieval quality against the hand-built analog fixture, (ii) Brier scores on resolved theses' branch frequencies.
- **Mechanism-claim tests (new v0.4):** mechanism-conditioned `TransitionTendency`s are falsifiable — e.g., "disintegrative phase follows `elite_overproduction` signature at lag L." Score them in the masked-ending harness: conditioned vs. unconditioned transition predictions on held-out instances. Run twice — full corpus vs. pre-framework sources only (§3.2.3) — to separate real recurrence from historiographic contamination. Arguably a more interesting research output than the forecasting product itself.
- **Composition fixture (v0.4; extended v0.5):** hand-built multi-source arc instances (e.g., one arc whose beats span 3 books) that the composition pass must recover; precision/recall on episode→instance assignment. Must include **near-miss decoys** — episode pairs sharing scope + arc_type + rough temporal proximity that are nonetheless distinct instances (e.g., the 1907 panic vs. the 1920s boom–crash, both US, both `CREDIT_BOOM_BUST`) — since that is the false-merge failure mode the guardrails exist for. The fixture is also the tuning target for the per-scale temporal thresholds (§6.2 stage 6): thresholds are set by fixture performance, not intuition, and must be tuned before they gate production runs. Failure blocks pipeline-version upgrades, same as the analog fixture blocks embedding upgrades.
- **Mechanism A/B (new v0.4):** retrieval and thesis calibration with vs. without mechanism features. Mechanisms must pay rent like everything else; if tagging doesn't improve calibration, it's decoration.

---

## 7. Stack (lean v1)

Python; Prefect (or plain queues) for orchestration, every stage idempotent. Postgres + pgvector as the single store (graph as edge tables; Neo4j only if traversal queries demand it). scikit-learn/HDBSCAN for discovery. LLM API: cheap model for segmentation, strong model for extraction/classification/synthesis. FastAPI + simple web UI: zoomable fractal timeline, episode inspector with sources, arc-instance viewer with phase-coverage gaps, thesis workbench, unified review queue (promotions, arc instances, framework imports).

---

## 8. Build Order

1. **Spike (1–2 wks):** 5–10 books on financial manias (Kindleberger, Mackay, Galbraith, Reinhart–Rogoff). Canonical taxonomy only. Bootstrap a minimal mechanism vocabulary here — mania sources are dense with credit-cycle mechanisms (`leverage_buildup`, `credit_contraction`), so tagging can be validated cheaply from day one. Hand-check segmentation/extraction/classification quality.
2. Structural rendering + dual embeddings; build the 30-pair analog fixture; analog retrieval + thesis generation; masked-ending tests on 1907/1929/1997/2008 vs bare-LLM baseline. **τ_class and the unclassified path land here (v0.4.1) — they gate what enters the analog base, so they precede any calibration claims.**
3. Widen corpus past 1000 episodes → first discovery run (**with unclassified-density trigger active**) → abstract-layer naming → taxonomy A/B.
4. Promotion loop + review UI; scoped cycle hierarchy bootstrap: seed a scope registry (major polities/civilizations + `INTL_SYSTEM`) and per-scope cycle trees via the formalized framework-import flow (§3.7): Turchin/Strauss–Howe/Dalio/dynastic frameworks as versioned hypotheses; mention→entity resolution (`ActorEntity`, including cohorts) — the composition pass (§6.2 stage 6), **provisional composition**, and composition fixture land here, since all need entity resolution; bottom-up clustering proposes cycles the seeds missed — disagreements are the interesting research output. Dyadic retrieval lands here, since it needs populated cycle-state vectors. Full Turchin mechanism vocabulary + mechanism-conditioned transitions + mechanism-claim tests land here too, once per-scope episode density can support them.
5. **v2+:** graph-motif mining; alternative external taxonomies (I Ching 64-state grid as an `ArcDefinition` set with `provenance="external"` — structurally it's a labeled state machine over scenarios, so it slots in as data).

---

## 9. Risks & Open Questions

- **Narrative fallacy, formalized.** The system industrializes exactly the bias Taleb warns about; the only defense is the eval harness and honesty about corpus survivorship (histories over-record dramatic arcs; boring non-events are underdocumented, skewing the analog base).
- **Canon rediscovery masquerading as discovery (§3.2.1):** treat cluster novelty as a hypothesis for human review, never a result.
- **Topic clusters masquerading as arcs (§3.2.2):** era/region-diversity gates in promotion; structural embeddings as the only clustering input.
- **Framework contamination (§3.2.3, new v0.4):** post-Turchin/post-Dalio historiography writes framework-shaped narratives. Mechanism-signature validation weights pre-framework sources; mechanism-claim tests run on the pre-framework slice as the honest condition.
- **Inferred composition manufactures arcs from coincidence (new v0.4):** the composition pass can stitch unrelated episodes into a story that never was. Guardrails: inference-distance caps, human review above a size threshold, `attested`/`inferred` disclosure in theses, and the composition fixture (with near-miss decoys, v0.5) as a regression gate. An inferred instance is a *proposed* story.
- **τ_class trades two failure modes (v0.4.1, restored v0.6):** set the classification floor too low and misfits pollute the phase-conditioned analog base; too high and the analog base starves while the unclassified pool balloons. Track the unclassified fraction per scope and per taxonomy version as a standing health metric — a rising fraction is either a miscalibrated τ_class or a genuine canon gap, and the discovery trigger (§3.4) plus promotion loop is how the two are told apart. Tune τ_class against the analog fixture, not by intuition.
- **Historiographic bias:** check whether theses flip when the corpus mix (source schools) changes.
- **Scope boundaries are themselves contested claims.** Is "the West" one scope or many? Does "China" as a scope span dynastic breaks? Treat the scope registry like the taxonomy — versioned data with hypotheses, not ontology — theses now record `scope_registry_version` (§4).
- **Cohort entities inherit Strauss–Howe's weakest assumption (new v0.4):** that birth-year cohorts are coherent actors at all. Cohort `ActorEntity`s should be treated as framework-tagged hypotheses like everything else imported — if cohort-attached features never improve retrieval or calibration, the archetype dimension is decoration.
- **Corpus geography skews cycle clocks.** An English-language history corpus over-documents Euro-American scopes; non-Western scopes will have sparse cycle trees and thin analog sets, making their phase estimates less reliable exactly where they're least checked. Track per-scope episode density and per-scope mechanism density and surface both as confidence inputs to theses.
- **Leakage remains the single biggest threat to believing your own results.**
- **Realistic ceiling:** scenario structuring with historical base rates — genuinely useful for investment theses — rather than point prediction.

---

## 10. Future Improvements: Widening the Sensorium (roadmap, not commitments)

*Context. Discovery (§3.4) is LLM-mediated, schema-bounded, and corpus-limited: clustering runs on `structural_render`s, so the role vocabulary and render template are the perceptual bottleneck of the whole discovery apparatus. A pattern the representation cannot express produces no cluster — not because it isn't in history, but because the sensorium can't see it. The current seeds (roles, canon, corpus, fixtures) are finance/geopolitics-skewed; the architecture is not. Everything below is data and vocabulary work except items 10.2 and 10.5, which are the two genuine design changes.*

### 10.1 Widen the role vocabulary

Extend the controlled role vocabulary beyond political-economy roles, along the axes classical story taxonomies already map:

- **Political-dramatic:** `USURPER`, `PRETENDER`, `REGENT`, `COURT_FAVORITE`, `KINGMAKER`, `PURGED_FACTION`, `HEIR_APPARENT`
- **Proppian-functional:** `DONOR`/`PATRON`, `DISPATCHER`, `FALSE_HERO`, `HELPER`, `TRAITOR_WITHIN`
- **Social-mobility:** `PARVENU`, `DECLINING_HOUSE`, `DISPOSSESSED_CLASS`
- **Religious/ideological:** `PROPHET_FIGURE`, `HERESIARCH`, `TRUE_BELIEVER_MOVEMENT`, `APOSTATE`

Keep it controlled (~60–80 roles, not 500): roles that appear once never form clusters; the point is forcing analogous actors across millennia into the same token. Admission test per candidate role: *would two episodes a thousand years apart share this token in a way that reveals shape?*

**Modern applicability is a requirement, not a hope.** Roles name structural positions, not costumes: a "court" is any power center where proximity to a principal outweighs formal office (an administration's inner circle, a founder-CEO's kitchen cabinet, a politburo); succession crises, favorites' falls, boardroom usurpations, and schisms (corporate, ideological, open-source) all render through these roles today. Forecasting depends on this (§6.5 step 1 renders the *present* through the same vocabulary). Two modern wrinkles to design for: (a) modern role-holders are often **distributed collectives** (an investor syndicate as kingmaker, a movement as pretender) — extraction must be prompted that roles can be filled by collective `ActorEntity`s, or it will only spot roles wearing individual faces; (b) some modern structural positions may be **genuinely novel** (e.g., a platform gatekeeper controlling distribution rails) — detected via extraction residue (10.5), not assumed away.

### 10.2 Extend the render template (design change — new relation lines)

Roles alone cannot express what distinguishes the intrigue/betrayal family of arcs; the template needs relational and epistemic structure:

- **`RELATIONS:`** — typed edges between roles (*trusts, betrays, patronizes, displaces, conspires_with*). Betrayal is an edge, not a role; without this line, intrigue arcs render identically to open conflicts.
- **`CONCEALED:` / `REVEALED:`** — information asymmetry. Conspiracy and fraud arcs are *defined* by who knows what when (a false-hero unmasking arc is unrenderable without it).
- **`REVERSAL:`** — peripeteia marker: whether fortune inverted (the signature of tragedy and rags-to-riches alike).
- **`STAKES:`** — stake type (throne, fortune, salvation, survival), so structural matching collapses a succession war and a price war only when they genuinely share shape.

Every template change re-embeds the corpus, so template versions are batch-epoch experiments, versioned and A/B'd against the analog fixture like everything else (§6.3).

### 10.3 Widen the corpus (interleaved, not sequential)

Deliberate tranches beyond economic history: dynastic/court history (Plutarch, Tacitus, Gibbon, succession chronicles — the densest intrigue material), religious and movement history (schisms, heresies, revivals), revolutions (including revolutions consuming their children), colonial encounters, institutional histories (churches, armies, universities — slow institutional-scale arcs), and biography (rise-and-fall at personal scale). Discipline: tag tranches with school and era (per §6.1), and **interleave tranches rather than exhausting finance first** — discovery on a lopsided corpus mints finance-shaped archetypes that later data cannot dislodge without full re-clustering.

### 10.4 Seed story-theory arcs + non-financial fixtures

Import classical story taxonomies via the §3.7 flow (each declaring what is and isn't imported, paying rent per §3.6): **Propp** (31 ordered functions + 7 roles — nearly an `ArcDefinition` avant la lettre), **Booker** (seven plots with phase sequences), **Polti** (36 dramatic situations — enriches the *tension* vocabulary rather than phases), **Frye** (four mythoi — abstract-layer altitude). Seed candidate canonical arcs: `SUCCESSION_CRISIS`, `CONSPIRACY_EXPOSURE`, `FAVORITE_RISE_FALL`, `REVOLUTION_DEVOURS_OWN`, `FALSE_HERO_UNMASKED`. Extend the analog fixture with cross-era **non-financial** pairs (Sejanus ↔ a Ming court purge; Wars of the Roses ↔ a Sengoku succession struggle; French Revolution ↔ Iranian Revolution): until such pairs rank in top-k structural neighbors, there is no evidence the widened sensorium works.

Epistemic caveat (extends §3.2): these taxonomies describe *told stories*, not events (the Hayden White problem — narrative shape may be added at the writing stage). Importing them tests whether history-as-written follows story logic; even pure *validation* — which of Booker's plots recur as event-structures, at what frequencies, with what transition statistics — is a real research result. When a discovered cluster resembles the hero's journey, three explanations always compete: the pattern is in history, in historiography, or in the LLM's priors; pre-framework slicing and human review are partial defenses, not full separation.

### 10.5 Vocabulary-evolution loop (design change — closes the last static loop)

The canon evolves (§3.5) but the vocabulary that *feeds* discovery is currently static, which silently caps what can ever be discovered. Give the role vocabulary and render template the same lifecycle as the taxonomy:

1. Track **extraction residue**: a role-fit confidence per actor mention (analogous to τ_class); actors that fit no role well accumulate as residue.
2. Residue density (per era, per scope) triggers **vocabulary-revision proposals** (LLM-drafted, like promotion candidates).
3. Human review → vocabulary version bump → batch re-render → re-cluster.

Monitor **modern-source residue as a first-class metric from the spike onward**: high residue on contemporary texts specifically means present-day situations render poorly, which is a direct hit to forecast quality (§6.5 step 1), not merely a coverage gap. It is also the detector for genuinely novel 21st-century structural positions (10.1b).

**Cost, stated honestly:** every vocabulary or template bump invalidates embeddings corpus-wide. Widening is therefore punctuated, not continuous — batch epochs, exactly what the pinned-model/versioned re-render machinery (§6.3) assumes. Sequencing: 10.1 and 10.4's fixtures can begin alongside build-order step 2; 10.2 and 10.5 are template/schema changes best landed at a corpus-version boundary; 10.3 runs continuously from step 3 onward.

---

## 11. As-Built Status (v0.7 reconciliation — NarrativeGenerator repo)

*This section maps the design to the implementation as of 2026-07-10. It is descriptive, not normative: where the code deliberately diverges, the divergence is named and either adopted into the design or flagged as debt. Overall shape: the implementation is a faithful build of the v0.5 branch's load-bearing invariants plus, as of v0.7, the core v0.4.1 no-fit path. The remaining gaps are concentrated in entity resolution, the framework-import/promotion flows, and the full evaluation harness.*

### 11.1 Implemented (verified in code)

| Design element | Where | Notes |
|---|---|---|
| Dual embeddings, identity/analogy discipline (§3.3a) | `retrieval/embeddings.py`, `composition/identity.py` | Separate surface/structural columns; composition scores on surface only, no structural fallback |
| Outcome-free structural render (§3.3, v0.7) | `retrieval/embeddings.py` | Resolution/consequences excluded; mechanisms serialized; **requires corpus re-embed** |
| Composition pass, fixed stage order (§6.2 stage 6) | `composition/pipeline.py`, `identity.py` | Scope partition → actor gate → surface signal → per-scale temporal + arc agreement → phase continuity; hard gate cascade, not weighted sum |
| Unscoped-episode singleton rule (v0.7) | `composition/pipeline.py` | Unscoped episodes never merge; gap-filling is scope-restricted |
| Evidence floor (v0.7) | `composition/identity.py` | ≥2 concrete signals required for `is_match`; default configurable |
| Per-scale temporal thresholds (§6.2) | `composition/identity.py` | 2y/5y/10y/40y — **untuned hypotheses**, marked as such |
| Near-miss decoy fixture (§6.6) | `tests/fixtures/composition_fixture.py` | 1907-panic-vs-1920s-boom decoy present; small (1 positive, 1 negative case) — needs growth before threshold tuning means much |
| Causal-attestation invariant (§4) | `models.py` validator + DB CHECK | `CAUSES` ⇒ attested, enforced at model and DB layers |
| link_status / review_status orthogonal axes (§4) | `models.py`, `storage/orm_models.py` | As specified |
| τ_class + unclassified state (§6.2 stage 4, v0.7) | `extraction/pipeline.py`, `extraction/config.py` | Floor default 0.5, env-overridable (`NE_TAU_CLASS`) — **untuned**; unclassified episodes carry no arc assignment, excluded from arc-conditioned analog base |
| Arc-less thesis mode (§6.5.8, v0.7) | `thesis/generator.py`, `retrieval/analog_retrieval.py` | Unclassified query → bare structural NN retrieval, confidence capped LOW, uncertainty stated, `mode="arc_less"` persisted |
| Data-layer masking + baselines (§6.6, v0.7) | `evaluation/masking.py`, `evaluation/baselines.py` | Masked copies (drop post-T, strip outcomes); persistence + bare-LLM baselines |
| Scoped cycles, many-to-many memberships, phase_coverage, `is_arc_instance` (§2, §4) | `models.py`, `storage/` | Per-scope readings via `CycleMembership.reading` |
| Mechanism tagging + retrieval feature + conditioned transitions (§3.8) | `models.py`, `extraction/`, `retrieval/` | See divergence 11.2.1 |
| Staged extraction, versioned prompts (§6.2) | `extraction/` | Segmentation → extraction → classification → linking |
| Discovery scaffolding (§3.4) | `taxonomy/service.py` | HDBSCAN on embeddings, taxonomy-as-data, `DiscoveredArc` records |
| Brier scoring + calibration (§6.6) | `evaluation/metrics.py`, `backtest.py` | Per-thesis scoring; full harness loop still open (11.3) |

### 11.2 Partial / deliberate divergences

1. **Mechanism vocabulary is a hardcoded enum**, not versioned `Mechanism` records with `narrative_signatures`/`source_framework` (§3.8 as specified). Descriptions live in `extraction/config.py` beside a `CURRENT_MECHANISM_VOCAB_VERSION` constant. Acceptable at spike scale; must become data before framework imports or pre-framework validation can work.
2. **Episode carries a single `arc_type`/`arc_phase` plus `secondary_arcs`**, not the §4 `arc_assignments: list[ArcAssignment]`. Functionally close (multi-label representable), structurally divergent; `ArcAssignment` exists and is used by `CycleMembership.reading`.
3. **Actor roles are free text** ("President", "Banker"), not the §3.3 controlled vocabulary, and the render includes free-text conditions/mechanics — so proper nouns can leak into the structural embedding through prose. The §3.3 cross-era design goal is therefore **unverified**: the 30-pair analog fixture (§6.3) does not exist yet, and until it does there is no evidence the place-blind property holds in practice.
4. **Second-pass classification is unwired** (prompt written, `TODO` in `extraction/pipeline.py`). When wired, unclassified episodes must be excluded from the neighbor pool (noted in code).
5. **Discovery selects clusters by silhouette score**, not bootstrap stability (§3.4 says "stability… not silhouette alone").
6. **`scope_id` is a bare string** — no `Scope` registry (kind/parent/aliases), no `scope_registry_version` on theses. Inconsistent scope labels from extraction cause false *splits* (the v0.7 unscoped rule prevents the false-*merge* side).
7. **`Cycle.framework_source` is a label only** — the §3.7 three-part import flow (arc shapes + mechanism terms + cycle hypotheses, versioned) does not exist.
8. **Review statuses exist in schema; no review queue or UI** consumes them (§6.4, §7).
9. **Thesis lacks `taxonomy_condition` and `active_framework_imports`** — no taxonomy A/B (§3.6) is possible yet. `mode` and `taxonomy_version` are recorded.

### 11.3 Not built (open design, no code)

- **ActorEntity/ActorMention split + cohorts (§2):** composition runs on alias-normalized name matching, flagged in code as interim debt. Blocks cross-polity phase correlation and Strauss–Howe cohorts.
- **Unclassified-density discovery trigger (§3.4)** and the **promotion loop end-to-end (§3.5)** — the unclassified pool now exists (v0.7) and can be measured, but nothing watches it yet.
- **Provisional cluster-keyed composition (§6.2 stage 6, v0.4.1).**
- **30-pair analog fixture (§6.3), taxonomy A/B (§3.6), mechanism-claim tests, mechanism A/B (§6.6)** — and the assembled masked-ending loop around the v0.7 masking primitives. This cluster is the highest-priority remaining work: until it exists, no calibration claim is interpretable.
- **Framework import flow (§3.7), pre-framework source weighting (§3.2.3).** Publication date is carried in ingestion metadata, so the weighting has its input when built.
- **Dyadic/system retrieval conditioning on relative phase (§6.5 step 4).**
- **FastAPI UI, review queue, Prefect orchestration (§7);** idempotent re-runs keyed by (pipeline_version, taxonomy_version, mechanism_vocabulary_version) are not enforced — `Episode` has a `version` int, not the keyed re-run machinery.
- **Everything in §10** (sensorium widening) — roadmap, unchanged.

### 11.4 Standing cautions carried into v0.7

- τ_class (0.5) and the per-scale temporal thresholds are **untuned defaults**; both must be tuned against fixtures (§6.6, §9) before any production run's outputs are trusted.
- The v0.7 render change invalidates existing structural embeddings; re-embed before comparing retrieval results across the boundary.
- Same-event resolution remains name-match-based until entity resolution lands, so duplicate narrations of one event can still enter analog counts as independent evidence (§9 narrative-fallacy risk, unmitigated).
