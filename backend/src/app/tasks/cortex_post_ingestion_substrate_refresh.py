"""Legacy task name — delegates to substrate pipeline coordinator (phases 02–07)."""

from __future__ import annotations

import logging
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.substrate_pipeline.constants import PIPELINE_TRIGGER_POST_INGESTION

_LOGGER = logging.getLogger("app")

_TASK = "vector.cortex.post_ingestion_substrate_refresh"


@celery_app.task(name=_TASK, queue="vector")
def run_cortex_post_ingestion_substrate_refresh_task(
    tenant_id: str,
    batch_limit: int | None = None,
) -> dict[str, Any]:
    """Run full substrate pipeline (canonical through retrieval) for one tenant."""
    from app.tasks.cortex_substrate_pipeline import run_cortex_substrate_pipeline_coordinator_task

    _LOGGER.info("post_ingestion_substrate_refresh_delegate tenant_id=%s", tenant_id)
    return run_cortex_substrate_pipeline_coordinator_task(
        tenant_id,
        trigger_kind=PIPELINE_TRIGGER_POST_INGESTION,
        bundle_id=None,
        batch_limit=batch_limit,
        reason="legacy_post_ingestion_task",
    )
