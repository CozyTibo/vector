# Base app and repository setup (specification)

This document describes how we intend to lay out the **repository**, **Docker Compose–based local/runtime stack**, **Makefile** developer workflow, and **minimal backend skeleton** before any connectors or domain pipeline logic. It aligns with:

- [`technical-vision-execution-intelligence-platform.md`](technical-vision-execution-intelligence-platform.md) — modular monolith, Python, Postgres-oriented data plane.
- [`engineering-guidelines.md`](engineering-guidelines.md) — `backend/` layout, domains, thin routes, dedicated **test DB**, layering.
- [`senior-standards.md`](senior-standards.md) — typing, migrations, tests, logging, file size.

**Status:** the repository implements this specification (root `Makefile`, `docker-compose.yml`, `backend/`, `frontend/`). Treat this file as the canonical description of that layout.

---

## 1. Repository layout (monorepo)

Single git repository with a clear split so a **frontend** can land later without colliding with the API.

```text
vector/
  backend/                 # Python application (this spec)
  frontend/                 # Vite + React (Docker dev server); calls API via VITE_API_BASE_URL
  DOCS/                     # Architecture and engineering docs
  docker-compose.yml        # Root orchestration: Postgres + backend (and later services)
  Makefile                  # Developer commands (wrap docker compose)
  .env.example              # Documented variables (copy to `.env`, gitignored)
  .gitignore
  README.md                 # Pointers to DOCS and quick start (once implemented)
  docker/                   # e.g. postgres init scripts (create `vector_test`, extensions)
```

**Principle:** Anything installable/runnable for the product backend lives under **`backend/`**. The repo root only holds **shared infra** (compose, make, env template) and documentation.

---

## 2. What the “base app” includes (before connectors)

Goal: a **runnable** backend shell with **no business features**, proving:

- HTTP API process (e.g. FastAPI) with **`GET /health`** (liveness, no DB) and **`GET /ready`** (DB `SELECT 1` + Redis `PING` when `REDIS_URL` is set).
- **Postgres** with two logical databases: **`vector`** (dev/default) and **`vector_test`** (tests only) — per engineering guidelines §7.3.
- **Alembic** migrations on **`vector`** and **`vector_test`** in CI/Make targets.
- **Structured package layout** matching the guidelines: `domains/` (empty or stub packages), `api/http/` (routers only), `infrastructure/db/` (Base, future models), `settings`, `contracts` as needed later.
- **Frontend** (`frontend/`): Dockerized Vite dev server; browser fetches API at `VITE_API_BASE_URL` (e.g. `http://localhost:8000`). Backend **CORS** via `CORS_ORIGINS` (must include the UI origin, e.g. `http://localhost:5173`).
- **pytest** with tests mirroring `src` layout; **no tests against `vector`** for routine runs.
- **mypy** (`strict` or project-agreed level) on `src` (and relaxed rules for `tests` if needed).
- **Optional but recommended:** **Ruff** (lint + format) in the same toolchain; **not** a substitute for mypy.

**Out of scope for the base milestone:** connectors, raw ingestion tables, normalization, graph, auth beyond stubs, frontend code.

---

## 3. Docker Compose principles

- **No host Python/Postgres required** for day-to-day work: developers run **`make …`** which invokes **`docker compose`**.
- Services (minimal):
  - **`postgres`**: version pinned (e.g. 16), named volume for data, **healthcheck** (`pg_isready`), init script to **`CREATE DATABASE vector_test`** in addition to the default DB.
  - **`backend`**: image built from **`backend/Dockerfile`**, depends on healthy Postgres, exposes API port (e.g. 8000), loads **`.env`**.
- **Mounts (dev):** optional bind mounts for `backend/src`, `backend/tests`, `backend/alembic` for fast iteration with `--reload` — document tradeoff (prod image should not rely on mounts).
- **Environment:** `.env.example` lists `POSTGRES_*`, `DATABASE_URL` (points at compose service hostname **`postgres`**, not `localhost`, from inside containers), and **`DATABASE_URL_TEST`** for the test database URL.

---

## 4. Makefile targets (required set)

All targets should **assume Docker Compose** unless documented otherwise. Naming can be adjusted; **capabilities** should remain.

| Target | Purpose |
|--------|---------|
| **`help`** | Print available targets and short descriptions |
| **`setup`** / **`build`** | Build images |
| **`up`** | Start stack in background |
| **`down`** | Stop stack |
| **`install`** | First-time path: ensure `.env` exists (e.g. copy from `.env.example`), **build**, **up**, run **migrations** on dev DB |
| **`reinstall`** | Aggressive refresh: **down**, rebuild **no cache**, **up**, **migrate** (document data loss risk on named volumes if user runs `down -v`) |
| **`migrate`** | `alembic upgrade head` against **dev** `DATABASE_URL` |
| **`migrate-down`** | `alembic downgrade -1` (or documented policy) |
| **`migrate-new`** | `alembic revision --autogenerate -m "…"` (requires models + env wiring) |
| **`migrate-test`** | Apply migrations to **`vector_test`** (override `DATABASE_URL` for the one-shot container) |
| **`db-schema`** | Overwrite **`artifacts/db-schema.schema.rb`** with a Rails **`schema.rb`**-style snapshot from the dev DB (reference only) |
| **`db-psql`** | Interactive `psql` into **`vector`** |
| **`db-psql-test`** | Interactive `psql` into **`vector_test`** |
| **`test`** | Run **pytest** with **`DATABASE_URL` = test URL; run `migrate-test` first** so schema matches |
| **`test-unit`** | Optional: pytest excluding `@pytest.mark.integration` |
| **`mypy`** | Run **mypy** on `src/<package>` inside the backend container |
| **`lint`** / **`fmt`** | Optional: **ruff check** / **ruff format** |
| **`check`** | **mypy + lint + test** — single pre-push gate |
| **`shell`** | Shell into backend container for debugging |

**Implementation notes:**

- Make should pass **`DATABASE_URL`** explicitly for **`migrate-test`** and **`test`** so accidental use of the dev DB is impossible (guidelines §7.3).
- **`db-schema`** requires Postgres running (`compose up`); document failure mode if not.

---

## 5. Backend package layout (inside `backend/`)

Suggested structure consistent with [`engineering-guidelines.md`](engineering-guidelines.md) §8:

```text
backend/
  Dockerfile
  pyproject.toml              # deps + [tool.pytest] + [tool.mypy] + optional ruff
  README.md                   # short pointer to root DOCS
  alembic.ini
  alembic/
    env.py
    versions/
  src/
    vector/
      settings.py
      domains/                  # stubs until connectors/ingestion/… exist
      api/
        http/
          main.py
          routes/
      infrastructure/
        db/
          base.py
          models/
      contracts/                # optional, when cross-cutting DTOs appear
  tests/
    vector/
      api/
        http/
      ...                       # mirror src
```

- **`PYTHONPATH`** / editable install: Dockerfile runs **`pip install -e .`** (or uv equivalent) so `vector` imports resolve.
- **Alembic `env.py`:** reads **`DATABASE_URL`** from environment; `target_metadata` from shared `Base` once models exist.

---

## 6. Initial migration

- First revision may be **empty** (`upgrade`/`downgrade` `pass`) to validate tooling, or create minimal extensions/enums if we standardize early.
- After first ORM models land: **`make migrate-new msg="…"`** with autogenerate, then review (senior-standards migration safety).

---

## 7. Testing and mypy policy

- **Tests:** mirror **`src`** tree under **`tests/`**; unit tests for pure logic; integration/acceptance tests marked `@pytest.mark.integration` and using **`vector_test`** only.
- **mypy:** run in CI and via **`make mypy`**; configuration in **`pyproject.toml`** (`strict` on `src`, pragmatic overrides on `tests` if needed).
- **No `print()`** in production or tests (senior-standards).

---

## 8. Security and hygiene (baseline)

- **`.env`** gitignored; secrets never committed.
- **Root `README.md`**: after implementation, should only say “copy `.env.example` → `.env`”, **`make install`**, health URL — details stay in **DOCS**.
- **`artifacts/`** (generated schema dumps): gitignored or committed intentionally — team choice; document in README when decided.

---

## 9. Future extensions (out of base scope)

- **Frontend** folder: Vite/Next/etc. with its own `Dockerfile` and compose service when needed.
- **Workers** (Celery, Dramatiq, Temporal): additional compose services sharing the same image or a slim worker image.
- **CI** (GitHub Actions / other): `make check` in a job using the same compose file or a CI-optimized variant.

---

## 10. Related documents

| Document | Role |
|----------|------|
| [`technical-vision-execution-intelligence-platform.md`](technical-vision-execution-intelligence-platform.md) | Product/architecture vision |
| [`engineering-guidelines.md`](engineering-guidelines.md) | Modules, layers, errors, tests, file size |
| [`senior-standards.md`](senior-standards.md) | Daily Python/SQL/MR bar |

---

## Document history

| Date | Change |
|------|--------|
| 2026-03-24 | Initial specification (documentation only; implementation reverted per team request) |
| 2026-03-24 | Base app scaffold added: Compose, Makefile, `backend/` package, Alembic, tests, mypy/ruff |
