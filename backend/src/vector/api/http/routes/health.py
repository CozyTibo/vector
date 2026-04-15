"""Liveness (`/health`) and readiness (`/ready`) endpoints."""

from __future__ import annotations

import logging
import os

import redis
from fastapi import APIRouter
from sqlalchemy import text

from vector.infrastructure.db.session import get_engine

logger = logging.getLogger("app")

router = APIRouter(tags=["health"])


def _redis_status() -> str:
    """Return ``ok``, ``failed``, or ``skipped`` when ``REDIS_URL`` is unset."""
    url = os.environ.get("REDIS_URL", "").strip()
    if not url:
        return "skipped"
    client: redis.Redis | None = None
    try:
        client = redis.from_url(url)
        client.ping()
        logger.info("ready: redis connection OK")
        return "ok"
    except Exception as e:
        logger.error("ready: redis FAILED: %s", e)
        return "failed"
    finally:
        if client is not None:
            client.close()


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

    redis_state = _redis_status()

    return {
        "status": "ok",
        "database": "ok" if db_ok else "failed",
        "redis": redis_state,
    }
