from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from sqlalchemy import select

from app.celery_app import celery_app
from vector.domains.cortex.identity.scheduler import iter_tenants_with_actor_entities
from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.infrastructure.db.models.identity_pass_run import IdentityPassRun
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_LOGGER = logging.getLogger(__name__)

_TASK_TICK = "vector.cortex.identity.scheduler_tick"
_RUN_RUNNING = "RUNNING"
_RUN_FAILED = "FAILED"
_STUCK_RUNNING_MIN_SECONDS = 600


def _fail_stuck_running_identity_passes(
    session,
    *,
    tenant_id: uuid.UUID,
    interval_seconds: int,
) -> int:
    """Worker crash mid-pass leaves RUNNING forever and blocks the scheduler."""
    grace_seconds = max(_STUCK_RUNNING_MIN_SECONDS, int(interval_seconds) * 2)
    cutoff = utc_now() - timedelta(seconds=grace_seconds)
    stuck = list(
        session.scalars(
            select(IdentityPassRun).where(
                IdentityPassRun.tenant_id == tenant_id,
                IdentityPassRun.status == _RUN_RUNNING,
                IdentityPassRun.started_at < cutoff,
            ),
        ).all(),
    )
    if not stuck:
        return 0
    now = utc_now()
    for row in stuck:
        row.status = _RUN_FAILED
        row.finished_at = now
        row.error_summary = "stale_running_pass_abandoned"
    session.flush()
    _LOGGER.warning(
        "identity scheduler abandoned %s stale RUNNING pass(es) for tenant %s",
        len(stuck),
        tenant_id,
    )
    return len(stuck)


def _should_skip_scheduled_identity_pass(
    session,
    *,
    tenant_id: uuid.UUID,
    interval_seconds: int,
) -> bool:
    """Avoid duplicate scheduled passes (multiple Beat containers or slow workers)."""
    _fail_stuck_running_identity_passes(
        session,
        tenant_id=tenant_id,
        interval_seconds=interval_seconds,
    )
    in_flight_window = max(120, int(interval_seconds) * 2)
    running = session.scalar(
        select(IdentityPassRun.id)
        .where(
            IdentityPassRun.tenant_id == tenant_id,
            IdentityPassRun.status == _RUN_RUNNING,
            IdentityPassRun.started_at >= utc_now() - timedelta(seconds=in_flight_window),
        )
        .limit(1),
    )
    if running is not None:
        return True
    min_gap = max(60, int(interval_seconds * 0.85))
    recent = session.scalar(
        select(IdentityPassRun.id)
        .where(
            IdentityPassRun.tenant_id == tenant_id,
            IdentityPassRun.source_trigger == "scheduled",
            IdentityPassRun.started_at >= utc_now() - timedelta(seconds=min_gap),
        )
        .limit(1),
    )
    return recent is not None


@celery_app.task(name=_TASK_TICK, queue="vector")
def tick_cortex_identity_scheduler() -> dict[str, object]:
    settings = get_settings()
    if not settings.cortex_identity_scheduler_enabled:
        return {"status": "disabled", "enqueued": 0}

    from app.tasks.cortex_identity_sync import run_cortex_identity_pass_task

    interval = max(60, int(settings.cortex_identity_scheduler_interval_seconds))
    enqueued = 0
    skipped = 0
    tenant_ids: list[str] = []
    with session_scope() as session:
        for tid in iter_tenants_with_actor_entities(session):
            tenant_ids.append(str(tid))
    for tid in tenant_ids:
        tid_uuid = uuid.UUID(tid)
        with session_scope() as session:
            if _should_skip_scheduled_identity_pass(
                session,
                tenant_id=tid_uuid,
                interval_seconds=interval,
            ):
                skipped += 1
                continue
        run_cortex_identity_pass_task.delay(tid, source_trigger="scheduled")
        enqueued += 1
    _LOGGER.info(
        "identity scheduler tick enqueued %s passes (%s skipped, %s tenants)",
        enqueued,
        skipped,
        len(tenant_ids),
    )
    return {
        "status": "ok",
        "enqueued": enqueued,
        "skipped": skipped,
        "tenant_count": len(tenant_ids),
        "interval_seconds": interval,
    }

