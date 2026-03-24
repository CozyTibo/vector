# Vector — developer workflows via Docker Compose.
# See DOCS/base-app-and-repository-setup.md

COMPOSE ?= docker compose
BACKEND_SERVICE := backend
FRONTEND_SERVICE := frontend
POSTGRES_SERVICE := postgres
DOTENV := .env

POSTGRES_USER ?= vector
POSTGRES_PASSWORD ?= vector
POSTGRES_DB ?= vector
DEV_DB_URL ?= postgresql+psycopg://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@postgres:5432/$(POSTGRES_DB)
TEST_DB_URL ?= postgresql+psycopg://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@postgres:5432/vector_test

.PHONY: help setup build up down logs logs-frontend restart install reinstall migrate migrate-down migrate-new migrate-test seed-basic-tenant db-schema routes db-psql db-psql-test shell test test-unit mypy lint fmt check

help:
	@echo "Vector — Makefile (Docker Compose)"
	@echo ""
	@echo "  make setup / build   Build images"
	@echo "  make install         Create .env if needed, build, up, migrate (dev DB)"
	@echo "  make up / down       Start or stop stack"
	@echo "  make migrate         alembic upgrade head (dev DB)"
	@echo "  make migrate-down    alembic downgrade -1"
	@echo "  make migrate-new     make migrate-new msg=\"description\""
	@echo "  make migrate-test    alembic upgrade on vector_test"
	@echo "  make seed-basic-tenant  Dev DB: create tenant from SEED_* if slug missing"
	@echo "  make db-schema       Rails-style schema snapshot to artifacts/ (stack must be up)"
	@echo "  make routes          list HTTP routes (grouped by tag)"
	@echo "  make db-psql         psql on dev DB"
	@echo "  make db-psql-test    psql on test DB"
	@echo "  make test            migrate-test then pytest on test DB"
	@echo "  make test-unit       pytest excluding @integration"
	@echo "  make mypy / lint / fmt"
	@echo "  make check           mypy + lint + test"
	@echo "  make reinstall       down, rebuild --no-cache, up, migrate"
	@echo "  make logs-frontend   docker compose logs -f frontend"
	@echo "  Note: reinstall keeps DB volume; use 'docker compose down -v' to wipe data."

setup: $(DOTENV)
	$(COMPOSE) build

$(DOTENV):
	@test -f $(DOTENV) || (cp .env.example $(DOTENV) && echo "Created $(DOTENV) from .env.example")

build: $(DOTENV)
	$(COMPOSE) build

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
	@echo "OK — API http://localhost:$${BACKEND_PORT:-8000}/health/live"
	@echo "    UI  http://localhost:$${FRONTEND_PORT:-5173}/"

reinstall: down
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d
	$(MAKE) migrate

migrate: $(DOTENV)
	$(COMPOSE) run --rm -e DATABASE_URL=$(DEV_DB_URL) $(BACKEND_SERVICE) alembic upgrade head

migrate-down: $(DOTENV)
	$(COMPOSE) run --rm -e DATABASE_URL=$(DEV_DB_URL) $(BACKEND_SERVICE) alembic downgrade -1

migrate-new: $(DOTENV)
	@test -n "$(msg)" || (echo 'Usage: make migrate-new msg="description"' && exit 1)
	$(COMPOSE) run --rm -e DATABASE_URL=$(DEV_DB_URL) $(BACKEND_SERVICE) alembic revision --autogenerate -m "$(msg)"

migrate-test: $(DOTENV)
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

db-psql: $(DOTENV)
	$(COMPOSE) exec $(POSTGRES_SERVICE) psql -U "$(POSTGRES_USER)" -d "$(POSTGRES_DB)"

db-psql-test: $(DOTENV)
	$(COMPOSE) exec $(POSTGRES_SERVICE) psql -U "$(POSTGRES_USER)" -d vector_test

shell: $(DOTENV)
	$(COMPOSE) run --rm $(BACKEND_SERVICE) bash

test: $(DOTENV) migrate-test
	$(COMPOSE) run --rm -e DATABASE_URL=$(TEST_DB_URL) $(BACKEND_SERVICE) pytest -q

test-unit: $(DOTENV)
	$(COMPOSE) run --rm $(BACKEND_SERVICE) pytest -q -m "not integration"

mypy: $(DOTENV)
	$(COMPOSE) run --rm $(BACKEND_SERVICE) mypy src/vector

lint: $(DOTENV)
	$(COMPOSE) run --rm $(BACKEND_SERVICE) ruff check src tests

fmt: $(DOTENV)
	$(COMPOSE) run --rm $(BACKEND_SERVICE) ruff format src tests

check: mypy lint test
	@echo "check: OK"
