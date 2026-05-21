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
        "app.tasks.cortex_canonical_materialize_backlog",
        "app.tasks.cortex_full_pipeline_rerun",
        "app.tasks.cortex_org_link_jobs",
        "app.tasks.cortex_post_ingestion_substrate_refresh",
        "app.tasks.cortex_substrate_pipeline",
        "app.tasks.cortex_tcre_reconstruction_jobs",
        "app.tasks.cortex_synthesis_jobs",
        "app.tasks.cortex_convergence",
        "app.tasks.cortex_execution",
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
    "app.tasks.cortex_canonical_materialize_backlog",
    "app.tasks.cortex_full_pipeline_rerun",
    "app.tasks.cortex_org_link_jobs",
    "app.tasks.cortex_post_ingestion_substrate_refresh",
    "app.tasks.cortex_tcre_reconstruction_jobs",
    "app.tasks.cortex_synthesis_jobs",
    "app.tasks.cortex_convergence",
    "app.tasks.cortex_execution",
)

# Phase 01 Step 2–3: live lane vs replay lane (orchestration-model.md, replay-strategy.md).
celery_app.conf.task_routes = {
    "vector.cortex.ingestion.run_sync": {"queue": "cortex_live"},
    "vector.cortex.ingestion.run_sync_replay": {"queue": "cortex_replay"},
}

_tick_seconds = int(os.environ.get("CORTEX_INGESTION_SCHEDULER_INTERVAL_SECONDS", "1800"))
_tick_seconds = max(60, _tick_seconds)
_convergence_sweep_seconds = int(os.environ.get("CORTEX_CONVERGENCE_SWEEPER_INTERVAL_SECONDS", "120"))
_convergence_sweep_seconds = max(30, _convergence_sweep_seconds)

# M3: substrate progression is convergence lease + sweeper only (no legacy watchdog/progression beat).
celery_app.conf.beat_schedule = {
    "cortex-ingestion-scheduler-tick": {
        "task": "vector.cortex.ingestion.scheduler_tick",
        "schedule": timedelta(seconds=_tick_seconds),
    },
    "cortex-convergence-sweep": {
        "task": "vector.cortex.convergence.sweep",
        "schedule": timedelta(seconds=_convergence_sweep_seconds),
    },
}


def _register_tasks() -> None:
    """Import task modules so they bind to ``celery_app``."""
    importlib.import_module("app.tasks.email")
    importlib.import_module("app.tasks.onboarding_activation_task")
    importlib.import_module("app.tasks.cortex_ingestion_sync")
    importlib.import_module("app.tasks.cortex_ingestion_scheduler")
    importlib.import_module("app.tasks.cortex_ingestion_verify")
    importlib.import_module("app.tasks.cortex_canonical_materialize_backlog")
    importlib.import_module("app.tasks.cortex_full_pipeline_rerun")
    importlib.import_module("app.tasks.cortex_org_link_jobs")
    importlib.import_module("app.tasks.cortex_post_ingestion_substrate_refresh")
    importlib.import_module("app.tasks.cortex_tcre_reconstruction_jobs")
    importlib.import_module("app.tasks.cortex_substrate_pipeline")
    importlib.import_module("app.tasks.cortex_substrate_continuity_watchdog")
    importlib.import_module("app.tasks.cortex_graph_density_promotion")
    importlib.import_module("app.tasks.cortex_orphan_continuity_stitch")
    importlib.import_module("app.tasks.cortex_substrate_traversal_scheduling")
    importlib.import_module("app.tasks.cortex_substrate_traversal_retry")
    importlib.import_module("app.tasks.cortex_substrate_stalled_traversal_recovery")
    importlib.import_module("app.tasks.cortex_substrate_tcre_saturation_scheduling")
    importlib.import_module("app.tasks.cortex_substrate_synthesis_activation_scheduling")
    importlib.import_module("app.tasks.cortex_substrate_operational_progression")
    importlib.import_module("app.tasks.cortex_synthesis_jobs")
    importlib.import_module("app.tasks.cortex_convergence")
    importlib.import_module("app.tasks.cortex_execution")
    importlib.import_module("app.tasks.cortex_execution")


_register_tasks()


@worker_process_init.connect
def _import_task_modules_after_fork(**_kwargs: object) -> None:
    """Prefork children must bind task modules to the app (avoids unregistered-task KeyError)."""
    importlib.import_module("app.tasks.email")
    importlib.import_module("app.tasks.onboarding_activation_task")
    importlib.import_module("app.tasks.cortex_ingestion_sync")
    importlib.import_module("app.tasks.cortex_ingestion_scheduler")
    importlib.import_module("app.tasks.cortex_ingestion_verify")
    importlib.import_module("app.tasks.cortex_canonical_materialize_backlog")
    importlib.import_module("app.tasks.cortex_full_pipeline_rerun")
    importlib.import_module("app.tasks.cortex_org_link_jobs")
    importlib.import_module("app.tasks.cortex_post_ingestion_substrate_refresh")
    importlib.import_module("app.tasks.cortex_tcre_reconstruction_jobs")
    importlib.import_module("app.tasks.cortex_substrate_pipeline")
    importlib.import_module("app.tasks.cortex_substrate_continuity_watchdog")
    importlib.import_module("app.tasks.cortex_graph_density_promotion")
    importlib.import_module("app.tasks.cortex_orphan_continuity_stitch")
    importlib.import_module("app.tasks.cortex_substrate_traversal_scheduling")
    importlib.import_module("app.tasks.cortex_substrate_traversal_retry")
    importlib.import_module("app.tasks.cortex_substrate_stalled_traversal_recovery")
    importlib.import_module("app.tasks.cortex_substrate_tcre_saturation_scheduling")
    importlib.import_module("app.tasks.cortex_substrate_synthesis_activation_scheduling")
    importlib.import_module("app.tasks.cortex_substrate_operational_progression")
    importlib.import_module("app.tasks.cortex_synthesis_jobs")
    importlib.import_module("app.tasks.cortex_convergence")
    importlib.import_module("app.tasks.cortex_execution")
