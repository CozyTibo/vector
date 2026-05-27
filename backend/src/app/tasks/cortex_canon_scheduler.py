"""Celery Beat — enqueue canon materialization passes per tenant."""

from __future__ import annotations

import logging

from app.celery_app import celery_app
from vector.domains.cortex.canon.scheduler import iter_tenants_with_live_raw
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_LOGGER = logging.getLogger(__name__)

_TASK_TICK = "vector.cortex.canon.scheduler_tick"


@celery_app.task(name=_TASK_TICK, queue="vector")
def tick_cortex_canon_scheduler() -> dict[str, object]:
    settings = get_settings()
    if not settings.cortex_canon_scheduler_enabled:
        return {"status": "disabled", "enqueued": 0}

    from app.tasks.cortex_canon_sync import run_cortex_canon_pass_task

    enqueued = 0
    tenant_ids: list[str] = []
    with session_scope() as session:
        for tid in iter_tenants_with_live_raw(session, settings):
            tenant_ids.append(str(tid))
    for tid in tenant_ids:
        run_cortex_canon_pass_task.delay(tid, source_trigger="scheduled")
        enqueued += 1
    _LOGGER.info("canon scheduler tick enqueued %s passes", enqueued)
    return {"status": "ok", "enqueued": enqueued, "tenant_count": len(tenant_ids)}
