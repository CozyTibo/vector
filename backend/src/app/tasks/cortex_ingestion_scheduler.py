"""Celery Beat — Cortex ingestion-only scheduler (live sync lane)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.ingestion.scheduler import iter_routed_live_sync_jobs
from vector.domains.cortex.ingestion.scheduler_tick_history import complete_scheduler_tick_v1
from vector.infrastructure.cortex_scheduler_pause import read_scheduler_paused_flag
from vector.infrastructure.db.models.ingestion_scheduler_tick import IngestionSchedulerTick
from vector.infrastructure.db.session import session_scope
from vector.infrastructure.observability.ingestion_tasks import PHASE_STEP1, log_ingestion_event
from vector.settings import get_settings

_LOGGER = logging.getLogger("app")

# Ingestion-only Beat entry (see celery_app.conf.beat_schedule).
_TASK_SCHEDULER_TICK = "vector.cortex.ingestion.scheduler_tick"


@celery_app.task(name=_TASK_SCHEDULER_TICK)
def tick_cortex_ingestion_scheduler() -> dict[str, object]:
    """Ingestion Beat tick: enqueue ``run_sync`` on ``cortex_live`` for routed tenant connections."""
    settings = get_settings()
    beat_interval = max(60, int(settings.cortex_ingestion_scheduler_interval_seconds))

    with session_scope() as session:
        tick = IngestionSchedulerTick(
            started_at=datetime.now(tz=UTC),
            outcome="running",
            beat_interval_seconds=beat_interval,
        )
        session.add(tick)
        session.flush()
        tick_id = tick.id

    if not settings.cortex_ingestion_scheduler_enabled:
        with session_scope() as session:
            complete_scheduler_tick_v1(
                session,
                tick_id,
                outcome="skipped_disabled",
                enqueued_count=0,
                candidate_count=0,
                skip_reason="scheduler_disabled",
            )
        return {"enqueued": 0, "skipped": True, "reason": "scheduler_disabled", "tick_id": str(tick_id)}

    if read_scheduler_paused_flag(settings):
        with session_scope() as session:
            complete_scheduler_tick_v1(
                session,
                tick_id,
                outcome="skipped_paused",
                enqueued_count=0,
                candidate_count=0,
                skip_reason="scheduler_paused_operator_redis",
            )
        return {
            "enqueued": 0,
            "skipped": True,
            "reason": "scheduler_paused_operator_redis",
            "tick_id": str(tick_id),
        }

    from app.tasks.cortex_ingestion_sync import run_cortex_connector_sync_task

    with session_scope() as session:
        jobs = iter_routed_live_sync_jobs(session, settings)

    enqueued_jobs: list[dict[str, Any]] = []
    enqueued = 0
    for job in jobs:
        run_cortex_connector_sync_task.apply_async(
            args=[
                str(job.tenant_id),
                job.connector_id,
                "scheduled_lane",
                "incremental",
                str(job.connection_id),
            ],
            kwargs={"scheduler_tick_id": str(tick_id)},
            queue="cortex_live",
        )
        enqueued += 1
        enqueued_jobs.append(
            {
                "tenant_id": str(job.tenant_id),
                "connection_id": str(job.connection_id),
                "connector_id": job.connector_id,
            }
        )

    outcome = "enqueued" if enqueued else "noop"
    with session_scope() as session:
        complete_scheduler_tick_v1(
            session,
            tick_id,
            outcome=outcome,
            enqueued_count=enqueued,
            candidate_count=len(jobs),
            enqueued_jobs=enqueued_jobs,
        )

    log_ingestion_event(
        _LOGGER,
        logging.INFO,
        "cortex ingestion beat tick",
        task_name="tick_cortex_ingestion_scheduler",
        phase=PHASE_STEP1,
        outcome=outcome,
        enqueued=enqueued,
        candidates=len(jobs),
        tick_id=str(tick_id),
    )
    return {
        "tick_id": str(tick_id),
        "enqueued": enqueued,
        "candidates": len(jobs),
        "beat_interval_seconds": beat_interval,
    }
