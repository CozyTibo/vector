"""Post-ingestion downstream scheduling (canon + identity passes)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from vector.settings import Settings, get_settings

_LOGGER = logging.getLogger(__name__)


def schedule_post_ingestion_substrate_refresh(
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
    reason: str = "ingestion",
) -> dict[str, Any]:
    """Enqueue canon and identity passes after a successful live incremental sync."""
    cfg = settings or get_settings()
    if not cfg.cortex_post_ingestion_substrate_refresh_enabled:
        return {"scheduled": False, "reason": "disabled"}

    tid = str(tenant_id)
    enqueued: list[str] = []

    if cfg.cortex_canon_scheduler_enabled:
        from app.tasks.cortex_canon_sync import run_cortex_canon_pass_task

        run_cortex_canon_pass_task.delay(tid, source_trigger="ingestion_complete")
        enqueued.append("canon_pass")

    if cfg.cortex_identity_scheduler_enabled:
        from app.tasks.cortex_identity_sync import run_cortex_identity_pass_task

        run_cortex_identity_pass_task.delay(tid, source_trigger="ingestion_complete")
        enqueued.append("identity_pass")

    if not enqueued:
        return {"scheduled": False, "reason": "downstream_schedulers_disabled"}

    _LOGGER.info(
        "post-ingestion downstream scheduled tenant=%s reason=%s lanes=%s",
        tid,
        reason,
        enqueued,
    )
    return {"scheduled": True, "reason": reason, "enqueued": enqueued}


def mark_dirty_and_enqueue_convergence_v1(
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
    reason: str = "ingestion",
    telemetry_trigger: str | None = None,
) -> dict[str, Any]:
    """Redirect legacy convergence hook to post-ingestion downstream passes."""
    _ = telemetry_trigger
    return schedule_post_ingestion_substrate_refresh(
        tenant_id=tenant_id,
        settings=settings,
        reason=reason,
    )
