"""Tenant-scoped Cortex flush + rerun through Phase 07 (ingestion → … → retrieval index)."""

from __future__ import annotations

import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.execution.execution_path_telemetry import emit_admin_bypass_telemetry_v1
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PIPELINE_TRIGGER_FLUSH_RERUN,
)
from vector.domains.cortex.substrate_pipeline.orchestrator import (
    enqueue_next_pipeline_phase_v1,
    start_substrate_pipeline_run_v1,
)
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_TASK_FULL_RERUN = "vector.cortex.ingestion.flush_rerun_to_identity"


@celery_app.task(name=_TASK_FULL_RERUN, queue="cortex_live")
def run_cortex_flush_rerun_to_identity_task(
    tenant_id: str,
    bundle_id: str,
    connectors: list[dict[str, str]],
    batch_limit: int,
) -> dict[str, Any]:
    """Ingest syncs, substrate refresh (canonical → identity → graph → TCRE → retrieval index)."""
    tid = uuid.UUID(tenant_id)
    emit_admin_bypass_telemetry_v1(
        tenant_id=tid,
        admin_action="flush_rerun_to_identity",
        celery_task_id=str(run_cortex_flush_rerun_to_identity_task.request.id),
        detail={"bundle_id": bundle_id, "connector_count": len(connectors)},
    )
    settings = get_settings()
    sync_results: list[dict[str, Any]] = []
    with session_scope() as session:
        for row in connectors:
            connector_id = str(row.get("connector") or "").strip()
            connection_id = str(row.get("connection_id") or "").strip()
            if not connector_id or not connection_id:
                sync_results.append(
                    {
                        "connector": connector_id or "unknown",
                        "ok": False,
                        "error": "invalid_connector_payload",
                    }
                )
                continue
            try:
                out = execute_connector_sync(
                    session,
                    settings,
                    tenant_id=tid,
                    connector_id=connector_id,
                    source_trigger="manual_admin_flush_rerun",
                    ingestion_sync_context=IngestionSyncContext.live_incremental(),
                    connection_id=uuid.UUID(connection_id),
                )
                sync_results.append(
                    {
                        "connector": connector_id,
                        "ok": True,
                        "raw_rows_written": out.get("raw_rows_written"),
                        "run_id": out.get("run_id"),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                sync_results.append(
                    {
                        "connector": connector_id,
                        "ok": False,
                        "error": str(exc),
                    }
                )
        run_id, created = start_substrate_pipeline_run_v1(
            session,
            tenant_id=tid,
            trigger_kind=PIPELINE_TRIGGER_FLUSH_RERUN,
            bundle_id=bundle_id.strip(),
        )
        session.commit()
    first_phase = enqueue_next_pipeline_phase_v1(
        tenant_id=tid,
        pipeline_run_id=run_id,
        phase_id=PHASE_02_CANONICAL,
        bundle_id=bundle_id.strip(),
        batch_limit=batch_limit,
        identity_substrate_trigger="cortex_flush_rerun",
    )
    return {
        "tenant_id": tenant_id,
        "bundle_id": bundle_id.strip(),
        "sync_results": sync_results,
        "pipeline_run_id": str(run_id),
        "pipeline_created": created,
        "first_phase": first_phase,
    }
