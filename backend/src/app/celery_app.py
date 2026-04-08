"""Celery application (broker/backend). Used by `app.worker` and task modules."""

from __future__ import annotations

import importlib
import os

from celery import Celery

# Default for local dev when REDIS_URL is unset (Docker Compose sets it explicitly).
_redis = os.environ.get("REDIS_URL", "").strip() or "redis://127.0.0.1:6379/0"

# Name is `celery_app`, not `app`, so a future `import app.tasks…` at module level cannot
# shadow the Celery instance (that would drop all @app.task registrations).
celery_app = Celery(
    "vector",
    broker=_redis,
    backend=os.environ.get("CELERY_RESULT_BACKEND", _redis),
)
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.task_default_queue = "vector"
celery_app.conf.task_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_serializer = "json"
# Ensure task modules load on every worker process (avoids "unregistered task" if imports differ).
celery_app.conf.imports = ("app.tasks.ingestion", "app.tasks.manager_onboarding")


def _register_tasks() -> None:
    """Import task modules so they bind to ``celery_app``."""
    importlib.import_module("app.tasks.ingestion")
    importlib.import_module("app.tasks.manager_onboarding")


def _configure_beat_schedule() -> None:
    raw = os.environ.get("VECTOR_INGESTION_SWEEP_INTERVAL_SECONDS", "900").strip()
    try:
        interval = int(raw)
    except ValueError:
        interval = 900
    if interval <= 0:
        return
    celery_app.conf.beat_schedule = {
        "sweep-canonical-lag": {
            "task": "vector.ingestion.sweep_canonical_lag",
            "schedule": float(interval),
        },
    }


_register_tasks()
_configure_beat_schedule()
