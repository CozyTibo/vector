"""Enqueue tenant execution worker (no revoke, no stable task id)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from vector.domains.cortex.execution.execution_path_telemetry import (
    EXECUTION_PATH_CONVERGENCE,
    emit_execution_path_telemetry_v1,
)

_LOGGER = logging.getLogger(__name__)


def enqueue_tenant_convergence_v1(
    tenant_id: uuid.UUID | str,
    *,
    reason: str = "sweeper",
) -> dict[str, Any]:
    """Idempotent hint to run execution slice; durable lease is source of truth."""
    from app.tasks.cortex_convergence import run_tenant_convergence_task

    tid = uuid.UUID(str(tenant_id))
    async_result = run_tenant_convergence_task.apply_async(
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
        "execution_worker_enqueued tenant_id=%s reason=%s celery_task_id=%s",
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
        "execution_path_telemetry": telemetry,
    }


enqueue_tenant_execution_v1 = enqueue_tenant_convergence_v1
