# Vector frontend

Vite + React + TypeScript. Calls the backend API (see root `docker-compose` / `Makefile`).

**Local API URL:** in the repo root `.env`, set `VITE_API_BASE_URL` to the backend origin only (e.g. `http://localhost:8000`), never a tenant-scoped path.

For `npm run dev` on the host, copy `frontend/env.development.sample` to `frontend/.env.development` and keep `VITE_API_BASE_URL` empty. Vite then proxies `/admin`, `/auth`, and other API routes to `VITE_API_PROXY_TARGET` (from repo `.env`, default `http://127.0.0.1:8000`), which avoids CORS. If `frontend/.env.development` sets `VITE_API_BASE_URL=http://localhost:8000`, the browser calls the API cross-origin and you need `CORS_ORIGINS=http://localhost:5173` on the backend.
