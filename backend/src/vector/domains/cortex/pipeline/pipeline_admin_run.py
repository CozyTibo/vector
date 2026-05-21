"""``POST …/cortex/pipeline/run`` — operator run/flush facade over execution + ingestion."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.cortex_ingestion_policy import (
    SUPPORTED_CONNECTOR_IDS,
    should_route_ingestion_to_cortex,
)
from vector.domains.cortex.execution.admin_commands import execution_rerun_v1
from vector.domains.cortex.ingestion.admin_overview import build_cortex_ingestion_admin_overview
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.settings import Settings

RunMode = Literal["from_ingestion", "from_phase", "flush_and_run"]
FlushMode = Literal["all", "derived_only"]

_START_PHASE_TO_API: dict[str, str] = {
    "canonical": "CANONICAL",
    "identity": "IDENTITY",
    "graph": "GRAPH",
    "reconstruction": "TCRE",
    "retrieval": "RETRIEVAL",
    "synthesis": "SYNTHESIS",
}

CORTEX_MANUAL_SYNC_CONFIRM_PHRASE = "RUN MANUAL CORTEX INGESTION SYNC"
CORTEX_FLUSH_RERUN_CONFIRM_PHRASE = "FLUSH RAW DATA AND RERUN CORTEX THROUGH PHASE 07"
CORTEX_FLUSH_DERIVED_CONFIRM_PHRASE = "FLUSH DERIVED CORTEX DATA AND RERUN FROM CANONICAL"


def _runnable_connectors(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
) -> list[str]:
    overview = build_cortex_ingestion_admin_overview(session, settings, tenant_id)
    return [
        str(row["connector"])
        for row in overview.get("connectors") or []
        if row.get("cortex_routed") and row.get("connection_status") == "active"
    ]


def _enqueue_connector_syncs(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    connectors: list[str],
) -> list[dict[str, Any]]:
    from app.tasks.cortex_ingestion_sync import run_cortex_connector_sync_task

    stmt = (
        select(TenantConnection)
        .where(
            TenantConnection.tenant_id == tenant_id,
            TenantConnection.status == "active",
        )
        .order_by(TenantConnection.provider.asc(), TenantConnection.created_at.desc())
    )
    conns = list(session.scalars(stmt).all())
    by_provider: dict[str, TenantConnection] = {}
    for conn_row in conns:
        if conn_row.provider not in by_provider:
            by_provider[conn_row.provider] = conn_row

    enqueued: list[dict[str, Any]] = []
    for connector in connectors:
        if connector not in SUPPORTED_CONNECTOR_IDS:
            continue
        if not should_route_ingestion_to_cortex(settings, connector, tenant_id):
            continue
        tc: TenantConnection | None = by_provider.get(connector)
        if tc is None:
            enqueued.append({"connector": connector, "ok": False, "detail": "no_active_connection"})
            continue
        run_cortex_connector_sync_task.delay(
            str(tenant_id),
            connector,
            "pipeline_run_from_ingestion",
            "incremental",
            str(tc.id),
        )
        enqueued.append({"connector": connector, "ok": True, "connection_id": str(tc.id)})
    return enqueued


def pipeline_run_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    mode: RunMode,
    start_phase: str | None = None,
    flush_mode: FlushMode | None = None,
    confirmation: str | None = None,
) -> dict[str, Any]:
    if mode == "from_ingestion":
        if confirmation != CORTEX_MANUAL_SYNC_CONFIRM_PHRASE:
            raise ValueError("confirmation_mismatch")
        connectors = _runnable_connectors(session, settings, tenant_id=tenant_id)
        syncs = _enqueue_connector_syncs(
            session, settings, tenant_id=tenant_id, connectors=connectors
        )
        return {
            "surface_kind": "pipeline_run",
            "mode": mode,
            "tenant_id": str(tenant_id),
            "connector_syncs": syncs,
            "hint": "Post-ingest dispatch marks tenant dirty and enqueues execution convergence.",
        }

    if mode == "from_phase":
        key = (start_phase or "").strip().lower()
        api_phase = _START_PHASE_TO_API.get(key)
        if api_phase is None:
            raise ValueError(f"unsupported_start_phase:{start_phase}")
        out = execution_rerun_v1(session, tenant_id=tenant_id, from_phase=api_phase)
        return {
            "surface_kind": "pipeline_run",
            "mode": mode,
            "tenant_id": str(tenant_id),
            "start_phase": key,
            "execution": out,
        }

    if mode == "flush_and_run":
        fm = flush_mode or "derived_only"
        if fm == "all":
            if confirmation != CORTEX_FLUSH_RERUN_CONFIRM_PHRASE:
                raise ValueError("confirmation_mismatch")
            cleared = execution_rerun_v1(
                session,
                tenant_id=tenant_id,
                from_phase="CANONICAL",
                flush_all=True,
            )
            connectors = _runnable_connectors(session, settings, tenant_id=tenant_id)
            syncs = _enqueue_connector_syncs(
                session, settings, tenant_id=tenant_id, connectors=connectors
            )
            return {
                "surface_kind": "pipeline_run",
                "mode": mode,
                "flush_mode": fm,
                "tenant_id": str(tenant_id),
                "execution": cleared,
                "connector_syncs": syncs,
            }
        if confirmation != CORTEX_FLUSH_DERIVED_CONFIRM_PHRASE:
            raise ValueError("confirmation_mismatch")
        out = execution_rerun_v1(session, tenant_id=tenant_id, from_phase="CANONICAL")
        return {
            "surface_kind": "pipeline_run",
            "mode": mode,
            "flush_mode": fm,
            "tenant_id": str(tenant_id),
            "execution": out,
        }

    raise ValueError(f"unsupported_mode:{mode}")
