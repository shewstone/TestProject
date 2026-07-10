# T5 — Minimal Scope registry: protect composition's stage-1 hard filter

**Priority:** P1
**Design refs:** §2 (scoped cycles), §4 (`Scope` model, `scope_registry_version`), §6.2 stage 6.1, §9 ("scope boundaries are contested claims"), §11.2.6
**Depends on:** nothing. T2's scrub consumes the alias table.
**Effort:** M

## Problem

`scope_id` is a bare string emitted by LLM extraction. The scope partition is
composition's **first hard filter** — the mechanism the design credits with
eliminating the false-merge class "by construction" — but "US",
"United States", and "USA" are three partitions today. The v0.7 unscoped rule
prevents false *merges*; inconsistent labels still cause false *splits*
(§11.2.6), which fragment arc instances and undercount analogs.

## Scope

### 5a. Model + storage (matches §4)

```python
class Scope(BaseModel):
    id: str                      # slug: "us", "china", "intl_system"
    kind: Literal["polity", "civilization", "region", "system", "dyad"]
    name: str
    parent_scope_id: str | None
    aliases: list[str] = []
```

- `ScopeORM` + migration + `ScopeRepository` (get, get_by_alias, list, create).
- `SCOPE_REGISTRY_VERSION = "scope-v0.1.0"` — the registry is versioned data,
  not ontology (§9): "the West" vs many, dynastic China as one scope — these
  are hypotheses someone will revise.

### 5b. Seed registry (`data/scope_registry_v0.1.0.json`, loaded by migration or bootstrap script)

~25 entries covering the spike corpus: US, UK, France, Germany, Austria(-Hungary),
Russia, China, Japan, Netherlands, Spain, Italy, Ottoman, Rome, Athens, Sparta,
Persia, Byzantium + `INTL_SYSTEM` + civilizational parents (Western Europe,
Sinosphere) + dyads as needed (US–CHINA, ATHENS–SPARTA). Aliases carry the
work: "United States", "USA", "America", "the Union"; "Weimar Germany",
"Wilhelmine Germany", "Prussia"→(germany, with a comment — contested, see §9);
dynastic aliases ("Ming", "Qing")→china per the doc's China-spans-dynasties
default hypothesis.

### 5c. Resolver (`extraction/scope_resolution.py`)

- `resolve_scope(raw: str) -> str | None`: normalize (casefold, strip
  punctuation/articles) → exact alias match → None. **No fuzzy matching** in
  v1: a wrong scope silently poisons the composition partition, while an
  unresolved scope falls into the v0.7 singleton path, which is visible and
  safe. Same asymmetry logic as the evidence floor.
- Unresolved raw strings are logged with counts (the promotion queue for new
  aliases — same human-ratifies-structure pattern as §6.4).

### 5d. Integration points

- Extraction linking stage: pass raw location/polity guess through resolver;
  store resolved id or None.
- Composition: partitions on resolved ids only (behavior unchanged, inputs cleaner).
- `Thesis.scope_registry_version`: new field + column, stamped at generation
  (§4 requires it; §11.2.9 lists it missing).
- T2 scrub: registry names+aliases are the place-token replacement table.

## Acceptance criteria

- [ ] Scope model/ORM/repo + seed registry of ~25 scopes with aliases.
- [ ] `resolve_scope("United States") == resolve_scope("USA") == "us"`;
      unknown → None + logged.
- [ ] Composition test: two episodes labeled "US" and "United States" now land
      in one partition (was: two).
- [ ] Theses record scope_registry_version.
- [ ] Registry bump = data change + version bump, no code change.

## Out of scope

- Scope *inference* beyond alias lookup (LLM-assisted resolution) — needs the
  review queue first.
- Cross-scope phase correlation (`ACTOR_SCOPE` edges, §11.3) — needs
  ActorEntity, different ticket.

## Risks

- A seed registry bakes in exactly the contested boundaries §9 warns about.
  Mitigation is the versioning itself + logging unresolved strings so the
  registry grows from corpus evidence rather than a priori geography.
