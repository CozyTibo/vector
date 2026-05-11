# Local mock connectors (development only)

Mock HTTP server for **GitHub REST**, **Linear GraphQL**, **Notion REST subset**, **Google Calendar events subset (Calls)**, and **Slack Web API subset**, plus a full **mock company dataset** used by Manager Insights mock mode. **Docker Compose** starts it as the **`mock-connectors`** service (`0.0.0.0:9183` in-container, port **9183** on the host). **Makefile** can run the same app on **127.0.0.1** only for a host-only backend. The Vector backend exchanges Linear OAuth codes with **real** `https://api.linear.app/oauth/token`, resolves viewer/org with **real** `https://api.linear.app/graphql`, then sends **ingestion** GraphQL to this mock when `VECTOR_USE_MOCK_CONNECTORS=true`.

**Do not** enable this in production, CI, or AWS. Server-side rules: `VECTOR_USE_MOCK_CONNECTORS=true` is valid only when `ENV=development`.

Strategy: [`DOCS/strategy/local-mock-connectors-and-fixtures.md`](../../DOCS/strategy/local-mock-connectors-and-fixtures.md).  
Seed audit (contents, usage, gaps): [`DOCS/strategy/mock-data-seed-audit.md`](../../DOCS/strategy/mock-data-seed-audit.md).  
**Phase 04 (identity & continuity):** hostile deterministic mock scenarios, personas, and replay-drift taxonomy — [`DOCS/cortex/04-identity/phase-04-mock-data-strategy.md`](../../DOCS/cortex/04-identity/phase-04-mock-data-strategy.md).

## Prerequisites

- Python 3.11+ with backend dependencies (`fastapi`, `uvicorn`).
- From repo root, `PYTHONPATH` must include `backend/src` and `backend` (the `Makefile.mock` targets set this).

## Start mocks

**Recommended (Docker Compose):** from the repo root, `docker compose up` builds and runs **`mock-connectors`** alongside postgres/backend/frontend. The backend container is configured with `VECTOR_MOCK_CONNECTOR_BASE_URL=http://mock-connectors:9183`.

**Host-only backend** (uvicorn on your machine, no Compose):

```bash
make -f Makefile.mock mock-connectors-up
```

Do **not** run both Compose `mock-connectors` and `make mock-connectors-up` at once — they contend for host port **9183**.

Health (host): `http://127.0.0.1:9183/health` (includes current `seed`).

- GitHub-shaped routes: `http://127.0.0.1:9183/...` (same paths as `https://api.github.com/...`).
- Linear GraphQL (used by backend in mock mode): `http://127.0.0.1:9183/linear/graphql`. Ingestion uses **`operationName`** (e.g. `LinearIngestIssues`, `LinearIngestComments`, `LinearIngestTeams`, …) matching `vector.domains.ingestion.linear_graphql_sync`. The mock also exposes `POST /linear/oauth/token` for ad-hoc testing; **ingestion uses a real Linear access token** from `api.linear.app/oauth/token` when not in mock mode.
- Notion subset (used by backend in mock mode): `http://127.0.0.1:9183/notion/v1/search`, `/notion/v1/databases/{id}`, `/notion/v1/databases/{id}/query`, `/notion/v1/blocks/{id}/children`.
- Calls subset (Google Calendar events): `http://127.0.0.1:9183/google-calendar/v3/calendars/{calendarId}/events`.
- Slack subset (Web API POST methods): `http://127.0.0.1:9183/slack/api/users.list`, `conversations.list`, `conversations.history`, `conversations.replies`.

### Admin (debug)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/admin/reseed?seed=<int>` | Regenerate in-memory dataset (no uvicorn restart). |
| `GET` | `/admin/dataset` | Summary counts for `github`, `linear`, `slack`, `notion`, `calls`. |
| `GET` | `/admin/dataset/full` | Full deterministic company dataset (`github`, `linear`, `slack_events`, `notion`, `calls`, edges, patterns). |
| `GET` | `/admin/scenarios` | Scenario slugs present in the dataset (strategy §11). |

Reseed from Makefile (mock server must be running):

```bash
make -f Makefile.mock mock-reseed SEED=3
```

GitHub list endpoints include a **`Link`** header (`rel="next"`, `prev`, `first`, `last`) like production, using the request URL as the base.

## Run the Vector API against mocks

1. **Docker Compose:** `docker compose up` — mocks + URL for the API are already wired.
2. **Host-only API:** start mocks (`make -f Makefile.mock mock-connectors-up`), then:

```bash
make -f Makefile.mock dev-mock
# export ENV=development
# export VECTOR_USE_MOCK_CONNECTORS=true
# export VECTOR_MOCK_CONNECTOR_BASE_URL=http://127.0.0.1:9183
# export VECTOR_MOCK_SEED=42
```

3. Run `uvicorn app.main:app` from `backend/` with `PYTHONPATH` set (see Makefile).

## Switch back to real APIs

```bash
make -f Makefile.mock dev-real
```

Unset `VECTOR_MOCK_CONNECTOR_BASE_URL` and set `VECTOR_USE_MOCK_CONNECTORS=false`.

## Regenerate dataset JSON

```bash
make -f Makefile.mock mock-dataset
```

Writes `backend/mock_connectors/fixtures/generated/dataset.json` (gitignored; optional).

## Validate dataset

```bash
make -f Makefile.mock mock-validate
```

By default this validates the **live** `generate_dataset(VECTOR_MOCK_SEED)` output (not a stale `dataset.json`). To validate the checked-in JSON snapshot instead, set `MOCK_VALIDATE_USE_JSON=1`.

## Stop mocks

```bash
make -f Makefile.mock mock-connectors-down
```

## Environment variables

| Variable | Purpose |
|----------|---------|
| `VECTOR_USE_MOCK_CONNECTORS` | `true` only with `ENV=development` — backend uses mock base URLs. |
| `VECTOR_MOCK_CONNECTOR_BASE_URL` | Unified mock base, default `http://127.0.0.1:9183`. |
| `VECTOR_MOCK_SEED` | Deterministic dataset seed (default `42`). |

## Layout

- `fixtures/company_generator.py` — Nexora dataset orchestration.
- `fixtures/execution_stories.py` — deterministic execution scenarios (timelines, relations, PR budget).
- `fixtures/nexora_content.py` — product copy and comment arcs.
- `github_mock/` — GitHub REST handlers.
- `linear_mock/` — Linear OAuth + GraphQL handlers.
- `unified.py` — single ASGI app.
- `../Dockerfile.mock-connectors` — slim image used by Compose service **`mock-connectors`**.
