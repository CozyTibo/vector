"""Mark tenant dirty and enqueue authoritative convergence (no revoke/debounce)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from vector.domains.cortex.execution.execution_path_telemetry import (
    EXECUTION_PATH_CONVERGENCE,
    EXECUTION_PATH_LEGACY,
    emit_execution_path_telemetry_v1,
)
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
    """After incremental ingest: durable dirty lease + convergence worker hint."""
    cfg = settings or get_settings()
    if not cfg.cortex_post_ingestion_substrate_refresh_enabled:
        return {"scheduled": False, "reason": "disabled"}

    if cfg.cortex_convergence_runtime_enabled:
        from vector.domains.cortex.convergence.enqueue import enqueue_tenant_convergence_v1
        from vector.domains.cortex.convergence.lease import mark_tenant_dirty_v1
        from vector.infrastructure.db.session import session_scope

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

    debounce = max(30, int(cfg.cortex_post_ingestion_substrate_refresh_debounce_seconds))
    task_id = post_ingestion_refresh_celery_task_id(tenant_id)

    from vector.domains.cortex.substrate_pipeline.orchestrator import schedule_substrate_pipeline_v1

    result = schedule_substrate_pipeline_v1(
        tenant_id=tenant_id,
        settings=cfg,
        trigger_kind="post_ingestion",
        batch_limit=cfg.cortex_post_ingestion_canonical_batch_limit,
        reason=reason,
    )
    if not result.get("scheduled"):
        return result
    async_result_id = result.get("celery_task_id")
    telemetry = emit_execution_path_telemetry_v1(
        tenant_id=tenant_id,
        execution_path=EXECUTION_PATH_LEGACY,
        trigger=f"post_ingestion:{reason}",
        celery_task_id=async_result_id,
        detail={"countdown_seconds": debounce, "schedule_action": result.get("schedule_action")},
    )
    _LOGGER.info(
        "post_ingestion_substrate_refresh_scheduled tenant_id=%s reason=%s countdown_s=%s",
        tenant_id,
        reason,
        debounce,
    )
    return {
        "scheduled": True,
        "path": "legacy_debounced_coordinator",
        "execution_path": EXECUTION_PATH_LEGACY,
        "reason": reason,
        "task_id": task_id,
        "celery_task_id": async_result_id,
        "countdown_seconds": debounce,
        "execution_path_telemetry": telemetry,
    }
