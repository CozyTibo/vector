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

## Sign-in (product auth)

- **Google:** set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `SECRET_KEY` in `.env`. In [Google Cloud Console](https://console.cloud.google.com/), add redirect URI `http://localhost:8000/auth/google/callback`.
- **Email + password:** `POST /auth/register` and `POST /auth/login` (see OpenAPI at `/docs`); the UI has register/log-in forms. Same session cookie as Google.
- **Dev tenant:** after migrations, run `make seed-basic-tenant` to create tenant slug `dev` (and user `dev@vector.local` / `changeme` from `.env.example`) if that slug is not in the DB yet.
