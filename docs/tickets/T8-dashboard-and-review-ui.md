# T8 — Dashboard: processing queue, arc-formation view, review queue

**Priority:** P1
**Design refs:** §7 ("FastAPI + simple web UI: ... arc-instance viewer with phase-coverage gaps, ... unified review queue"), §6.4 (human ratifies structure), §6.2 stage 6 guardrails (review_status)
**Depends on:** T7 (documents feed the queue)
**Effort:** M–L

## Problem

Nothing serves the system's state: processing progress is only visible
in logs, arc instances only via SQL, and the `review_status` fields
(schema'd since v0.5) have no consumer — §11.2.8 lists "no review queue
or UI" as standing debt. The design is explicit that composed structure
above a size threshold requires human ratification; without a UI that
flow cannot exist.

## Scope

### 8a. FastAPI app (`narrative_engine/api/`)

- App served by uvicorn on port 8000 (compose service `server`), with
  the T7 watcher running as a lifespan background task (single
  always-on container: watcher + API + dashboard).
- Session handling via a `get_session` dependency (test-overridable).
- JSON endpoints:
  - `GET /api/health` — liveness + corpus counts.
  - `GET /api/documents` — the processing queue (T7 rows, newest first).
  - `GET /api/arc-instances` — arc-instance cycles with their member
    episodes, per-episode phase, dates, and review/link status — the
    payload the arc-formation view renders. Phase-coverage gaps must be
    derivable (that's the §7 "arc-instance viewer with phase-coverage
    gaps").
  - `GET /api/review-queue` — CycleMemberships and EpisodeLinks with
    `review_status="pending"`, joined with episode/cycle titles.
  - `POST /api/review/membership/{id}` and `/api/review/link/{id}`
    with `{"decision": "approved" | "rejected"}` — writes
    `review_status`; the only mutation the UI performs.

### 8b. Dashboard (single static page, no build step)

Server-rendered shell + vanilla JS polling the JSON endpoints (~3s):

- **Queue panel:** documents with live status badges, chunk/episode
  counts, duplicate rows visibly flagged with what they duplicate,
  failures with their error.
- **Arc-formation panel:** one lane per arc instance; the arc's phase
  sequence drawn as segments (boom → euphoria → distress → panic →
  revulsion etc.), filled where episodes document them, hollow where
  gaps remain — arcs visibly "fill in" as processing runs. Episode dots
  with titles on hover; inferred links rendered distinctly from
  attested (§4 disclosure discipline extends to the UI).
- **Review panel:** pending memberships/links with approve/reject
  buttons hitting the POST endpoints.

### 8c. Compose/deploy

- `server` service in docker-compose: runs `alembic upgrade head` then
  uvicorn; mounts `./data`; exposes 8000. Dockerfile gains the `web`
  extra.
- **No auth** — bind assumption is localhost/dev. Flagged as a hard
  precondition for any non-local deployment (production-readiness
  Tier 3).

## Acceptance criteria

- [ ] `docker compose up server` → dashboard on :8000 shows queue, arcs,
      review panels; watcher picks up drops into ./data/raw.
- [ ] Approve/reject persists review_status (API test).
- [ ] Arc payload includes per-phase coverage and link_status; endpoint
      tests cover documents/arc-instances/review flows.
- [ ] Dashboard renders with zero JS dependencies (inline vanilla JS).

## Out of scope

- Auth, multi-user, websockets (polling is fine at this scale).
- Promotion-queue and framework-import review flavors (§6.4 lists
  three; this ticket lands the arc-instance one the schema already
  supports; the other two need their own aggregates first).
- Thesis workbench and fractal timeline (§7) — separate ticket when
  theses are generated routinely.
