from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.celery_app import celery_app
from vector.domains.cortex.identity.pass_run_ops import RUN_RUNNING, abandon_stuck_running_identity_passes
from vector.domains.cortex.identity.scheduler import iter_tenants_with_actor_entities
from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.domains.cortex.runtime.lane_scheduler_tick import complete_lane_scheduler_tick_v1
from vector.infrastructure.db.models.identity_pass_run import IdentityPassRun
from vector.infrastructure.db.models.identity_scheduler_tick import IdentitySchedulerTick
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_LOGGER = logging.getLogger(__name__)

_TASK_TICK = "vector.cortex.identity.scheduler_tick"


def _should_skip_scheduled_identity_pass(
    session,
    *,
    tenant_id: uuid.UUID,
    interval_seconds: int,
) -> bool:
    """Avoid duplicate scheduled passes (multiple Beat containers or slow workers)."""
    abandon_stuck_running_identity_passes(
        session,
        tenant_id=tenant_id,
        interval_seconds=interval_seconds,
    )
    in_flight_window = max(120, int(interval_seconds) * 2)
    running = session.scalar(
        select(IdentityPassRun.id)
        .where(
            IdentityPassRun.tenant_id == tenant_id,
            IdentityPassRun.status == RUN_RUNNING,
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
    beat_interval = max(60, int(settings.cortex_identity_scheduler_interval_seconds))

    with session_scope() as session:
        tick = IdentitySchedulerTick(
            started_at=datetime.now(tz=UTC),
            outcome="running",
            beat_interval_seconds=beat_interval,
        )
        session.add(tick)
        session.flush()
        tick_id = tick.id

    if not settings.cortex_identity_scheduler_enabled:
        with session_scope() as session:
            tick = session.get(IdentitySchedulerTick, tick_id)
            if tick is not None:
                complete_lane_scheduler_tick_v1(
                    session,
                    tick,
                    outcome="skipped_disabled",
                    enqueued_count=0,
                    candidate_count=0,
                    skip_reason="scheduler_disabled",
                )
        return {"status": "disabled", "enqueued": 0, "tick_id": str(tick_id)}

    from app.tasks.cortex_identity_sync import run_cortex_identity_pass_task

    enqueued = 0
    skipped = 0
    tenant_ids: list[str] = []
    enqueued_ids: list[str] = []
    with session_scope() as session:
        for tid in iter_tenants_with_actor_entities(session):
            tenant_ids.append(str(tid))
    for tid in tenant_ids:
        tid_uuid = uuid.UUID(tid)
        with session_scope() as session:
            if _should_skip_scheduled_identity_pass(
                session,
                tenant_id=tid_uuid,
                interval_seconds=beat_interval,
            ):
                skipped += 1
                continue
        run_cortex_identity_pass_task.delay(tid, source_trigger="scheduled")
        enqueued += 1
        enqueued_ids.append(tid)
    outcome = "enqueued" if enqueued else "noop"
    with session_scope() as session:
        tick = session.get(IdentitySchedulerTick, tick_id)
        if tick is not None:
            complete_lane_scheduler_tick_v1(
                session,
                tick,
                outcome=outcome,
                enqueued_count=enqueued,
                candidate_count=len(tenant_ids),
                skipped_count=skipped,
                enqueued_tenant_ids=enqueued_ids,
            )
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
        "interval_seconds": beat_interval,
        "tick_id": str(tick_id),
    }
