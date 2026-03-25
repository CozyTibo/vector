"""ASGI application entry."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vector.api.http.routes import auth, health, me
from vector.api.http.routes.connectors import build_connectors_router
from vector.api.http.routes.debug_projections import build_debug_projections_router


def _cors_allow_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
    return [o.strip() for o in raw.split(",") if o.strip()]


app = FastAPI(title="Vector", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router)
app.include_router(build_connectors_router())
app.include_router(build_debug_projections_router(), prefix="/debug", tags=["debug"])
app.include_router(me.router)
