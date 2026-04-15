"""Liveness (`/health`), readiness (`/ready`), and deep readiness (`/ready/e2e`)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import redis
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Response
from sqlalchemy import text

from vector.infrastructure.db.session import get_engine

logger = logging.getLogger("app")

router = APIRouter(tags=["health"])

_E2E_CELERY_INSPECT_TIMEOUT_S = float(os.environ.get("READY_E2E_CELERY_TIMEOUT_S", "2.5"))


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


def _find_alembic_ini() -> Path | None:
    """Resolve ``alembic.ini`` (Docker ``WORKDIR`` is ``/app``; tests may run from ``backend/``)."""
    cwd_ini = Path.cwd() / "alembic.ini"
    if cwd_ini.is_file():
        return cwd_ini
    # ``health.py`` → ``backend/src/vector/api/http/routes`` → six parents up to ``backend/``
    candidate = Path(__file__).resolve().parents[5] / "alembic.ini"
    if candidate.is_file():
        return candidate
    return None


def _migrations_state(engine: Any) -> tuple[str, str | None]:
    """
    Compare Alembic revision in the DB to the script head.

    Returns ``(status, detail)`` where status is ``ok``, ``behind``, ``failed``, or ``skipped``.
    """
    ini = _find_alembic_ini()
    if ini is None:
        logger.error("ready e2e: alembic.ini not found (cwd=%s)", Path.cwd())
        return ("failed", "alembic.ini not found")

    try:
        cfg = Config(str(ini))
        script = ScriptDirectory.from_config(cfg)
        heads = script.get_heads()
        if len(heads) != 1:
            return ("failed", f"expected a single migration head, got {sorted(heads)!r}")
        head = heads[0]
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current = context.get_current_revision()
        if current is None:
            return ("behind", "database has no alembic revision (migrations not applied)")
        if current != head:
            return ("behind", f"database at {current!r}, head is {head!r}")
        logger.info("ready e2e: migrations at head %s", head)
        return ("ok", None)
    except Exception as e:
        logger.exception("ready e2e: migration check FAILED: %s", e)
        return ("failed", str(e))


def _worker_state() -> str:
    """Celery worker reachability: ``ok`` / ``no_workers`` / ``failed`` / ``skipped``."""
    if not os.environ.get("REDIS_URL", "").strip():
        return "skipped"
    try:
        from app.celery_app import celery_app

        inspect = celery_app.control.inspect(timeout=_E2E_CELERY_INSPECT_TIMEOUT_S)
        if inspect is None:
            logger.error("ready e2e: celery inspect handle is None (broker unreachable?)")
            return "failed"
        pong = inspect.ping()
        if not pong:
            logger.warning("ready e2e: no Celery workers replied to ping")
            return "no_workers"
        for worker, reply in pong.items():
            if not isinstance(reply, dict) or reply.get("ok") != "pong":
                logger.error("ready e2e: unexpected ping reply from %s: %r", worker, reply)
                return "failed"
        logger.info("ready e2e: Celery ping OK (%d worker(s))", len(pong))
        return "ok"
    except Exception as e:
        logger.exception("ready e2e: Celery inspect FAILED: %s", e)
        return "failed"


@router.get("/ready/e2e")
def ready_e2e(response: Response) -> dict[str, Any]:
    """
    Deep readiness: DB, Alembic head, Redis, Celery workers.

    Unlike ``/ready``, returns ``503`` if any non-skipped check is unhealthy.
    """
    db_state = "failed"
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_state = "ok"
        logger.info("ready e2e: database connection OK")
    except Exception as e:
        logger.error("ready e2e: database FAILED: %s", e)

    migrations_state = "skipped"
    migrations_detail: str | None = None
    if db_state == "ok":
        engine = get_engine()
        migrations_state, migrations_detail = _migrations_state(engine)

    redis_state = _redis_status()
    worker_state = "skipped" if redis_state != "ok" else _worker_state()

    ok_values = frozenset({"ok", "skipped"})
    overall_ok = all(
        s in ok_values
        for s in (db_state, migrations_state, redis_state, worker_state)
    )

    body: dict[str, Any] = {
        "status": "ok" if overall_ok else "degraded",
        "database": db_state,
        "migrations": migrations_state,
        "redis": redis_state,
        "worker": worker_state,
    }
    if migrations_detail and migrations_state != "ok":
        body["migrations_detail"] = migrations_detail

    response.status_code = 200 if overall_ok else 503
    return body
