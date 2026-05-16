"""Debounce and enqueue post–ingestion substrate refresh (canonical → identity → graph)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from vector.settings import Settings, get_settings

_LOGGER = logging.getLogger(__name__)

_REFRESH_TASK_ID_PREFIX = "cortex-post-ingest-refresh-"


def post_ingestion_refresh_celery_task_id(tenant_id: uuid.UUID | str) -> str:
    return f"{_REFRESH_TASK_ID_PREFIX}{tenant_id}"


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

    from app.celery_app import celery_app
    from app.tasks.cortex_post_ingestion_substrate_refresh import (
        run_cortex_post_ingestion_substrate_refresh_task,
    )

    try:
        celery_app.control.revoke(task_id, terminate=False)
    except Exception:  # noqa: BLE001 — best-effort cancel of a prior pending refresh
        pass

    async_result = run_cortex_post_ingestion_substrate_refresh_task.apply_async(
        kwargs={
            "tenant_id": str(tenant_id),
            "batch_limit": cfg.cortex_post_ingestion_canonical_batch_limit,
        },
        queue="vector",
        countdown=debounce,
        task_id=task_id,
    )
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
        "celery_task_id": str(async_result.id),
        "countdown_seconds": debounce,
    }
