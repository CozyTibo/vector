"""Async graph connected-component snapshot writer/reader (R4)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.graph_orphan_continuity import (
    list_graph_connected_components_v1,
)
from vector.infrastructure.db.models.cortex_admin_graph_component_snapshot import (
    CortexAdminGraphComponentSnapshot,
)

_LOGGER = logging.getLogger("app")

GraphComponentJobStatus = Literal["idle", "pending", "running", "complete", "failed"]


def read_admin_graph_component_snapshot_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    row = session.get(CortexAdminGraphComponentSnapshot, tenant_id)
    if row is None:
        return {
            "available": False,
            "captured_at_utc": None,
            "component_count": None,
            "component_sizes_top_20": [],
            "largest_component_size": None,
            "job_status": "idle",
            "error_detail": None,
        }
    sizes = [int(x) for x in (row.component_sizes_top_20 or []) if isinstance(x, int)]
    return {
        "available": row.job_status == "complete" and row.captured_at_utc is not None,
        "captured_at_utc": row.captured_at_utc,
        "component_count": row.component_count,
        "component_sizes_top_20": sizes,
        "largest_component_size": sizes[0] if sizes else None,
        "job_status": row.job_status,
        "error_detail": row.error_detail,
    }


def enqueue_graph_component_snapshot_refresh_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Mark pending and enqueue async component scan."""
    row = session.get(CortexAdminGraphComponentSnapshot, tenant_id)
    if row is not None and row.job_status in ("pending", "running"):
        return {
            "surface_kind": "operator_graph_component_refresh_v1",
            "tenant_id": str(tenant_id),
            "enqueued": False,
            "job_status": row.job_status,
            "hint": "refresh_already_in_progress",
        }

    now = datetime.now(UTC)
    if row is None:
        row = CortexAdminGraphComponentSnapshot(
            tenant_id=tenant_id,
            job_status="pending",
            component_sizes_top_20=[],
            updated_at=now,
        )
        session.add(row)
    else:
        row.job_status = "pending"
        row.error_detail = None
        row.updated_at = now
    session.flush()

    try:
        from app.tasks.cortex_admin_snapshot import refresh_graph_component_snapshot_task

        refresh_graph_component_snapshot_task.delay(str(tenant_id))
    except Exception:
        _LOGGER.debug(
            "graph component snapshot enqueue skipped tenant_id=%s",
            tenant_id,
            exc_info=True,
        )
        row.job_status = "failed"
        row.error_detail = "enqueue_failed"
        session.flush()
        return {
            "surface_kind": "operator_graph_component_refresh_v1",
            "tenant_id": str(tenant_id),
            "enqueued": False,
            "job_status": "failed",
        }

    return {
        "surface_kind": "operator_graph_component_refresh_v1",
        "tenant_id": str(tenant_id),
        "enqueued": True,
        "job_status": "pending",
    }


def refresh_admin_graph_component_snapshot_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Run connected-component scan and persist snapshot (Celery worker only)."""
    row = session.get(CortexAdminGraphComponentSnapshot, tenant_id)
    now = datetime.now(UTC)
    if row is None:
        row = CortexAdminGraphComponentSnapshot(
            tenant_id=tenant_id,
            job_status="running",
            component_sizes_top_20=[],
            updated_at=now,
        )
        session.add(row)
    else:
        row.job_status = "running"
        row.error_detail = None
        row.updated_at = now
    session.flush()

    try:
        components = list_graph_connected_components_v1(session, tenant_id=tenant_id)
        sizes = sorted((len(c) for c in components), reverse=True)
        row.captured_at_utc = now
        row.component_count = len(sizes)
        row.component_sizes_top_20 = sizes[:20]
        row.job_status = "complete"
        row.error_detail = None
        row.updated_at = now
        session.flush()
        from vector.domains.cortex.pipeline.operator_admin_inspect import (
            invalidate_operator_graph_snapshot_cache_v1,
        )

        invalidate_operator_graph_snapshot_cache_v1(tenant_id)
        return {
            "surface_kind": "admin_graph_component_snapshot_refresh",
            "tenant_id": str(tenant_id),
            "component_count": len(sizes),
            "largest_component_size": sizes[0] if sizes else 0,
            "job_status": "complete",
        }
    except Exception as exc:
        row.job_status = "failed"
        row.error_detail = str(exc)[:500]
        row.updated_at = now
        session.flush()
        _LOGGER.warning(
            "graph component snapshot failed tenant_id=%s",
            tenant_id,
            exc_info=True,
        )
        raise
