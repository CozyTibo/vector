"""Celery Beat — Phase 01 Step 2 scheduled dispatcher (live sync lane)."""

from __future__ import annotations

import logging

from app.celery_app import celery_app
from vector.domains.cortex.ingestion.scheduler import iter_routed_live_sync_jobs
from vector.infrastructure.cortex_scheduler_pause import read_scheduler_paused_flag
from vector.infrastructure.db.session import session_scope
from vector.infrastructure.observability.ingestion_tasks import PHASE_STEP1, log_ingestion_event
from vector.settings import get_settings

_LOGGER = logging.getLogger("app")

_TASK_SCHEDULER_TICK = "vector.cortex.ingestion.scheduler_tick"


@celery_app.task(name=_TASK_SCHEDULER_TICK)
def tick_cortex_ingestion_scheduler() -> dict[str, object]:
    """Periodic tick: enqueue ``run_sync`` on ``cortex_live`` for routed tenant connections."""
    settings = get_settings()
    if not settings.cortex_ingestion_scheduler_enabled:
        return {"enqueued": 0, "skipped": True, "reason": "scheduler_disabled"}

    if read_scheduler_paused_flag(settings):
        return {"enqueued": 0, "skipped": True, "reason": "scheduler_paused_operator_redis"}

    # Lazy import avoids circular init: ``cortex_ingestion_sync`` loads ``celery_app``, which
    # registers this module before ``cortex_ingestion_sync`` has finished importing.
    from app.tasks.cortex_ingestion_sync import run_cortex_connector_sync_task

    with session_scope() as session:
        jobs = iter_routed_live_sync_jobs(session, settings)

    enqueued = 0
    for job in jobs:
        run_cortex_connector_sync_task.apply_async(
            args=[str(job.tenant_id), job.connector_id, "scheduled_lane", "incremental", str(job.connection_id)],
            queue="cortex_live",
        )
        enqueued += 1

    log_ingestion_event(
        _LOGGER,
        logging.INFO,
        "cortex ingestion scheduler tick",
        task_name="tick_cortex_ingestion_scheduler",
        phase=PHASE_STEP1,
        outcome="scheduled" if enqueued else "noop",
        enqueued=enqueued,
        candidates=len(jobs),
    )
    return {"enqueued": enqueued, "candidates": len(jobs)}
