# Vector frontend

Vite + React + TypeScript. Calls the backend API (see root `docker-compose` / `Makefile`).

**Local API URL:** set `VITE_API_BASE_URL` in the repo root `.env` (default `http://localhost:8000`). The browser loads the page from the dev server and fetches the API from that URL, so it must be reachable from your machine.
