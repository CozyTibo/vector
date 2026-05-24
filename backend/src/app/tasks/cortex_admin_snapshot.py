"""Celery tasks — materialized admin continuity snapshots (R1)."""

from __future__ import annotations

import logging
import uuid

from app.celery_app import celery_app
from vector.domains.cortex.pipeline.admin_continuity_snapshot import (
    list_active_snapshot_tenant_ids_v1,
    refresh_admin_continuity_snapshot_v1,
)
from vector.domains.cortex.pipeline.admin_graph_component_snapshot import (
    refresh_admin_graph_component_snapshot_v1,
)
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger("app")

_TASK_REFRESH = "vector.cortex.admin.refresh_continuity_snapshot"
_TASK_SWEEP = "vector.cortex.admin.refresh_continuity_snapshots_sweep"
_TASK_GRAPH_COMPONENT = "vector.cortex.admin.refresh_graph_component_snapshot"


@celery_app.task(name=_TASK_REFRESH, queue="vector")
def refresh_admin_continuity_snapshot_task(tenant_id: str) -> dict:
    tid = uuid.UUID(str(tenant_id))
    with session_scope() as session:
        return refresh_admin_continuity_snapshot_v1(session, tenant_id=tid)


@celery_app.task(name=_TASK_SWEEP, queue="vector")
def refresh_admin_continuity_snapshots_sweep_task(limit: int = 200) -> dict:
    refreshed = 0
    errors = 0
    tenant_ids: list[uuid.UUID] = []
    with session_scope() as session:
        tenant_ids = list_active_snapshot_tenant_ids_v1(session, limit=limit)
        for tid in tenant_ids:
            try:
                refresh_admin_continuity_snapshot_v1(session, tenant_id=tid)
                refreshed += 1
            except Exception:
                errors += 1
                _LOGGER.warning(
                    "admin continuity snapshot sweep failed tenant_id=%s",
                    tid,
                    exc_info=True,
                )
    return {
        "surface_kind": "admin_continuity_snapshot_sweep",
        "tenants_attempted": len(tenant_ids),
        "refreshed": refreshed,
        "errors": errors,
    }


@celery_app.task(name=_TASK_GRAPH_COMPONENT, queue="vector")
def refresh_graph_component_snapshot_task(tenant_id: str) -> dict:
    tid = uuid.UUID(str(tenant_id))
    with session_scope() as session:
        return refresh_admin_graph_component_snapshot_v1(session, tenant_id=tid)
