"""Health endpoint (ALB/ECS, probes) — includes DB connectivity, always HTTP 200."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from sqlalchemy import text

from vector.infrastructure.db.session import get_engine

logger = logging.getLogger("app")

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    db_ok = False
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("health: database connection OK")
        db_ok = True
    except Exception as e:
        logger.error("health: database FAILED: %s", e)
    return {
        "status": "ok",
        "database": "ok" if db_ok else "failed",
    }
