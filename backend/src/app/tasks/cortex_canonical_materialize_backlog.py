"""Background drain for Phase 03 canonical backlog (tenant-scoped, route-routable)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.canonical.transform_runtime import drain_stub_materialize_backlog
from vector.infrastructure.db.session import session_scope

_LOGGER = logging.getLogger("app")

_TASK_DRAIN_STUB_BACKLOG = "vector.cortex.canonical.drain_stub_materialize_backlog"


@celery_app.task(name=_TASK_DRAIN_STUB_BACKLOG)
def drain_stub_materialize_backlog_task(
    tenant_id: str,
    bundle_id: str,
    connector: str | None = None,
    resource_type: str | None = None,
    batch_limit: int | None = None,
) -> dict[str, Any]:
    """Process all route-routable missing materializations for ``bundle_id`` (batched loop)."""
    tid = uuid.UUID(tenant_id)
    bid = bundle_id.strip()
    _LOGGER.info(
        "canonical_stub_backlog_drain_start tenant_id=%s bundle_id=%s connector=%s resource_type=%s batch_limit=%s",
        tenant_id,
        bid,
        connector,
        resource_type,
        batch_limit,
    )
    with session_scope() as session:
        summary = drain_stub_materialize_backlog(
            session,
            tenant_id=tid,
            bundle_id=bid,
            connector=connector,
            resource_type=resource_type,
            batch_limit=batch_limit,
        )
    _LOGGER.info(
        "canonical_stub_backlog_drain_done tenant_id=%s bundle_id=%s batches=%s attempted=%s succeeded=%s failed_rows=%s",
        tenant_id,
        bid,
        summary.get("batches_run"),
        summary.get("total_attempted"),
        summary.get("total_succeeded"),
        summary.get("total_failed_rows"),
    )
    return summary
