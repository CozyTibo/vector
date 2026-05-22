# Vector frontend

Vite + React + TypeScript. Calls the backend API (see root `docker-compose` / `Makefile`).

**Local API URL:** in the repo root `.env`, set `VITE_API_BASE_URL` to the backend origin only (e.g. `http://localhost:8000`), never a tenant-scoped path. For `npm run dev` in `frontend/`, you can leave `VITE_API_BASE_URL=` empty: Vite proxies `/admin`, `/auth`, and other API routes to `VITE_API_PROXY_TARGET` (defaults to `http://127.0.0.1:8000`), which avoids CORS. If the backend runs on another port (e.g. `8080`), set `VITE_API_PROXY_TARGET=http://localhost:8080`.
