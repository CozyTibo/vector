"""Post–live-ingestion substrate refresh: Phase 03 drain → identity → Phase 05 graph export."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.ingestion.post_ingestion_substrate_refresh import (
    run_post_ingestion_substrate_refresh,
)
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_LOGGER = logging.getLogger("app")

_TASK = "vector.cortex.post_ingestion_substrate_refresh"


@celery_app.task(name=_TASK, queue="vector")
def run_cortex_post_ingestion_substrate_refresh_task(
    tenant_id: str,
    batch_limit: int | None = None,
) -> dict[str, Any]:
    """Run canonical drain, identity refresh/audit, and graph_projection_export for one tenant."""
    tid = uuid.UUID(tenant_id)
    settings = get_settings()
    _LOGGER.info("post_ingestion_substrate_refresh_start tenant_id=%s", tenant_id)
    with session_scope() as session:
        out = run_post_ingestion_substrate_refresh(
            session,
            settings,
            tenant_id=tid,
            bundle_id=None,
            batch_limit=batch_limit,
            identity_substrate_trigger="cortex_post_ingestion_refresh",
        )
    _LOGGER.info(
        "post_ingestion_substrate_refresh_done tenant_id=%s keys=%s",
        tenant_id,
        list(out.keys()),
    )
    return out
