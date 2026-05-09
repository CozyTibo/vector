"""Background orchestration for tenant-scoped Cortex flush+rereun to canonical."""

from __future__ import annotations

import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.canonical.transform_runtime import drain_stub_materialize_backlog
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext
from vector.domains.cortex.ingestion.sync_executor import execute_connector_sync
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_TASK_FULL_RERUN = "vector.cortex.ingestion.flush_rerun_to_canonical"


@celery_app.task(name=_TASK_FULL_RERUN, queue="cortex_live")
def run_cortex_flush_rerun_to_canonical_task(
    tenant_id: str,
    bundle_id: str,
    connectors: list[dict[str, str]],
    batch_limit: int,
) -> dict[str, Any]:
    """Run connector syncs sequentially, then canonical backlog drain."""
    tid = uuid.UUID(tenant_id)
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
        canonical_summary = drain_stub_materialize_backlog(
            session,
            tenant_id=tid,
            bundle_id=bundle_id.strip(),
            connector=None,
            resource_type=None,
            batch_limit=batch_limit,
        )
    return {
        "tenant_id": tenant_id,
        "bundle_id": bundle_id.strip(),
        "sync_results": sync_results,
        "canonical_summary": canonical_summary,
    }
