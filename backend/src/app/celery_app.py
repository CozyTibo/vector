"""Celery application (broker/backend). Used by `app.worker` and task modules."""

from __future__ import annotations

import importlib
import os
from datetime import timedelta

from celery import Celery
from celery.signals import worker_process_init

from vector.infrastructure.redis_url import normalize_rediss_url


def _redis_url_for_celery(url: str) -> str:
    """Normalize Redis URL for Celery."""
    return normalize_rediss_url(url)


def _patch_rediss_urls_in_environ() -> None:
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

_broker = _redis_url_for_celery(os.environ.get("REDIS_URL", "").strip() or "redis://127.0.0.1:6379/0")
_backend_raw = os.environ.get("CELERY_RESULT_BACKEND", "").strip()
_backend = _redis_url_for_celery(_backend_raw) if _backend_raw else _broker

celery_app = Celery(
    "vector",
    broker=_broker,
    backend=_backend,
    include=[
        "app.tasks.email",
        "app.tasks.onboarding_activation_task",
        "app.tasks.cortex_ingestion_sync",
        "app.tasks.cortex_ingestion_scheduler",
        "app.tasks.cortex_ingestion_verify",
        "app.tasks.cortex_runtime",
    ],
)
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.task_default_queue = "vector"
celery_app.conf.task_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_serializer = "json"
celery_app.conf.imports = (
    "app.tasks.email",
    "app.tasks.onboarding_activation_task",
    "app.tasks.cortex_ingestion_sync",
    "app.tasks.cortex_ingestion_scheduler",
    "app.tasks.cortex_ingestion_verify",
    "app.tasks.cortex_runtime",
)

celery_app.conf.task_routes = {
    "vector.cortex.ingestion.run_sync": {"queue": "cortex_live"},
    "vector.cortex.ingestion.run_sync_replay": {"queue": "cortex_replay"},
    "vector.cortex.runtime.plan_passes": {"queue": "vector"},
    "vector.cortex.runtime.poll_passes": {"queue": "vector"},
}

_tick_seconds = max(60, int(os.environ.get("CORTEX_INGESTION_SCHEDULER_INTERVAL_SECONDS", "120")))
_plan_seconds = max(
    60,
    int(os.environ.get("CORTEX_CANON_SCHEDULER_INTERVAL_SECONDS", "300")),
)
_poll_seconds = max(30, int(os.environ.get("CORTEX_RUNTIME_POLL_INTERVAL_SECONDS", "60")))

celery_app.conf.beat_schedule = {
    "cortex-ingestion-beat-tick": {
        "task": "vector.cortex.ingestion.scheduler_tick",
        "schedule": timedelta(seconds=_tick_seconds),
        "options": {"queue": "vector"},
    },
    "cortex-runtime-plan-passes": {
        "task": "vector.cortex.runtime.plan_passes",
        "schedule": timedelta(seconds=_plan_seconds),
        "options": {"queue": "vector"},
    },
    "cortex-runtime-poll-passes": {
        "task": "vector.cortex.runtime.poll_passes",
        "schedule": timedelta(seconds=_poll_seconds),
        "options": {"queue": "vector"},
    },
}


def _register_tasks() -> None:
    importlib.import_module("app.tasks.email")
    importlib.import_module("app.tasks.onboarding_activation_task")
    importlib.import_module("app.tasks.cortex_ingestion_sync")
    importlib.import_module("app.tasks.cortex_ingestion_scheduler")
    importlib.import_module("app.tasks.cortex_ingestion_verify")
    importlib.import_module("app.tasks.cortex_runtime")


_register_tasks()


@worker_process_init.connect
def _import_task_modules_after_fork(**_kwargs: object) -> None:
    importlib.import_module("app.tasks.email")
    importlib.import_module("app.tasks.onboarding_activation_task")
    importlib.import_module("app.tasks.cortex_ingestion_sync")
    importlib.import_module("app.tasks.cortex_ingestion_scheduler")
    importlib.import_module("app.tasks.cortex_ingestion_verify")
    importlib.import_module("app.tasks.cortex_runtime")
