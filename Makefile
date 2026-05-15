# Vector — developer workflows via Docker Compose.
# See DOCS/base-app-and-repository-setup.md

COMPOSE ?= docker compose
BACKEND_SERVICE := backend
FRONTEND_SERVICE := frontend
POSTGRES_SERVICE := postgres
REDIS_SERVICE := redis
CELERY_WORKER_SERVICE := celery-worker
DOTENV := .env

POSTGRES_USER ?= vector
POSTGRES_PASSWORD ?= vector
POSTGRES_DB ?= vector
DEV_DB_URL ?= postgresql+psycopg://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@postgres:5432/$(POSTGRES_DB)
TEST_DB_URL ?= postgresql+psycopg://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@postgres:5432/vector_test

.PHONY: help setup build build-backend up down logs logs-frontend restart install life reinstall migrate migrate-down migrate-repair migrate-repair-test migrate-new migrate-test seed-basic-tenant db-schema routes octs-openapi db-psql db-psql-test db-drop shell test test-unit mypy lint fmt check frontend-build mock-help celery-tasks celery-restart celery-inspect redis-monitor celery-logs

mock-help:
	@$(MAKE) -f Makefile.mock help-mock

help:
	@echo "Vector — Makefile (Docker Compose)"
	@echo ""
	@echo "  make setup / build   Build images"
	@echo "  make build-backend   Build only the API image (picks up requirements.txt changes)"
	@echo "  make install         Create .env if needed, build, up, migrate (dev DB)"
	@echo "  make life            install, migrate, up, test (full local sanity lane)"
	@echo "  make up / down       Start or stop stack"
	@echo "  make frontend-build  docker compose build frontend (after package.json / lock changes)"
	@echo "  make migrate         repair alembic_version if needed, then alembic upgrade head (dev DB)"
	@echo "  make migrate-down    alembic downgrade -1"
	@echo "  make migrate-repair  reset alembic_version to repo HEAD (dev DB; also run before migrate)"
	@echo "  make migrate-repair-test  same for vector_test (also run before migrate-test)"
	@echo "  make migrate-new     make migrate-new msg=\"description\""
	@echo "  make migrate-test    alembic upgrade on vector_test"
	@echo "  make seed-basic-tenant  Dev DB: create tenant from SEED_* if slug missing"
	@echo "  make db-schema       Rails-style schema snapshot to artifacts/ (stack must be up)"
	@echo "  make routes          list HTTP routes (grouped by tag)"
	@echo "  make octs-openapi   regenerate Phase 05 OCTS walk OpenAPI (RULE API-0)"
	@echo "  make db-psql         psql on dev DB"
	@echo "  make db-psql-test    psql on test DB"
	@echo "  make db-drop         DROP + recreate empty dev DB $(POSTGRES_DB), then run make migrate"
	@echo "  make test            rebuild backend image if needed, migrate-test, pytest"
	@echo "  make test-unit       rebuild backend image if needed, pytest (no integration)"
	@echo "  make mypy / lint / fmt   (mypy checks src/vector + tests per pyproject)"
	@echo "  make check           mypy + lint + test"
	@echo "  make reinstall       down, rebuild --no-cache, up, migrate"
	@echo "  make logs-frontend   docker compose logs -f frontend"
	@echo "  Note: reinstall keeps DB volume; use 'docker compose down -v' to wipe data."
	@echo "  make mock-help          local GitHub/Linear mocks (Makefile.mock; dev-only)"
	@echo "  make celery-tasks       list Celery task names (from app.worker; no worker required)"
	@echo "  make celery-inspect     ask running workers: registered / active / stats (stack + worker up)"
	@echo "  make redis-monitor      stream all Redis commands (verbose; Ctrl+C to stop)"
	@echo "  make celery-logs        follow celery-worker logs (readable task activity)"

setup: $(DOTENV)
	$(COMPOSE) build

$(DOTENV):
	@test -f $(DOTENV) || (cp .env.example $(DOTENV) && echo "Created $(DOTENV) from .env.example")

build: $(DOTENV)
	$(COMPOSE) build

# Ensures dependency changes in backend/requirements.txt are in the image before run/test.
build-backend: $(DOTENV)
	$(COMPOSE) build $(BACKEND_SERVICE)

up: $(DOTENV)
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f $(BACKEND_SERVICE)

logs-frontend:
	$(COMPOSE) logs -f $(FRONTEND_SERVICE)

restart: down up

install: $(DOTENV) build up migrate
	@echo "OK — API http://localhost:$${BACKEND_PORT:-8000}/health"
	@echo "    UI  http://localhost:$${FRONTEND_PORT:-5173}/"

life: $(DOTENV)
	$(MAKE) install
	$(MAKE) migrate
	$(MAKE) up
	$(MAKE) test

reinstall: down
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d
	$(MAKE) migrate

frontend-build: $(DOTENV)
	$(COMPOSE) build frontend

migrate: $(DOTENV) build-backend
	@$(MAKE) migrate-repair
	$(COMPOSE) run --rm -e DATABASE_URL=$(DEV_DB_URL) $(BACKEND_SERVICE) alembic upgrade head

migrate-down: $(DOTENV) build-backend
	$(COMPOSE) run --rm -e DATABASE_URL=$(DEV_DB_URL) $(BACKEND_SERVICE) alembic downgrade -1

# Stamps head when alembic_version references a missing revision (branch switch). Safe if table missing.
migrate-repair: $(DOTENV) build-backend
	$(COMPOSE) run --rm -e DATABASE_URL=$(DEV_DB_URL) $(BACKEND_SERVICE) python -m vector.scripts.repair_alembic_version

migrate-repair-test: $(DOTENV) build-backend
	$(COMPOSE) run --rm -e DATABASE_URL=$(TEST_DB_URL) $(BACKEND_SERVICE) python -m vector.scripts.repair_alembic_version

migrate-new: $(DOTENV) build-backend
	@test -n "$(msg)" || (echo 'Usage: make migrate-new msg="description"' && exit 1)
	$(COMPOSE) run --rm -e DATABASE_URL=$(DEV_DB_URL) $(BACKEND_SERVICE) alembic revision --autogenerate -m "$(msg)"

migrate-test: $(DOTENV) build-backend
	@$(MAKE) migrate-repair-test
	$(COMPOSE) run --rm -e DATABASE_URL=$(TEST_DB_URL) $(BACKEND_SERVICE) alembic upgrade head

# Creates tenant SEED_TENANT_SLUG + password user if slug not in DB (see .env.example).
seed-basic-tenant: $(DOTENV)
	$(COMPOSE) run --rm -e DATABASE_URL=$(DEV_DB_URL) $(BACKEND_SERVICE) python -m vector.scripts.seed_basic_tenant

# Overwrites artifacts/db-schema.schema.rb each run (timestamp only inside the file).
db-schema: $(DOTENV)
	@mkdir -p artifacts
	@_out=artifacts/db-schema.schema.rb; \
	$(COMPOSE) run --rm -e DATABASE_URL=$(DEV_DB_URL) $(BACKEND_SERVICE) \
		python -m vector.scripts.dump_db_schema > "$$_out"; \
	echo "Wrote $${_out}"

routes: $(DOTENV)
	$(COMPOSE) run --rm $(BACKEND_SERVICE) python -m vector.scripts.list_routes

# Phase 05 **RULE API-0** — regenerate ``DOCS/cortex/05-traversal/schemas/generated/octs-walk-api-v1.openapi.json``.
octs-openapi: $(DOTENV) build-backend
	$(COMPOSE) run --rm -v "$(CURDIR)/DOCS:/app/DOCS:rw" $(BACKEND_SERVICE) python -m vector.scripts.generate_octs_walk_openapi

db-psql: $(DOTENV)
	$(COMPOSE) exec $(POSTGRES_SERVICE) psql -U "$(POSTGRES_USER)" -d "$(POSTGRES_DB)"

db-psql-test: $(DOTENV)
	$(COMPOSE) exec $(POSTGRES_SERVICE) psql -U "$(POSTGRES_USER)" -d vector_test

# Terminates backends, DROP DATABASE (one psql each: DROP cannot run in a transaction),
# then CREATE DATABASE so ``make migrate`` can connect immediately.
db-drop: $(DOTENV)
	@echo "Resetting database $(POSTGRES_DB) (requires postgres service: make up)…"
	@$(COMPOSE) exec -T $(POSTGRES_SERVICE) psql -U "$(POSTGRES_USER)" -d postgres -v ON_ERROR_STOP=1 -c \
		"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$(POSTGRES_DB)' AND pid <> pg_backend_pid();"
	@$(COMPOSE) exec -T $(POSTGRES_SERVICE) psql -U "$(POSTGRES_USER)" -d postgres -v ON_ERROR_STOP=1 -c \
		"DROP DATABASE IF EXISTS $(POSTGRES_DB);"
	@$(COMPOSE) exec -T $(POSTGRES_SERVICE) psql -U "$(POSTGRES_USER)" -d postgres -v ON_ERROR_STOP=1 -c \
		"CREATE DATABASE $(POSTGRES_DB) OWNER $(POSTGRES_USER);"
	@echo "OK — empty $(POSTGRES_DB) ready. Run: make migrate"

shell: $(DOTENV)
	$(COMPOSE) run --rm $(BACKEND_SERVICE) bash

test: $(DOTENV) migrate-test
	$(COMPOSE) run --rm -e DATABASE_URL=$(TEST_DB_URL) $(BACKEND_SERVICE) python -m pytest -q

test-unit: $(DOTENV) build-backend
	$(COMPOSE) run --rm $(BACKEND_SERVICE) python -m pytest -q -m "not integration"

mypy: $(DOTENV)
	$(COMPOSE) run --rm $(BACKEND_SERVICE) python -m mypy

lint: $(DOTENV)
	$(COMPOSE) run --rm $(BACKEND_SERVICE) python -m ruff check src tests

fmt: $(DOTENV)
	$(COMPOSE) run --rm $(BACKEND_SERVICE) python -m ruff format src tests

check: mypy lint test
	@echo "check: OK"

# --- Celery / Redis (broker) — stack should be up for exec-based targets ---

# Lists tasks registered on the Celery app (import-time); does not require a worker.
celery-tasks: $(DOTENV)
	@echo "Celery tasks (excluding celery.* builtins):"
	@$(COMPOSE) run --rm $(BACKEND_SERVICE) python -c "from app.worker import app; print('\n'.join(sorted(k for k in app.tasks if not k.startswith('celery.'))))"

# Celery does not reload Python when ./backend/src is bind-mounted; restart after task edits.
celery-restart: $(DOTENV)
	$(COMPOSE) restart $(CELERY_WORKER_SERVICE)

# Broadcast to workers via Redis — requires celery-worker (and Redis) up.
celery-inspect: $(DOTENV)
	@echo "=== inspect registered ==="
	@$(COMPOSE) exec $(CELERY_WORKER_SERVICE) celery -A app.worker inspect registered
	@echo ""
	@echo "=== inspect active ==="
	@$(COMPOSE) exec $(CELERY_WORKER_SERVICE) celery -A app.worker inspect active
	@echo ""
	@echo "=== inspect stats ==="
	@$(COMPOSE) exec $(CELERY_WORKER_SERVICE) celery -A app.worker inspect stats

# Raw stream of every command Redis receives (includes Celery broker traffic). Very noisy.
redis-monitor: $(DOTENV)
	@$(COMPOSE) exec $(REDIS_SERVICE) redis-cli MONITOR

# Human-readable: which tasks ran, errors, retries (requires celery-worker service).
celery-logs: $(DOTENV)
	@$(COMPOSE) logs -f $(CELERY_WORKER_SERVICE)
