"""Mark tenant dirty and enqueue authoritative convergence (no revoke/debounce)."""

from __future__ import annotations

import uuid
from typing import Any

from vector.domains.cortex.execution.convergence_dispatch import (
    mark_dirty_and_enqueue_convergence_v1,
)
from vector.settings import Settings, get_settings


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
    """After incremental ingest: ``mark_dirty_and_enqueue_convergence_v1`` (compat alias)."""
    return mark_dirty_and_enqueue_convergence_v1(
        tenant_id=tenant_id,
        settings=settings,
        reason=reason,
        telemetry_trigger=f"post_ingestion:{reason}",
    )
