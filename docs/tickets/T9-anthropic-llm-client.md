# T9 — Anthropic LLM client: Sonnet 5 extraction, Haiku segmentation

**Priority:** P0 (blocks all real extraction — Tier-1 item 1 of the production-readiness list)
**Design refs:** §7 ("cheap model for segmentation, strong model for extraction/classification/synthesis"), §6.2 (versioned prompts + JSON schema per stage)
**Depends on:** nothing
**Effort:** M

## Problem

The extraction pipeline cannot call any LLM usable today:

- `AnthropicClient` is a commented-out stub in the provider factory —
  `NE_LLM_PROVIDER=anthropic` raises `LLMError: Unsupported provider`.
- The config's Anthropic default model is `claude-3-opus-20240229`,
  **retired January 2026** (404s).
- `temperature=0.0` is hardcoded through the call paths; current Claude
  models (Sonnet 5, Opus 4.8/4.7) removed sampling parameters — sending
  `temperature` returns a 400.

## Scope

### 9a. `AnthropicClient` (`extraction/client.py`)

- `anthropic.AsyncAnthropic`, injectable for tests; rely on the SDK's
  built-in retries (429/5xx, `max_retries`) instead of duplicating tenacity.
- **Never send sampling parameters.** The `LLMClient` interface accepts
  `temperature` for the OpenAI path; the Anthropic client ignores it
  (current Claude models reject it with a 400; determinism steering is
  prompt-side).
- Check `stop_reason` before reading content: `refusal` → `LLMError`
  (visible failure, orchestrator already records per-stage errors);
  `max_tokens` → `LLMError` naming the truncation.
- `complete_with_json`: parse the first text block; strip markdown fences
  before `json.loads` (models sometimes wrap JSON in ``` fences).
- Typed error chain per SDK guidance: `BadRequestError` /
  `AuthenticationError` / `APIStatusError` / `APIConnectionError` →
  `LLMError` with cause.

### 9b. Model defaults (chosen with user 2026-07-11: Sonnet, not Opus)

| Setting | Default |
|---|---|
| `NE_LLM_PROVIDER` | `anthropic` |
| `NE_LLM_MODEL` / extraction / classification / linking | `claude-sonnet-5` |
| `NE_SEG_MODEL` (segmentation — the §7 "cheap model" stage) | `claude-haiku-4-5` |

All env-overridable per stage; switching a stage to Opus later is a
one-variable change. OpenAI path stays functional for
`NE_LLM_PROVIDER=openai` (its stale defaults are not this ticket's problem).

### 9c. Compose wiring

`app` and `server` services: `NE_LLM_PROVIDER=anthropic`,
`NE_LLM_MODEL=claude-sonnet-5`; `ANTHROPIC_API_KEY` already passes through
and the watcher already gates extraction on it.

## Acceptance criteria

- [ ] `NE_LLM_PROVIDER=anthropic` constructs a working client (test).
- [ ] Requests carry model + max_tokens and **no** `temperature`/`top_p`
      (test asserts absence).
- [ ] Refusal and truncation stop reasons surface as `LLMError` (test).
- [ ] Fenced JSON responses parse (test).
- [ ] No retired model ID anywhere in config.

## Out of scope (follow-ups, noted honestly)

- **Prompt caching** — needs the static instruction block split into
  `system` (cacheable prefix) with only the chunk in the user turn;
  today's prompts interleave them. Worth doing with the prompt-versioning
  work; do not fake it with a marker on a varying prefix.
- **Structured outputs** (`output_config.format` with the stage's JSON
  schema) — the right end state for §6.2's schema-per-stage design, but
  requires formalizing each stage's schema; land with prompt v2.
- **Message Batches API** for corpus runs (50% cost) — needs a
  batch-submission path in the watcher; separate ticket when corpus-scale
  ingestion starts.
