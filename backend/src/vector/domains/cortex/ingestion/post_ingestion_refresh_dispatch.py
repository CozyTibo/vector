"""Debounce and enqueue post–ingestion substrate pipeline (canonical → … → retrieval)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from vector.settings import Settings, get_settings

_LOGGER = logging.getLogger(__name__)

def post_ingestion_refresh_celery_task_id(tenant_id: uuid.UUID | str) -> str:
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
    """Schedule one substrate refresh per tenant after a debounce window.

    Each call resets the countdown so multi-connector scheduled ticks coalesce into a
    single refresh after the last successful incremental sync finishes (or after the
    tick enqueues the last connector for that tenant).
    """
    cfg = settings or get_settings()
    if not cfg.cortex_post_ingestion_substrate_refresh_enabled:
        return {"scheduled": False, "reason": "disabled"}

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
    _LOGGER.info(
        "post_ingestion_substrate_refresh_scheduled tenant_id=%s reason=%s countdown_s=%s",
        tenant_id,
        reason,
        debounce,
    )
    return {
        "scheduled": True,
        "reason": reason,
        "task_id": task_id,
        "celery_task_id": async_result_id,
        "countdown_seconds": debounce,
    }
