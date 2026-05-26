"""Single authoritative entry: mark tenant dirty + enqueue convergence worker."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from vector.domains.cortex.execution.enqueue import enqueue_tenant_convergence_v1
from vector.domains.cortex.execution.execution_path_telemetry import (
    EXECUTION_PATH_CONVERGENCE,
    emit_execution_path_telemetry_v1,
)
from vector.domains.cortex.execution.lease import mark_tenant_dirty_v1
from vector.domains.cortex.substrate_pipeline.substrate_contract_v1 import build_ingest_handoff_v1
from vector.infrastructure.db.session import session_scope
from vector.settings import Settings, get_settings

_LOGGER = logging.getLogger(__name__)


def mark_dirty_and_enqueue_convergence_v1(
    *,
    tenant_id: uuid.UUID,
    reason: str,
    settings: Settings | None = None,
    telemetry_trigger: str | None = None,
) -> dict[str, Any]:
    """Mark durable dirty obligation and enqueue convergence (sole live scheduling path)."""
    cfg = settings or get_settings()
    if not cfg.cortex_post_ingestion_substrate_refresh_enabled:
        return {
            "scheduled": False,
            "reason": "disabled",
            "ingest_handoff_v1": build_ingest_handoff_v1(
                dirty_enqueued=False,
                obligation_epoch=None,
                reason="disabled",
            ),
        }

    with session_scope() as session:
        dirty = mark_tenant_dirty_v1(session, tenant_id=tenant_id, reason=reason)
        session.commit()
    hint = enqueue_tenant_convergence_v1(tenant_id, reason=reason)
    trigger = telemetry_trigger or f"convergence_dispatch:{reason}"
    telemetry = emit_execution_path_telemetry_v1(
        tenant_id=tenant_id,
        execution_path=EXECUTION_PATH_CONVERGENCE,
        trigger=trigger,
        celery_task_id=hint.get("celery_task_id"),
        detail={"obligation_epoch": dirty.get("obligation_epoch"), "reason": reason},
    )
    _LOGGER.info(
        "convergence_dispatch tenant_id=%s reason=%s obligation_epoch=%s",
        tenant_id,
        reason,
        dirty.get("obligation_epoch"),
    )
    obligation_epoch = dirty.get("obligation_epoch")
    if obligation_epoch is not None:
        obligation_epoch = int(obligation_epoch)
    return {
        "scheduled": True,
        "path": "convergence_lease",
        "execution_path": EXECUTION_PATH_CONVERGENCE,
        "reason": reason,
        "execution_path_telemetry": telemetry,
        "ingest_handoff_v1": build_ingest_handoff_v1(
            dirty_enqueued=True,
            obligation_epoch=obligation_epoch,
            reason=reason,
            celery_task_id=str(hint.get("celery_task_id") or "") or None,
        ),
        **dirty,
        **hint,
    }
