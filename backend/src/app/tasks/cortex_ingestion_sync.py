"""Celery tasks — Cortex Phase 01 connector ingestion sync."""

from __future__ import annotations

import uuid

from app.celery_app import celery_app
from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_TASK_RUN_SYNC = "vector.cortex.ingestion.run_sync"


@celery_app.task(name=_TASK_RUN_SYNC)
def run_cortex_connector_sync_task(
    tenant_id: str,
    connector_id: str,
    source_trigger: str = "scheduled",
) -> dict[str, object]:
    """Execute one incremental sync for a tenant connection (runs + raw rows)."""
    tid = uuid.UUID(tenant_id)
    settings = get_settings()
    with session_scope() as session:
        return execute_connector_sync(
            session,
            settings,
            tenant_id=tid,
            connector_id=connector_id,
            source_trigger=source_trigger,
        )
