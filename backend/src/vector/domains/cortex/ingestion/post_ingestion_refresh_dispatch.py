"""Post-ingestion downstream scheduling (canon + identity passes via cortex_passes)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from vector.domains.cortex.runtime.pass_types import CANON_PASS, GRAPH_PROJECTION_PASS, IDENTITY_PASS
from vector.domains.cortex.runtime.queue import upsert_pending_pass_v1
from vector.infrastructure.db.session import session_scope
from vector.settings import Settings, get_settings

_LOGGER = logging.getLogger(__name__)


def schedule_post_ingestion_substrate_refresh(
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
    reason: str = "ingestion",
) -> dict[str, Any]:
    """Enqueue pending canon/identity pass rows after a successful live incremental sync."""
    cfg = settings or get_settings()
    if not cfg.cortex_post_ingestion_substrate_refresh_enabled:
        return {"scheduled": False, "reason": "disabled"}

    enqueued: list[str] = []
    with session_scope() as session:
        if cfg.cortex_canon_scheduler_enabled:
            upsert_pending_pass_v1(
                session,
                tenant_id=tenant_id,
                pass_type=CANON_PASS,
                source_trigger="ingestion_complete",
                priority=10,
            )
            enqueued.append("canon_pass")
        if cfg.cortex_identity_scheduler_enabled:
            upsert_pending_pass_v1(
                session,
                tenant_id=tenant_id,
                pass_type=IDENTITY_PASS,
                source_trigger="ingestion_complete",
                priority=10,
            )
            enqueued.append("identity_pass")
        if cfg.cortex_graph_scheduler_enabled:
            upsert_pending_pass_v1(
                session,
                tenant_id=tenant_id,
                pass_type=GRAPH_PROJECTION_PASS,
                source_trigger="ingestion_complete",
                priority=10,
            )
            enqueued.append("graph_projection_pass")

    if not enqueued:
        return {"scheduled": False, "reason": "downstream_schedulers_disabled"}

    _LOGGER.info(
        "post-ingestion passes scheduled tenant=%s reason=%s lanes=%s",
        tenant_id,
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
    _ = telemetry_trigger
    return schedule_post_ingestion_substrate_refresh(
        tenant_id=tenant_id,
        settings=settings,
        reason=reason,
    )
