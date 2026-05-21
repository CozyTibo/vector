"""Enqueue tenant execution slice (no revoke, no stable task id)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from vector.domains.cortex.execution.execution_path_telemetry import (
    EXECUTION_PATH_CONVERGENCE,
    emit_execution_path_telemetry_v1,
)
from vector.domains.cortex.execution.lease import mark_tenant_dirty_v1
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger(__name__)


def enqueue_tenant_convergence_v1(
    tenant_id: uuid.UUID | str,
    *,
    reason: str = "sweeper",
) -> dict[str, Any]:
    """Idempotent hint to run execution slice; durable lease is source of truth."""
    from app.tasks.cortex_execution import run_execution_slice_task

    tid = uuid.UUID(str(tenant_id))
    async_result = run_execution_slice_task.apply_async(
        kwargs={"tenant_id": str(tid), "reason": reason},
        queue="vector",
    )
    telemetry = emit_execution_path_telemetry_v1(
        tenant_id=tid,
        execution_path=EXECUTION_PATH_CONVERGENCE,
        trigger=f"execution_enqueue:{reason}",
        celery_task_id=str(async_result.id),
    )
    _LOGGER.info(
        "execution_slice_enqueued tenant_id=%s reason=%s celery_task_id=%s",
        tid,
        reason,
        async_result.id,
    )
    return {
        "enqueued": True,
        "tenant_id": str(tid),
        "reason": reason,
        "celery_task_id": str(async_result.id),
        "execution_path": EXECUTION_PATH_CONVERGENCE,
        "task_name": "vector.cortex.execution.run_slice",
        "execution_path_telemetry": telemetry,
    }


enqueue_tenant_execution_v1 = enqueue_tenant_convergence_v1


def enqueue_execution_slice_at_phase_v1(
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    phase_cursor: str,
    reason: str = "legacy_phase_redirect",
) -> dict[str, Any]:
    """Set lease cursor and enqueue execution slice (M6: replaces per-phase Celery chain)."""
    schedule_reason = f"{reason}:{phase_cursor}"
    with session_scope() as session:
        from vector.domains.cortex.execution.lease import _get_or_create_lease

        row = _get_or_create_lease(session, tenant_id=tenant_id)
        row.pipeline_run_id = pipeline_run_id
        row.phase_cursor = phase_cursor
        dirty = mark_tenant_dirty_v1(session, tenant_id=tenant_id, reason=schedule_reason)
        session.commit()
    hint = enqueue_tenant_convergence_v1(tenant_id, reason=schedule_reason)
    return {
        "phase_id": phase_cursor,
        "pipeline_run_id": str(pipeline_run_id),
        "path": "execution_slice",
        **dirty,
        **hint,
    }
