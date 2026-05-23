"""Phase B step B4 — phase 05 walks persisted when scheduling eligible."""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.constants import PHASE_05_TRAVERSAL
from vector.domains.cortex.substrate_pipeline.phase05_walks_persisted_gate import (
    P0_B4_STEP,
    PHASE_B4_WALKS_PERSISTED_SCHEMA_VERSION,
    summarize_phase05_walk_output_v1,
)
from vector.infrastructure.db.models.cortex_octs_durable_walk_record import CortexOctsDurableWalkRecord
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePhaseRun

DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def verify_b4_phase05_walks_persisted_wiring_v1() -> dict[str, Any]:
    """Static wiring: phase 05 gate + schedule pass enforcement."""
    errors: list[str] = []
    from vector.domains.cortex.operational_runtime import substrate_traversal_scheduling as sched_mod
    from vector.domains.cortex.substrate_pipeline import phase_runners as pr_mod
    from vector.domains.cortex.substrate_pipeline import phase05_walks_persisted_gate as gate_mod

    p05_src = inspect.getsource(pr_mod.run_phase_05_traversal_v1)
    for needle in (
        "evaluate_phase05_schedule_context_v1",
        "supplement_phase05_walks_when_eligible_v1",
        "resolve_phase05_traversal_outcome_v1",
        "scheduling_eligible",
    ):
        if needle not in p05_src:
            errors.append(f"phase_05_missing_{needle}")

    sched_src = inspect.getsource(sched_mod.schedule_octs_walks_for_tenant_v1)
    if "enforce_schedule_pass_walks_persisted_v1" not in sched_src:
        errors.append("schedule_octs_walks_missing_enforce_gate")

    if not hasattr(gate_mod, "enforce_schedule_pass_walks_persisted_v1"):
        errors.append("gate_module_missing_enforce_helper")

    return {
        "wiring_ok": not errors,
        "errors": errors,
        "phase_b4_schema_version": PHASE_B4_WALKS_PERSISTED_SCHEMA_VERSION,
    }


def snapshot_phase05_walks_persisted_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    lookback_hours: int = 168,
) -> dict[str, Any]:
    """Prod snapshot: recent phase 05 receipts and durable walk rows."""
    cutoff = datetime.now(UTC) - timedelta(hours=lookback_hours)
    runs = list(
        session.scalars(
            select(CortexSubstratePhaseRun)
            .where(
                CortexSubstratePhaseRun.tenant_id == tenant_id,
                CortexSubstratePhaseRun.phase_id == PHASE_05_TRAVERSAL,
            )
            .order_by(CortexSubstratePhaseRun.completed_at.desc().nullslast())
            .limit(24)
        ).all()
    )
    slice_summaries: list[dict[str, Any]] = []
    slices_with_walks = 0
    eligible_empty_lies = 0
    for run in runs:
        if run.completed_at is not None and run.completed_at < cutoff:
            continue
        raw = dict(run.output_json or {})
        receipt = dict(raw.get("substrate_phase_receipt") or {})
        summary = summarize_phase05_walk_output_v1(raw)
        eligible = bool(raw.get("scheduling_eligible"))
        outcome = str(receipt.get("outcome") or run.status or "")
        has_walks = summary["walks_persisted"] > 0 or summary["walks_available"] > 0
        if has_walks:
            slices_with_walks += 1
        if eligible and outcome == "COMPLETED_EMPTY" and not has_walks:
            eligible_empty_lies += 1
        slice_summaries.append(
            {
                "pipeline_run_id": str(run.pipeline_run_id),
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "status": run.status,
                "receipt_outcome": outcome,
                "scheduling_eligible": eligible,
                "walks_persisted": summary["walks_persisted"],
                "walks_available": summary["walks_available"],
                "phase05_walks_gate_ok": (raw.get("phase05_walks_gate") or {}).get("ok"),
            }
        )

    walk_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOctsDurableWalkRecord)
            .where(CortexOctsDurableWalkRecord.tenant_id == tenant_id)
        )
        or 0
    )

    latest = slice_summaries[0] if slice_summaries else None
    return {
        "tenant_id": str(tenant_id),
        "lookback_hours": lookback_hours,
        "phase05_slices_sampled": len(slice_summaries),
        "slices_with_walks_persisted_or_available": slices_with_walks,
        "eligible_completed_empty_violations": eligible_empty_lies,
        "durable_walk_row_count": walk_count,
        "has_durable_walks": walk_count > 0,
        "latest_phase_05": latest,
        "slice_summaries": slice_summaries[:8],
        "wiring": verify_b4_phase05_walks_persisted_wiring_v1(),
        "phase_b4_schema_version": PHASE_B4_WALKS_PERSISTED_SCHEMA_VERSION,
    }


def evaluate_p0_b4_phase05_walks_persisted_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    schedule_drive: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step B4: phase 05 receipts show walks when scheduling eligible (B-G4)."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    wiring = dict(snapshot.get("wiring") or {})
    latest = dict(snapshot.get("latest_phase_05") or {})
    latest_walks = 0
    if latest:
        latest_walks = max(
            int(latest.get("walks_persisted") or 0),
            int(latest.get("walks_available") or 0),
        )

    drive_mat = dict((schedule_drive or {}).get("pass") or {}).get("materialization") or {}
    drive_persisted = int(drive_mat.get("walks_persisted") or 0) if schedule_drive else 0

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "phase_b4_schema_version": int(snapshot.get("phase_b4_schema_version") or 0)
        >= PHASE_B4_WALKS_PERSISTED_SCHEMA_VERSION,
        "tenant_has_durable_walks": bool(snapshot.get("has_durable_walks")),
        "recent_slice_with_walks": int(snapshot.get("slices_with_walks_persisted_or_available") or 0)
        > 0
        or drive_persisted > 0,
        "no_eligible_completed_empty_lies": int(
            snapshot.get("eligible_completed_empty_violations") or 0
        )
        == 0,
        "latest_slice_walks_when_present": latest_walks > 0
        if latest
        else bool(snapshot.get("has_durable_walks")),
    }
    checks_advisory = {
        "latest_phase_05": latest,
        "slice_summaries": snapshot.get("slice_summaries"),
        "schedule_drive": schedule_drive,
        "durable_walk_row_count": snapshot.get("durable_walk_row_count"),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    p0_b4_pass = all(checks.values())
    return {
        "step": P0_B4_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "schedule_drive": schedule_drive,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_b4_pass": p0_b4_pass,
        "verification": {
            "step_b4_pass": p0_b4_pass,
            "cleared_for_b5": p0_b4_pass,
            "b_g4_phase05_walks": checks.get("recent_slice_with_walks"),
        },
    }
