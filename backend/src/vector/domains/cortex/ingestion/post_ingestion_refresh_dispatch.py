"""Mark tenant dirty and enqueue authoritative convergence (no revoke/debounce)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from vector.domains.cortex.execution.enqueue import enqueue_tenant_convergence_v1
from vector.domains.cortex.execution.lease import mark_tenant_dirty_v1
from vector.domains.cortex.execution.execution_path_telemetry import (
    EXECUTION_PATH_CONVERGENCE,
    emit_execution_path_telemetry_v1,
)
from vector.infrastructure.db.session import session_scope
from vector.settings import Settings, get_settings

_LOGGER = logging.getLogger(__name__)


def post_ingestion_refresh_celery_task_id(tenant_id: uuid.UUID | str) -> str:
    """Legacy stable task id — retained for admin diagnostics only."""
    from vector.domains.cortex.substrate_pipeline.orchestrator import (
        substrate_pipeline_celery_task_id,
    )

    return substrate_pipeline_celery_task_id(tenant_id)


def schedule_post_ingestion_substrate_refresh(
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
    reason: str = "ingestion",
) -> dict[str, Any]:
    """After incremental ingest: durable dirty lease + convergence worker hint (M2: sole path)."""
    cfg = settings or get_settings()
    if not cfg.cortex_post_ingestion_substrate_refresh_enabled:
        return {"scheduled": False, "reason": "disabled"}

    with session_scope() as session:
        dirty = mark_tenant_dirty_v1(session, tenant_id=tenant_id, reason=reason)
        session.commit()
    hint = enqueue_tenant_convergence_v1(tenant_id, reason=reason)
    telemetry = emit_execution_path_telemetry_v1(
        tenant_id=tenant_id,
        execution_path=EXECUTION_PATH_CONVERGENCE,
        trigger=f"post_ingestion:{reason}",
        celery_task_id=hint.get("celery_task_id"),
        detail={"obligation_epoch": dirty.get("obligation_epoch")},
    )
    _LOGGER.info(
        "post_ingestion_convergence_marked_dirty tenant_id=%s reason=%s obligation_epoch=%s",
        tenant_id,
        reason,
        dirty.get("obligation_epoch"),
    )
    return {
        "scheduled": True,
        "path": "convergence_lease",
        "execution_path": EXECUTION_PATH_CONVERGENCE,
        "reason": reason,
        "execution_path_telemetry": telemetry,
        **dirty,
        **hint,
    }
