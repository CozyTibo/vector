"""Legacy task name — delegates to convergence dispatch (M4)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app

_LOGGER = logging.getLogger("app")

_TASK = "vector.cortex.post_ingestion_substrate_refresh"


@celery_app.task(name=_TASK, queue="vector")
def run_cortex_post_ingestion_substrate_refresh_task(
    tenant_id: str,
    batch_limit: int | None = None,
) -> dict[str, Any]:
    """Mark tenant dirty and enqueue convergence worker (legacy Celery entrypoint)."""
    del batch_limit  # convergence resolves batch limits from settings
    from vector.domains.cortex.ingestion.post_ingestion_refresh_dispatch import (
        schedule_post_ingestion_substrate_refresh,
    )

    _LOGGER.info("post_ingestion_substrate_refresh_convergence tenant_id=%s", tenant_id)
    return schedule_post_ingestion_substrate_refresh(
        tenant_id=uuid.UUID(tenant_id),
        reason="legacy_post_ingestion_task",
    )
