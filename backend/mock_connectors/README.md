# Local mock connectors (development only)

Mock HTTP server for **GitHub REST** and **Linear OAuth + GraphQL**. Binds to **127.0.0.1** only.

**Do not** enable this in production, CI, or AWS. Server-side rules: `VECTOR_USE_MOCK_CONNECTORS=true` is valid only when `ENV=development`.

Strategy: [`DOCS/strategy/local-mock-connectors-and-fixtures.md`](../../DOCS/strategy/local-mock-connectors-and-fixtures.md).

## Prerequisites

- Python 3.11+ with backend dependencies (`fastapi`, `uvicorn`).
- From repo root, `PYTHONPATH` must include `backend/src` and `backend` (the `Makefile.mock` targets set this).

## Start mocks

```bash
make -f Makefile.mock mock-connectors-up
```

Health: `http://127.0.0.1:9183/health` (includes current `seed`).

- GitHub-shaped routes: `http://127.0.0.1:9183/...` (same paths as `https://api.github.com/...`).
- Linear: `http://127.0.0.1:9183/linear/graphql`, `http://127.0.0.1:9183/linear/oauth/token`.

### Admin (debug)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/admin/reseed?seed=<int>` | Regenerate in-memory dataset (no uvicorn restart). |
| `GET` | `/admin/dataset` | JSON with `seed`, `github` (repos, PRs, commits, GitHub issues), and `linear` (org name, teams, projects, epics, issues, users, comments, relations, workflow states). |
| `GET` | `/admin/scenarios` | Scenario slugs present in the dataset (strategy §11). |

Reseed from Makefile (mock server must be running):

```bash
make -f Makefile.mock mock-reseed SEED=3
```

GitHub list endpoints include a **`Link`** header (`rel="next"`, `prev`, `first`, `last`) like production, using the request URL as the base.

## Run the Vector API against mocks

1. Start mocks (above).
2. Export:

```bash
make -f Makefile.mock dev-mock
# then run uvicorn / docker with those variables, e.g.:
# export ENV=development
# export VECTOR_USE_MOCK_CONNECTORS=true
# export VECTOR_MOCK_CONNECTOR_BASE_URL=http://127.0.0.1:9183
# export VECTOR_MOCK_SEED=42
```

3. Start the backend as you usually do (`uvicorn app.main:app` or Docker Compose with env overrides).

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

- `fixtures/company_generator.py` — Nexora dataset.
- `github_mock/` — GitHub REST handlers.
- `linear_mock/` — Linear OAuth + GraphQL handlers.
- `unified.py` — single ASGI app (loopback bind enforced via Makefile / uvicorn `--host`).
