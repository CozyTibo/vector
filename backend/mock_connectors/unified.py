"""Unified local mock: GitHub + Linear APIs + full company fixture payloads.

**Docker Compose** runs this on `0.0.0.0:9183` as the `mock-connectors` service. **Makefile**
`mock-connectors-up` binds **127.0.0.1** only for host-only dev. Not for production or CI.

Dataset is loaded at import time from `VECTOR_MOCK_SEED` and can be **reseeded** via
`POST /admin/reseed?seed=` without restarting the process.
"""

from __future__ import annotations

from fastapi import FastAPI

from mock_connectors.admin_api import build_admin_router
from mock_connectors.github_mock.routes.rest import build_github_router
from mock_connectors.linear_mock.server import build_linear_router
from mock_connectors.runtime_state import state

app = FastAPI(title="Vector mock connectors", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mock": "connectors", "seed": str(state.seed)}


app.include_router(build_github_router(lambda: state.data["github"]))
app.include_router(build_linear_router(lambda: state.data["linear"]), prefix="/linear")
app.include_router(build_admin_router())
