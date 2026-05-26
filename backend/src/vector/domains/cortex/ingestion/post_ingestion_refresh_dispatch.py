"""Mark tenant dirty and enqueue authoritative convergence (no revoke/debounce)."""

from __future__ import annotations

import uuid
from typing import Any

from vector.domains.cortex.execution.convergence_dispatch import (
    mark_dirty_and_enqueue_convergence_v1 as _mark_dirty_and_enqueue_convergence_v1,
)
from vector.domains.cortex.execution.execution_event_triggers import (
    trigger_post_ingestion_execution_v1,
)
from vector.settings import Settings, get_settings


def mark_dirty_and_enqueue_convergence_v1(
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
    reason: str = "ingestion",
    telemetry_trigger: str | None = None,
) -> dict[str, Any]:
    """Re-export for tests and legacy import paths."""
    _ = settings
    return _mark_dirty_and_enqueue_convergence_v1(
        tenant_id=tenant_id,
        reason=reason,
        telemetry_trigger=telemetry_trigger or f"post_ingestion:{reason}",
    )


def schedule_post_ingestion_substrate_refresh(
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
    reason: str = "ingestion",
) -> dict[str, Any]:
    """After incremental ingest: P2-B mark dirty + enqueue convergence (compat alias)."""
    cfg = settings or get_settings()
    if not cfg.cortex_post_ingestion_substrate_refresh_enabled:
        return {"scheduled": False, "reason": "disabled"}
    triggered = trigger_post_ingestion_execution_v1(tenant_id=tenant_id, reason=reason)
    if not triggered.get("triggered"):
        return {"scheduled": False, "reason": triggered.get("reason", "not_triggered")}
    dispatch = dict(triggered.get("dispatch") or {})
    return {**dispatch, "scheduled": bool(dispatch.get("scheduled", True))}
