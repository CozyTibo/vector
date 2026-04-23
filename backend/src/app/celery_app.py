"""Celery application (broker/backend). Used by `app.worker` and task modules."""

from __future__ import annotations

import importlib
import os

from celery import Celery

from vector.infrastructure.redis_url import normalize_rediss_url


def _redis_url_for_celery(url: str) -> str:
    """Normalize Redis URL for Celery.

    Celery's Redis SSL backend requires ``ssl_cert_reqs`` on ``rediss://`` URLs
    (see ``celery/backends/redis.py``).
    """
    stripped = normalize_rediss_url(url)
    # ElastiCache / many managed TLS Redis: skip CA verification unless you pin a CA.
    # Override by adding ``ssl_cert_reqs=CERT_REQUIRED`` (or ``required``) to ``REDIS_URL``.
    return stripped


def _patch_rediss_urls_in_environ() -> None:
    """Celery reads ``CELERY_*`` URLs from ``os.environ`` first (see ``celery.app.utils.Settings``).

    A normalized ``backend=`` / ``broker=`` passed to ``Celery()`` is ignored for
    ``result_backend`` / ``broker_url`` when the matching env var is set, so we
    rewrite those env values when they use ``rediss://`` without ``ssl_cert_reqs``.
    """
    for key in (
        "CELERY_RESULT_BACKEND",
        "CELERY_BROKER_URL",
        "CELERY_BROKER_READ_URL",
        "CELERY_BROKER_WRITE_URL",
        "REDIS_URL",
    ):
        raw = os.environ.get(key, "").strip()
        if not raw:
            continue
        normalized = _redis_url_for_celery(raw)
        if normalized != raw:
            os.environ[key] = normalized


_patch_rediss_urls_in_environ()

# Default for local dev when REDIS_URL is unset (Docker Compose sets it explicitly).
_broker = _redis_url_for_celery(os.environ.get("REDIS_URL", "").strip() or "redis://127.0.0.1:6379/0")
_backend_raw = os.environ.get("CELERY_RESULT_BACKEND", "").strip()
_backend = _redis_url_for_celery(_backend_raw) if _backend_raw else _broker

# Name is `celery_app`, not `app`, so a future `import app.tasks…` at module level cannot
# shadow the Celery instance (that would drop all @app.task registrations).
celery_app = Celery(
    "vector",
    broker=_broker,
    backend=_backend,
)
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.task_default_queue = "vector"
celery_app.conf.task_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_serializer = "json"
# Ensure task modules load on every worker process (avoids "unregistered task" if imports differ).
celery_app.conf.imports = ("app.tasks.ingestion", "app.tasks.email")


def _register_tasks() -> None:
    """Import task modules so they bind to ``celery_app``."""
    importlib.import_module("app.tasks.ingestion")
    importlib.import_module("app.tasks.email")


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
