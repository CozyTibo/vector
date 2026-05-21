"""Phase summary + explorer builders for ``GET …/cortex/pipeline/phases/{phase}/*``."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.canonical_control_plane import build_canonical_control_plane
from vector.domains.cortex.canonical.failure_remediation_runtime import sync_canonical_failure_cases
from vector.domains.cortex.canonical.forward_progress.operator_snapshot import (
    build_canonical_forward_progress_snapshot,
)
from vector.domains.cortex.canonical.transform_runtime import (
    list_recent_materializations,
    materialization_public_dict,
)
from vector.domains.cortex.ingestion.admin_overview import build_cortex_ingestion_admin_overview
from vector.domains.cortex.ingestion.admin_recent_raw import list_raw_records_for_connector
from vector.domains.cortex.pipeline.pipeline_admin_overview import build_pipeline_overview_v1
from vector.settings import Settings

_VALID_PHASES = frozenset({"ingestion", "canonical"})


def _assert_phase(phase: str) -> str:
    key = (phase or "").strip().lower()
    if key not in _VALID_PHASES:
        msg = f"unsupported_phase:{phase}"
        raise ValueError(msg)
    return key


def build_phase_summary_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    phase: str,
) -> dict[str, Any]:
    key = _assert_phase(phase)
    overview = build_pipeline_overview_v1(session, settings, tenant_id=tenant_id)
    phase_row = next((p for p in overview["phases"] if p["phase"] == key), None)
    if phase_row is None:
        raise ValueError("phase_not_in_overview")

    if key == "ingestion":
        ing = build_cortex_ingestion_admin_overview(session, settings, tenant_id)
        return {
            "surface_kind": "phase_summary",
            "phase": key,
            "tenant_id": str(tenant_id),
            "status": phase_row["status"],
            "processed_count": phase_row.get("processed_count"),
            "backlog_count": phase_row.get("backlog_count"),
            "last_success_at": phase_row.get("last_success_at"),
            "blockers": phase_row.get("blockers") or [],
            "connectors": ing.get("connectors") or [],
            "checkpoints": [
                {
                    "connector": row["connector"],
                    "checkpoint_last_incremental_at": row.get("checkpoint_last_incremental_at"),
                }
                for row in ing.get("connectors") or []
            ],
        }

    cp = build_canonical_control_plane(session, tenant_id)
    failures = sync_canonical_failure_cases(session, tenant_id)
    forward = build_canonical_forward_progress_snapshot(session, tenant_id=tenant_id)
    h = cp.get("health_overview") or {}
    insp = (cp.get("inspectors") or {}).get("coverage_inspector") or {}
    rollups = insp.get("coverage_connector_rollups") if isinstance(insp, dict) else []
    return {
        "surface_kind": "phase_summary",
        "phase": key,
        "tenant_id": str(tenant_id),
        "status": phase_row["status"],
        "processed_count": phase_row.get("processed_count"),
        "backlog_count": phase_row.get("backlog_count"),
        "last_success_at": phase_row.get("last_success_at"),
        "blockers": phase_row.get("blockers") or [],
        "health": h,
        "forward_progress": forward,
        "failure_count": int(failures.get("active_failure_count") or 0),
        "connector_rollups": rollups if isinstance(rollups, list) else [],
    }


def build_phase_explorer_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    phase: str,
    limit: int = 50,
    offset: int = 0,
    connector: str | None = None,
    resource_type: str | None = None,
    search_query: str | None = None,
    include_health_rows: bool = False,
) -> dict[str, Any]:
    key = _assert_phase(phase)
    lim = max(1, min(int(limit), 200))
    off = max(0, int(offset))

    if key == "ingestion":
        conn = (connector or "slack").strip()
        items, truncated, total = list_raw_records_for_connector(
            session,
            tenant_id,
            conn,
            limit=lim,
            offset=off,
            resource_type=resource_type,
            search_query=search_query,
            include_health_rows=include_health_rows,
        )
        rows = []
        for row in items:
            ingested_at = _iso_timestamp(row.get("fetched_at"))
            rows.append(
            {
                "connector": conn,
                "external_id": row.get("external_id"),
                "ingested_at": ingested_at,
                "resource_type": row.get("resource_type"),
                "payload_preview": _payload_preview(row.get("payload_body")),
                "raw_record_id": row.get("id"),
                "evidence": row,
            }
            )
        return {
            "surface_kind": "phase_explorer",
            "phase": key,
            "tenant_id": str(tenant_id),
            "columns": ["connector", "external_id", "ingested_at", "resource_type", "payload_preview"],
            "items": rows,
            "truncated": truncated,
            "total": total,
            "limit": lim,
            "offset": off,
        }

    mats = list_recent_materializations(session, tenant_id=tenant_id, limit=lim + off)
    page = mats[off : off + lim]
    rows = []
    for mat in page:
        pub = materialization_public_dict(mat)
        rows.append(
            {
                "canonical_type": pub.get("canonical_object_kind"),
                "source": pub.get("source_revision_key") or pub.get("bundle_id"),
                "entity": pub.get("canonical_entity_id"),
                "updated_at": _iso_timestamp(pub.get("canonical_processed_at"))
                or _iso_timestamp(pub.get("created_at")),
                "status": "materialized",
                "materialization_id": pub.get("id"),
                "evidence": pub,
            }
        )
    return {
        "surface_kind": "phase_explorer",
        "phase": key,
        "tenant_id": str(tenant_id),
        "columns": ["canonical_type", "source", "entity", "updated_at", "status"],
        "items": rows,
        "truncated": len(mats) > off + lim,
        "total": len(mats),
        "limit": lim,
        "offset": off,
    }


def _payload_preview(body: Any) -> str:
    if not isinstance(body, dict):
        return ""
    keys = list(body.keys())[:6]
    return ", ".join(keys) if keys else "(empty)"


def _iso_timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return str(value)
