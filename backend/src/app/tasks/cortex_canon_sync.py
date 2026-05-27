"""Celery tasks — Cortex canon v1 materialization."""

from __future__ import annotations

import logging
import uuid

from app.celery_app import celery_app
from vector.domains.cortex.canon.materialize import execute_canon_pass_for_tenant, process_dirty_queue_batch
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_LOGGER = logging.getLogger(__name__)

_TASK_CANON_PASS = "vector.cortex.canon.run_pass"


@celery_app.task(name=_TASK_CANON_PASS, queue="cortex_canon")
def run_cortex_canon_pass_task(
    tenant_id: str,
    source_trigger: str = "scheduled",
) -> dict[str, object]:
    """Materialize a batch of raw rows for one tenant."""
    tid = uuid.UUID(tenant_id)
    settings = get_settings()
    batch = settings.cortex_canon_batch_raw_limit
    with session_scope() as session:
        out = execute_canon_pass_for_tenant(
            session,
            tenant_id=tid,
            source_trigger=source_trigger,
            batch_limit=batch,
        )
        dirty_stats = process_dirty_queue_batch(session, tenant_id=tid, batch_limit=batch)
        session.commit()
    out["dirty_queue"] = dirty_stats
    return out
