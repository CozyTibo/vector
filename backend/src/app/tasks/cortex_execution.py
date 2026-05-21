"""Authoritative tenant execution slice (single Celery task; M6)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.execution.execution_path_telemetry import (
    EXECUTION_PATH_CONVERGENCE,
    emit_execution_path_telemetry_v1,
)
from vector.domains.cortex.execution.run_tenant_execution import run_tenant_convergence_v1
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_LOGGER = logging.getLogger("app")

_TASK_SLICE = "vector.cortex.execution.run_slice"


@celery_app.task(name=_TASK_SLICE, queue="vector", bind=True, max_retries=2)
def run_execution_slice_task(
    self,
    tenant_id: str,
    reason: str = "worker",
) -> dict[str, Any]:
    """Run one tenant execution slice (inline phases under lease; re-enqueue via lease when incomplete)."""
    cfg = get_settings()
    tid = uuid.UUID(tenant_id)
    emit_execution_path_telemetry_v1(
        tenant_id=tid,
        execution_path=EXECUTION_PATH_CONVERGENCE,
        trigger=f"execution_slice:{reason}",
        celery_task_id=str(self.request.id),
    )
    _LOGGER.info("execution_slice_start tenant_id=%s reason=%s", tenant_id, reason)
    with session_scope() as session:
        out = run_tenant_convergence_v1(
            session,
            tenant_id=tid,
            settings=cfg,
            reason=reason,
            celery_task_id=str(self.request.id),
        )
        session.commit()
    _LOGGER.info("execution_slice_done tenant_id=%s outcome=%s", tenant_id, out.get("outcome"))
    return out
