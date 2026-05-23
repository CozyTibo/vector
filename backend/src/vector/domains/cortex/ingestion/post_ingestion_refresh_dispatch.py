"""Mark tenant dirty and enqueue authoritative convergence (no revoke/debounce)."""

from __future__ import annotations

import uuid
from typing import Any

from vector.domains.cortex.execution.execution_event_triggers import (
    trigger_post_ingestion_execution_v1,
)
from vector.settings import Settings


def post_ingestion_refresh_celery_task_id(tenant_id: uuid.UUID | str) -> str:
    """Legacy stable task id — retained for admin diagnostics only."""
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
    """After incremental ingest: P2-B mark dirty + enqueue convergence (compat alias)."""
    _ = settings
    return trigger_post_ingestion_execution_v1(tenant_id=tenant_id, reason=reason)
