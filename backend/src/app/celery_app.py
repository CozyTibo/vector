"""Celery application (broker/backend). Used by `app.worker` and task modules."""

from __future__ import annotations

import importlib
import os
from datetime import timedelta

from celery import Celery
from celery.signals import worker_process_init

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
    # Loader imports these on worker startup (in addition to `imports` below).
    include=[
        "app.tasks.email",
        "app.tasks.onboarding_activation_task",
        "app.tasks.cortex_ingestion_sync",
        "app.tasks.cortex_ingestion_scheduler",
        "app.tasks.cortex_ingestion_verify",
        "app.tasks.cortex_canon_sync",
        "app.tasks.cortex_canon_scheduler",
        "app.tasks.cortex_identity_sync",
        "app.tasks.cortex_identity_scheduler",
    ],
)
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.task_default_queue = "vector"
celery_app.conf.task_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_serializer = "json"
# Ensure task modules load on every worker process (avoids "unregistered task" if imports differ).
celery_app.conf.imports = (
    "app.tasks.email",
    "app.tasks.onboarding_activation_task",
    "app.tasks.cortex_ingestion_sync",
    "app.tasks.cortex_ingestion_scheduler",
    "app.tasks.cortex_ingestion_verify",
    "app.tasks.cortex_canon_sync",
    "app.tasks.cortex_canon_scheduler",
    "app.tasks.cortex_identity_sync",
    "app.tasks.cortex_identity_scheduler",
)

# Phase 01 Step 2–3: live lane vs replay lane (orchestration-model.md, replay-strategy.md).
celery_app.conf.task_routes = {
    "vector.cortex.ingestion.run_sync": {"queue": "cortex_live"},
    "vector.cortex.ingestion.run_sync_replay": {"queue": "cortex_replay"},
    "vector.cortex.canon.run_pass": {"queue": "cortex_canon"},
    "vector.cortex.identity.run_pass": {"queue": "cortex_identity"},
}

# Ingestion-only Beat: no other periodic tasks belong in this schedule.
_tick_seconds = int(os.environ.get("CORTEX_INGESTION_SCHEDULER_INTERVAL_SECONDS", "120"))
_tick_seconds = max(60, _tick_seconds)

_canon_tick_seconds = int(os.environ.get("CORTEX_CANON_SCHEDULER_INTERVAL_SECONDS", "300"))
_canon_tick_seconds = max(60, _canon_tick_seconds)
_identity_tick_seconds = int(os.environ.get("CORTEX_IDENTITY_SCHEDULER_INTERVAL_SECONDS", "300"))
_identity_tick_seconds = max(60, _identity_tick_seconds)

celery_app.conf.beat_schedule = {
    "cortex-ingestion-beat-tick": {
        "task": "vector.cortex.ingestion.scheduler_tick",
        "schedule": timedelta(seconds=_tick_seconds),
        "options": {"queue": "vector"},
    },
    "cortex-canon-beat-tick": {
        "task": "vector.cortex.canon.scheduler_tick",
        "schedule": timedelta(seconds=_canon_tick_seconds),
        "options": {"queue": "vector"},
    },
    "cortex-identity-beat-tick": {
        "task": "vector.cortex.identity.scheduler_tick",
        "schedule": timedelta(seconds=_identity_tick_seconds),
        "options": {"queue": "vector"},
    },
}


def _register_tasks() -> None:
    """Import task modules so they bind to ``celery_app``."""
    importlib.import_module("app.tasks.email")
    importlib.import_module("app.tasks.onboarding_activation_task")
    importlib.import_module("app.tasks.cortex_ingestion_sync")
    importlib.import_module("app.tasks.cortex_ingestion_scheduler")
    importlib.import_module("app.tasks.cortex_ingestion_verify")
    importlib.import_module("app.tasks.cortex_canon_sync")
    importlib.import_module("app.tasks.cortex_canon_scheduler")
    importlib.import_module("app.tasks.cortex_identity_sync")
    importlib.import_module("app.tasks.cortex_identity_scheduler")


_register_tasks()


@worker_process_init.connect
def _import_task_modules_after_fork(**_kwargs: object) -> None:
    """Prefork children must bind task modules to the app (avoids unregistered-task KeyError)."""
    importlib.import_module("app.tasks.email")
    importlib.import_module("app.tasks.onboarding_activation_task")
    importlib.import_module("app.tasks.cortex_ingestion_sync")
    importlib.import_module("app.tasks.cortex_ingestion_scheduler")
    importlib.import_module("app.tasks.cortex_ingestion_verify")
    importlib.import_module("app.tasks.cortex_canon_sync")
    importlib.import_module("app.tasks.cortex_canon_scheduler")
    importlib.import_module("app.tasks.cortex_identity_sync")
    importlib.import_module("app.tasks.cortex_identity_scheduler")
