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
from vector.api.http.routes.connectors import slack as slack_routes
from vector.api.http.routes.debug_canonical import build_debug_canonical_router
from vector.api.http.routes.debug_projections import build_debug_projections_router
from vector.api.http.routes.slack_manager_onboarding import build_slack_manager_onboarding_router
from vector.settings import get_settings

logger = logging.getLogger("app")


def _cors_allow_origins() -> list[str]:
    # Comma-separated; override entirely with CORS_ORIGINS in ECS (e.g. staging-only list).
    default = (
        "http://localhost:5173,"
        "https://d3lwynjhzjqd60.cloudfront.net,"
        "https://www.myvector.co,"
        "https://myvector.co"
    )
    raw = os.environ.get("CORS_ORIGINS", default)
    return [o.strip() for o in raw.split(",") if o.strip()]


def _cors_origin_regex() -> str | None:
    """Development only: credentialed CORS for SPA on common private LAN origins."""
    if os.environ.get("VECTOR_DEV_CORS_LAN", "1").strip().lower() in ("0", "false", "no"):
        return None
    try:
        settings = get_settings()
    except Exception:
        return None
    if settings.env != "development":
        return None
    return (
        r"^http://("
        r"localhost(:\d+)?|"
        r"127\.0\.0\.1(:\d+)?|"
        r"192\.168\.\d{1,3}\.\d{1,3}(:\d+)?|"
        r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?|"
        r"172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3}(:\d+)?"
        r")$"
    )


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

_cors_kw: dict = {
    "allow_origins": _cors_allow_origins(),
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}
_cors_rx = _cors_origin_regex()
if _cors_rx:
    _cors_kw["allow_origin_regex"] = _cors_rx
app.add_middleware(CORSMiddleware, **_cors_kw)

app.include_router(health.router)
app.include_router(admin.build_admin_router())
app.include_router(auth.router)
app.include_router(build_connectors_router())
app.include_router(slack_routes.build_slack_callback_router())
app.include_router(build_slack_manager_onboarding_router())
app.include_router(build_debug_projections_router(), prefix="/debug", tags=["debug"])
app.include_router(build_debug_canonical_router(), prefix="/debug", tags=["debug"])
app.include_router(me.router)
app.include_router(onboarding.build_onboarding_router())
