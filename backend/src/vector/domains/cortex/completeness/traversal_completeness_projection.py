"""OCTS / traversal completeness (replay walk accounting)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.completeness._completeness_common import build_stage_envelope_v1, pct
from vector.domains.cortex.traversal.runtime.durable_walk_store import resolve_octs_walk_store_v1
from vector.domains.cortex.traversal.traversal_control_plane import build_octs_traversal_control_plane_v1
from vector.infrastructure.db.models.cortex_org_entity import CortexOrgEntity


def _count_graph_entities_v1(session: Session, *, tenant_id: uuid.UUID) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgEntity)
            .where(CortexOrgEntity.tenant_id == tenant_id)
        )
        or 0
    )


def project_traversal_completeness_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    cp = build_octs_traversal_control_plane_v1(session, tenant_id=tenant_id)
    store = resolve_octs_walk_store_v1(session)
    records = store.list_walk_records_for_tenant_v1(tenant_id)
    graph_entity_count = _count_graph_entities_v1(session, tenant_id=tenant_id)
    completed = [r for r in records if r.status == "completed" and r.walk_payload]
    failed = [r for r in records if r.status == "failed"]
    abort_classes = dict(cp.get("abort_classes") or {})

    omission_classes: dict[str, int] = dict(abort_classes)
    frontier_cutoff = int(abort_classes.get("budget_exhausted", 0))
    if frontier_cutoff:
        omission_classes["traversal_frontier_cutoff"] = frontier_cutoff

    unverified = sum(1 for r in records if r.status != "completed")
    if unverified:
        omission_classes["traversal_replay_unverified"] = unverified

    total = len(records)
    replay_covered = len(completed)
    degraded = frontier_cutoff + len(failed)
    replay_posture = "stable" if completed and not failed else ("partial" if completed else "unknown")

    last_ok = None
    if completed:
        wr = completed[0].walk_payload or {}
        wres = wr.get("walk_result") or {}
        last_ok = str(wres.get("walk_result_hash") or "")

    never_executed = total == 0 and graph_entity_count > 0
    intentionally_excluded = 0
    display_total = total
    drift_warnings: list[str] = []

    if never_executed:
        substrate_state = "degraded"
        replay_posture = "unknown"
        omission_classes["traversal_never_executed"] = 1
        intentionally_excluded = graph_entity_count
        display_total = graph_entity_count
        drift_warnings.append(
            "No OCTS walks recorded while org graph has entities — run bounded traversal after link promotion."
        )
    elif total == 0:
        substrate_state = "healthy"
        replay_posture = "unknown"
    else:
        substrate_state = "degraded" if failed or frontier_cutoff else ("healthy" if completed else "degraded")

    if failed:
        drift_warnings.append(f"{len(failed)} failed walk(s)")

    walk_receipts: list[dict[str, Any]] = []
    for rec in completed[:20]:
        wr = (rec.walk_payload or {}).get("walk_result") or {}
        hb = wr.get("hash_body") or {}
        walk_receipts.append(
            {
                "walk_id": str(rec.walk_id),
                "walk_hash": str(wr.get("walk_result_hash") or ""),
                "traversal_epoch": hb.get("traversal_epoch"),
                "frontier_boundary_reason": hb.get("termination_reason"),
                "node_count": len(hb.get("hop_receipts") or []),
                "traversal_gap_detected": False,
            }
        )

    return build_stage_envelope_v1(
        stage_id="traversal",
        label="Traversal",
        total_objects=display_total,
        processed_count=replay_covered,
        degraded_count=degraded,
        unresolved_count=unverified,
        omitted_count=frontier_cutoff,
        intentionally_excluded_count=intentionally_excluded,
        replay_posture=replay_posture,
        substrate_state=substrate_state,
        last_successful_at=last_ok,
        drift_warnings=drift_warnings,
        omission_classes=omission_classes,
        detail_route=f"/admin/tenants/{tenant_id}/cortex/traversal",
        metrics={
            "graph_entity_count": graph_entity_count,
            "walk_record_count": total,
            "traversal_never_executed": never_executed,
            "traversal_replay_coverage_percent": pct(replay_covered, total),
            "frontier_cutoff_count": frontier_cutoff,
            "walk_receipts_sample": walk_receipts,
            "abort_class_histogram": abort_classes,
        },
    )
