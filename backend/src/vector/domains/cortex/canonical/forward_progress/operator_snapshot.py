"""Operator truth surface for canonical forward-progress runtime."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.deferral_store import (
    count_deferrals,
    summarize_deferral_pressure,
    summarize_topology_parent_gaps,
)
from vector.domains.cortex.canonical.forward_progress.pass_fairness import parse_pass_cooldown_until
from vector.domains.cortex.canonical.forward_progress.metrics import build_forward_progress_metrics
from vector.domains.cortex.canonical.forward_progress.candidate_selection import (
    list_untreated_routable_count_estimate,
)
from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform
from vector.domains.cortex.convergence.lease import get_convergence_lease_v1
from vector.domains.cortex.substrate_pipeline.constants import PHASE_02_CANONICAL
from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1
from vector.infrastructure.db.models.cortex_canonical_materialization_deferral import (
    CortexCanonicalMaterializationDeferral,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePipelineRun


def build_canonical_forward_progress_snapshot(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str | None = None,
    deferral_sample_limit: int = 40,
) -> dict[str, Any]:
    bid = (bundle_id or "").strip() or resolve_default_bundle_id_for_stub_transform(db, tenant_id)
    if bid is None:
        return {"tenant_id": str(tenant_id), "bundle_id": None, "reason": "no_transformable_bundle"}

    untreated = list_untreated_routable_count_estimate(db, tenant_id=tenant_id, bundle_id=bid)
    deferral_counts = count_deferrals(db, tenant_id=tenant_id, bundle_id=bid)
    metrics = build_forward_progress_metrics(
        db,
        tenant_id=tenant_id,
        bundle_id=bid,
        untreated_estimate=untreated,
        deferral_counts=deferral_counts,
        total_succeeded=0,
        elapsed_ms=0,
    )

    lease = get_convergence_lease_v1(db, tenant_id=tenant_id)
    lease_doc: dict[str, Any] | None = None
    phase_02_doc: dict[str, Any] | None = None
    lease_detail: dict[str, Any] = {}
    if lease is not None:
        lease_detail = lease.detail_json if isinstance(lease.detail_json, dict) else {}
        lease_doc = {
            "status": lease.status,
            "obligation_epoch": int(lease.obligation_epoch),
            "target_epoch": int(lease.target_epoch),
            "phase_cursor": lease.phase_cursor,
            "next_attempt_at": lease.next_attempt_at.isoformat() if lease.next_attempt_at else None,
            "last_canonical_outcome": lease_detail.get("last_canonical_outcome"),
            "canonical_pass_index": lease_detail.get("canonical_pass_index"),
            "convergence_health": lease_detail.get("convergence_health"),
            "pass_cooldown_until": lease_detail.get("pass_cooldown_until"),
            "pass_topology_stall_counts": lease_detail.get("pass_topology_stall_counts"),
        }
        if lease.pipeline_run_id is not None:
            pr = db.get(CortexSubstratePipelineRun, lease.pipeline_run_id)
            if pr is not None:
                phase = get_phase_run_v1(db, pipeline_run_id=pr.id, phase_id=PHASE_02_CANONICAL)
                if phase is not None:
                    out = phase.output_json if isinstance(phase.output_json, dict) else {}
                    canonical_summary = out.get("canonical_summary")
                    summary = (
                        canonical_summary
                        if isinstance(canonical_summary, dict)
                        else {}
                    )
                    phase_02_doc = {
                        "status": phase.status,
                        "waiting_reason": phase.error_detail,
                        "canonical_outcome": out.get("canonical_outcome") or summary.get("canonical_outcome"),
                        "total_succeeded": summary.get("total_succeeded"),
                        "topology_wait": summary.get("topology_wait"),
                        "zero_progress_spin_detected": summary.get("zero_progress_spin_detected"),
                        "deferral_counts": summary.get("deferral_counts"),
                    }

    deferrals = db.scalars(
        select(CortexCanonicalMaterializationDeferral)
        .where(
            CortexCanonicalMaterializationDeferral.tenant_id == tenant_id,
            CortexCanonicalMaterializationDeferral.bundle_id == bid,
        )
        .order_by(CortexCanonicalMaterializationDeferral.deferred_at.desc())
        .limit(max(1, min(deferral_sample_limit, 200)))
    ).all()
    deferral_sample = [
        {
            "raw_record_id": int(d.raw_record_id),
            "connector": d.connector,
            "resource_type": d.resource_type,
            "deferral_reason": d.deferral_reason,
            "queue": d.queue,
            "parent_raw_record_id": d.parent_raw_record_id,
            "missing_parent_ref": d.missing_parent_ref,
            "retry_ready_at": d.retry_ready_at.isoformat() if d.retry_ready_at else None,
            "pass_key": d.pass_key,
        }
        for d in deferrals
    ]

    deferral_pressure = summarize_deferral_pressure(db, tenant_id=tenant_id, bundle_id=bid)
    topology_parent_gaps = summarize_topology_parent_gaps(db, tenant_id=tenant_id, bundle_id=bid)
    metrics["deferral_pressure_sample"] = deferral_pressure
    metrics["topology_parent_gaps_sample"] = topology_parent_gaps
    guidance = _build_operator_guidance(
        untreated=untreated,
        deferral_pressure=deferral_pressure,
        deferral_counts=deferral_counts,
        lease_detail=lease_detail,
        phase_02_doc=phase_02_doc,
    )

    return {
        "tenant_id": str(tenant_id),
        "bundle_id": bid,
        "metrics": metrics,
        "convergence_lease": lease_doc,
        "phase_02_canonical": phase_02_doc,
        "deferral_sample": deferral_sample,
        "deferral_pressure": deferral_pressure,
        "topology_parent_gaps": topology_parent_gaps,
        "operator_guidance": guidance,
    }


def _build_operator_guidance(
    *,
    untreated: int,
    deferral_pressure: list[dict[str, Any]],
    deferral_counts: dict[str, int],
    lease_detail: dict[str, Any],
    phase_02_doc: dict[str, Any] | None,
) -> str | None:
    if untreated <= 0:
        return "Substrate canonical coverage is complete for routable pairs."
    lines: list[str] = []
    permanent = int(deferral_counts.get("deferred_permanent_orphan") or 0)
    if permanent > 0:
        lines.append(
            f"{permanent:,} rows classified as permanent topology orphans (missing ingest parents)."
        )
    for row in deferral_pressure[:5]:
        rt = str(row.get("resource_type") or "")
        reason = str(row.get("deferral_reason") or "")
        n = int(row.get("count") or 0)
        if n <= 0:
            continue
        if rt == "github.pull_request_timeline_event":
            lines.append(
                f"{n:,} timeline events deferred — likely missing review/commit/workflow parents in raw ingest."
            )
        elif rt == "notion.database_row":
            lines.append(
                f"{n:,} Notion database rows awaiting productive pass allocation (parents usually present)."
            )
        elif rt == "github.deployment_status":
            lines.append(f"{n:,} deployment statuses in backlog — drain after deployments materialize.")
        else:
            lines.append(f"{n:,} {rt} deferred ({reason}).")

    cooled = parse_pass_cooldown_until(lease_detail)
    if cooled:
        lines.append(
            f"{len(cooled)} canonical pass(es) on local topology cooldown — other passes continue in parallel."
        )
    if phase_02_doc and phase_02_doc.get("status") == "waiting":
        lines.append("Phase 02 marked waiting — convergence will retry when parents or pass cooldowns clear.")
    if not lines:
        return f"{untreated:,} routable rows remain; convergence is still draining backlog."
    return " ".join(lines)
