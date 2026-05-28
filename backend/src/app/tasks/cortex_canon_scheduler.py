"""Celery Beat — enqueue canon materialization passes per tenant."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.celery_app import celery_app
from vector.domains.cortex.canon.scheduler import iter_tenants_with_live_raw
from vector.domains.cortex.canon.scheduler_dedup import should_skip_scheduled_canon_pass
from vector.domains.cortex.runtime.lane_scheduler_tick import complete_lane_scheduler_tick_v1
from vector.infrastructure.db.models.canon_scheduler_tick import CanonSchedulerTick
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_LOGGER = logging.getLogger(__name__)

_TASK_TICK = "vector.cortex.canon.scheduler_tick"


@celery_app.task(name=_TASK_TICK, queue="vector")
def tick_cortex_canon_scheduler() -> dict[str, object]:
    settings = get_settings()
    beat_interval = max(60, int(settings.cortex_canon_scheduler_interval_seconds))

    with session_scope() as session:
        tick = CanonSchedulerTick(
            started_at=datetime.now(tz=UTC),
            outcome="running",
            beat_interval_seconds=beat_interval,
        )
        session.add(tick)
        session.flush()
        tick_id = tick.id

    if not settings.cortex_canon_scheduler_enabled:
        with session_scope() as session:
            tick = session.get(CanonSchedulerTick, tick_id)
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

    from app.tasks.cortex_canon_sync import run_cortex_canon_pass_task

    enqueued = 0
    skipped = 0
    tenant_ids: list[str] = []
    enqueued_ids: list[str] = []
    with session_scope() as session:
        for tid in iter_tenants_with_live_raw(session, settings):
            tenant_ids.append(str(tid))
    for tid in tenant_ids:
        tid_uuid = uuid.UUID(tid)
        with session_scope() as session:
            if should_skip_scheduled_canon_pass(
                session,
                tenant_id=tid_uuid,
                interval_seconds=beat_interval,
            ):
                skipped += 1
                continue
        run_cortex_canon_pass_task.delay(tid, source_trigger="scheduled")
        enqueued += 1
        enqueued_ids.append(tid)

    outcome = "enqueued" if enqueued else "noop"
    with session_scope() as session:
        tick = session.get(CanonSchedulerTick, tick_id)
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
        "canon scheduler tick enqueued %s passes (%s skipped, %s tenants)",
        enqueued,
        skipped,
        len(tenant_ids),
    )
    return {
        "status": "ok",
        "enqueued": enqueued,
        "skipped": skipped,
        "tenant_count": len(tenant_ids),
        "tick_id": str(tick_id),
    }
