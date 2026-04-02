"""Celery application (broker/backend). Used by `app.worker` and task modules."""

from __future__ import annotations

import os

from celery import Celery

# Default for local dev when REDIS_URL is unset (Docker Compose sets it explicitly).
_redis = os.environ.get("REDIS_URL", "").strip() or "redis://127.0.0.1:6379/0"

app = Celery(
    "vector",
    broker=_redis,
    backend=os.environ.get("CELERY_RESULT_BACKEND", _redis),
)
app.conf.broker_connection_retry_on_startup = True
app.conf.task_default_queue = "vector"
app.conf.task_serializer = "json"
app.conf.accept_content = ["json"]
app.conf.result_serializer = "json"


def _register_tasks() -> None:
    """Import task modules so they bind to ``app``."""
    import app.tasks.ingestion  # noqa: F401


_register_tasks()
