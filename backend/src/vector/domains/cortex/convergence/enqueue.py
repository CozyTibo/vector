"""Enqueue convergence worker (no revoke, no stable task id)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

_LOGGER = logging.getLogger(__name__)


def enqueue_tenant_convergence_v1(
    tenant_id: uuid.UUID | str,
    *,
    reason: str = "sweeper",
) -> dict[str, Any]:
    """Idempotent hint to run convergence; durable lease is source of truth."""
    from app.tasks.cortex_convergence import run_tenant_convergence_task

    tid = uuid.UUID(str(tenant_id))
    async_result = run_tenant_convergence_task.apply_async(
        kwargs={"tenant_id": str(tid), "reason": reason},
        queue="vector",
    )
    _LOGGER.info(
        "convergence_worker_enqueued tenant_id=%s reason=%s celery_task_id=%s",
        tid,
        reason,
        async_result.id,
    )
    return {
        "enqueued": True,
        "tenant_id": str(tid),
        "reason": reason,
        "celery_task_id": str(async_result.id),
    }
