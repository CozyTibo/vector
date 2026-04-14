"""Health endpoint (ALB/ECS, probes) — includes DB connectivity."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from vector.infrastructure.db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=None)
def health_check() -> dict[str, str] | JSONResponse:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("health: database connection OK")
    except Exception as exc:
        logger.warning(
            "health: database connection FAILED — %s: %s",
            type(exc).__name__,
            exc,
        )
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
    return {"status": "ok"}
