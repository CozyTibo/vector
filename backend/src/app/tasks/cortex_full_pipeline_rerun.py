"""Tenant-scoped Cortex flush + rerun: P04 identity substrate then P05 graph projection ingress."""

from __future__ import annotations

import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.ingestion.post_ingestion_substrate_refresh import (
    run_post_ingestion_substrate_refresh,
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
    """Ingest syncs, canonical drain, identity audit, then Phase 05 org graph projection export."""
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
        substrate = run_post_ingestion_substrate_refresh(
            session,
            settings,
            tenant_id=tid,
            bundle_id=bundle_id.strip(),
            batch_limit=batch_limit,
            identity_substrate_trigger="cortex_flush_rerun",
        )
        return {
            "tenant_id": tenant_id,
            "bundle_id": bundle_id.strip(),
            "sync_results": sync_results,
            "canonical_summary": substrate.get("canonical_summary"),
            "determinism_repair": substrate.get("determinism_repair"),
            "identity_continuity_substrate": substrate.get("identity_continuity_substrate"),
            "identity_substrate_audit": substrate.get("identity_substrate_audit"),
            "identity_substrate_audit_replay_job_id": substrate.get(
                "identity_substrate_audit_replay_job_id"
            ),
            "identity_backfill_summary": substrate.get("identity_continuity_substrate"),
            "phase05_graph_projection_export_job_id": substrate.get(
                "phase05_graph_projection_export_job_id"
            ),
            "phase05_graph_projection_stable_hash_sha256": substrate.get(
                "phase05_graph_projection_stable_hash_sha256"
            ),
            "phase05_org_graph_traversal_verification_slice": substrate.get(
                "phase05_org_graph_traversal_verification_slice"
            ),
            "phase05_org_graph_traversal_slice_hash": substrate.get(
                "phase05_org_graph_traversal_slice_hash"
            ),
        }
