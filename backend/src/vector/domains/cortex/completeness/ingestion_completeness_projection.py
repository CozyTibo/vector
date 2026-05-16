"""Ingestion-layer substrate completeness (raw exhaust accounting)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.completeness._completeness_common import build_stage_envelope_v1, pct
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def project_ingestion_completeness_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    raw_total = int(
        session.scalar(
            select(func.count())
            .select_from(RawIngestionRecord)
            .where(RawIngestionRecord.tenant_id == tenant_id)
        )
        or 0
    )
    runs = list(
        session.scalars(
            select(IngestionRun)
            .where(IngestionRun.tenant_id == tenant_id)
            .order_by(IngestionRun.started_at.desc())
            .limit(100)
        ).all()
    )
    completed = [r for r in runs if r.status == "completed"]
    failed = [r for r in runs if r.status == "failed"]
    observed_rows = 0
    duplicate_estimate = 0
    for r in completed:
        stats = r.stats if isinstance(r.stats, dict) else {}
        observed_rows += int(stats.get("raw_rows_written") or stats.get("rows_written") or 0)
        duplicate_estimate += int(stats.get("duplicate_rows") or 0)

    omission_classes: dict[str, int] = {}
    if failed:
        omission_classes["partial_api_failure"] = len(failed)
    degraded_connectors = sum(1 for r in runs if r.status in ("failed", "cancelled"))
    if degraded_connectors:
        omission_classes["ingestion_connector_degraded"] = degraded_connectors
    if raw_total == 0 and runs:
        omission_classes["ingestion_window_missing"] = 1

    replay_posture = "stable" if not failed else "partial"
    if raw_total == 0 and not runs:
        replay_posture = "unknown"

    last_ok = completed[0].finished_at.isoformat() if completed and completed[0].finished_at else None
    substrate_state = "critical" if raw_total == 0 and runs else ("degraded" if failed else "healthy")

    connector_receipts: list[dict[str, Any]] = []
    by_connector: dict[str, list[IngestionRun]] = {}
    for r in runs:
        by_connector.setdefault(r.connector, []).append(r)
    for conn, conn_runs in sorted(by_connector.items()):
        conn_failed = sum(1 for x in conn_runs if x.status == "failed")
        conn_observed = sum(
            int((x.stats or {}).get("raw_rows_written") or 0)
            for x in conn_runs
            if x.status == "completed" and isinstance(x.stats, dict)
        )
        connector_receipts.append(
            {
                "connector_type": conn,
                "sync_count": len(conn_runs),
                "observed_event_count": conn_observed,
                "failed_fetch_count": conn_failed,
                "ingestion_gap_detected": conn_failed > 0,
                "replay_safe_sync_identity": (
                    str(conn_runs[0].id) if conn_runs and conn_runs[0].status == "completed" else None
                ),
            }
        )

    stage = build_stage_envelope_v1(
        stage_id="ingestion",
        label="Raw exhaust",
        total_objects=max(raw_total, observed_rows),
        processed_count=raw_total,
        degraded_count=len(failed),
        unresolved_count=0 if raw_total else (1 if runs else 0),
        omitted_count=len(failed),
        replay_posture=replay_posture,
        substrate_state=substrate_state,
        last_successful_at=last_ok,
        drift_warnings=[f"{len(failed)} failed sync run(s)"] if failed else [],
        omission_classes=omission_classes,
        detail_route=f"/admin/tenants/{tenant_id}/cortex/ingestion",
        metrics={
            "raw_event_total": raw_total,
            "ingestion_run_count": len(runs),
            "completed_run_count": len(completed),
            "failed_run_count": len(failed),
            "duplicate_event_estimate": duplicate_estimate,
            "ingestion_coverage_percent": pct(raw_total, max(observed_rows, raw_total, 1)),
            "connector_receipts": connector_receipts,
        },
    )
    return stage
