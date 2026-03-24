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
| `make db-schema` | Overwrite `artifacts/db-schema.schema.rb` with a Rails-style snapshot |

## Sign-in (product auth)

- **Google:** set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `SECRET_KEY` in `.env`. In [Google Cloud Console](https://console.cloud.google.com/), add redirect URI `http://localhost:8000/auth/google/callback`.
- **Email + password:** `POST /auth/register` and `POST /auth/login` (see OpenAPI at `/docs`); the UI has register/log-in forms. Same session cookie as Google.
- **Dev tenant:** after migrations, run `make seed-basic-tenant` to create tenant slug `dev` (and user `dev@vector.local` / `changeme` from `.env.example`) if that slug is not in the DB yet.

## GitHub connector (connect only)

After `make migrate`, set the `GITHUB_*` variables in `.env` (see `.env.example`). In the GitHub App settings, use the same **User authorization callback URL** as `GITHUB_USER_CALLBACK_URL`, or `http://127.0.0.1:8000/connectors/github/callback` if you rely on `GITHUB_API_PUBLIC_BASE_URL`. Signed-in users can open **Connect GitHub** on the frontend or `GET /connectors/github/install` on the API. Connector status for all registered providers is `GET /connectors`. The callback does not rely on the session cookie (signed `state` carries tenant + user), so `127.0.0.1` vs `localhost` on the API no longer breaks the return from GitHub.

**If you see “GitHub API error while reading installation”:** JWT `iss` must be **`GITHUB_CLIENT_ID`** (already fixed in code). Docker Compose often **truncates multi-line** `GITHUB_APP_PRIVATE_KEY` in `.env` — use a **single line** with `\n`, or **`GITHUB_APP_PRIVATE_KEY_PATH`** to a mounted PEM file, then check `docker compose logs backend` for the exact GitHub HTTP response.
