"""Liveness (`/health`) and readiness (`/ready`) endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from sqlalchemy import text

from vector.infrastructure.db.session import get_engine

logger = logging.getLogger("app")

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
def ready_check() -> dict[str, str]:
    db_ok = False
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
        logger.info("ready: database connection OK")
    except Exception as e:
        logger.error("ready: database FAILED: %s", e)
    return {
        "status": "ok",
        "database": "ok" if db_ok else "failed",
    }
