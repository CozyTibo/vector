# Vector

Execution intelligence platform — monorepo.

- **`backend/`** — Python API (FastAPI) and data plane.
- **`frontend/`** — Reserved for admin/product UI.
- **`DOCS/`** — Architecture and engineering standards.

## Quick start

Requires **Docker** (daemon running).

```bash
cp .env.example .env
make install
```

- API health: http://localhost:8000/health/live  
- Frontend (checks API): http://localhost:5173/  
- Full tooling: `make help`  
- Specification: [`DOCS/base-app-and-repository-setup.md`](DOCS/base-app-and-repository-setup.md)

## Common commands

| Command | Purpose |
|--------|---------|
| `make test` | Migrate test DB, run pytest |
| `make mypy` | Typecheck |
| `make db-psql` | SQL shell on dev DB |
| `make db-schema` | Dump schema SQL to `artifacts/` |
