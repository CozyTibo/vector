"""Post-ingestion substrate hooks (removed — ingestion-only cortex retains a no-op API)."""

from __future__ import annotations

import uuid
from typing import Any

from vector.settings import Settings, get_settings


def mark_dirty_and_enqueue_convergence_v1(
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
    reason: str = "ingestion",
    telemetry_trigger: str | None = None,
) -> dict[str, Any]:
    """No-op: downstream substrate pipeline removed."""
    _ = settings, reason, telemetry_trigger
    return {"scheduled": False, "reason": "substrate_pipeline_removed"}


def schedule_post_ingestion_substrate_refresh(
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
    reason: str = "ingestion",
) -> dict[str, Any]:
    """No-op: downstream substrate pipeline removed."""
    _ = tenant_id, reason
    cfg = settings or get_settings()
    if not cfg.cortex_post_ingestion_substrate_refresh_enabled:
        return {"scheduled": False, "reason": "disabled"}
    return {"scheduled": False, "reason": "substrate_pipeline_removed"}
