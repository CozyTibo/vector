"""ASGI application entry."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vector.api.http.routes import admin, auth, health, me, onboarding
from vector.api.http.routes.connectors import build_connectors_router
from vector.api.http.routes.debug_canonical import build_debug_canonical_router
from vector.api.http.routes.debug_projections import build_debug_projections_router
from vector.settings import get_settings

logger = logging.getLogger(__name__)


def _cors_allow_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
    return [o.strip() for o in raw.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.env in ("staging", "production") and settings.vector_use_mock_connectors:
        msg = "VECTOR_USE_MOCK_CONNECTORS must be false in staging/production"
        raise RuntimeError(msg)
    logger.info("Vector API starting (env=%s)", settings.env)
    yield
    logger.info("Vector API shutting down")


app = FastAPI(title="Vector", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(admin.build_admin_router())
app.include_router(auth.router)
app.include_router(build_connectors_router())
app.include_router(build_debug_projections_router(), prefix="/debug", tags=["debug"])
app.include_router(build_debug_canonical_router(), prefix="/debug", tags=["debug"])
app.include_router(me.router)
app.include_router(onboarding.build_onboarding_router())
