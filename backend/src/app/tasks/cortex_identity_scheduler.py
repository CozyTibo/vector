from __future__ import annotations

import logging

from app.celery_app import celery_app
from vector.domains.cortex.identity.scheduler import iter_tenants_with_actor_entities
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_LOGGER = logging.getLogger(__name__)

_TASK_TICK = "vector.cortex.identity.scheduler_tick"


@celery_app.task(name=_TASK_TICK, queue="vector")
def tick_cortex_identity_scheduler() -> dict[str, object]:
    settings = get_settings()
    if not settings.cortex_identity_scheduler_enabled:
        return {"status": "disabled", "enqueued": 0}

    from app.tasks.cortex_identity_sync import run_cortex_identity_pass_task

    enqueued = 0
    tenant_ids: list[str] = []
    with session_scope() as session:
        for tid in iter_tenants_with_actor_entities(session):
            tenant_ids.append(str(tid))
    for tid in tenant_ids:
        run_cortex_identity_pass_task.delay(tid, source_trigger="scheduled")
        enqueued += 1
    _LOGGER.info("identity scheduler tick enqueued %s passes", enqueued)
    return {"status": "ok", "enqueued": enqueued, "tenant_count": len(tenant_ids)}

