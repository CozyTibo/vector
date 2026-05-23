"""P1-G / Phase 2.2 — AA1–AA7 continuity proof panel (single-command operator surface)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, Final, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.candidate_selection import (
    list_untreated_routable_count_estimate,
)
from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform
from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.execution.tenant_constants import LEASE_STATUS_STALLED
from vector.domains.cortex.operational_runtime.graph_density import compute_graph_density_metrics_v1
from vector.domains.cortex.operational_runtime.graph_orphan_continuity import (
    ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1,
    ORPHAN_CLASS_IDENTITY_UNRESOLVED_V1,
    classify_tenant_graph_orphans_v1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    evaluate_traversal_propagation_v1,
)
from vector.domains.cortex.retrieval.retrieval_component_materialization import (
    snapshot_retrieval_aa4_footprint_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
    PHASE_STATUS_COMPLETED,
    PIPELINE_TRIGGER_POST_INGESTION,
)
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_COMPLETED_EMPTY,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_recovery import (
    get_latest_pipeline_run_for_tenant_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePipelineRun
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePhaseRun
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)

P2_2_STEP = "2.2_continuity_proof_panel"
DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")

STRICT_AA_PANEL_SCHEMA_VERSION_V1 = 2

AA_GATE_IDS_V1: Final[tuple[str, ...]] = (
    "AA1",
    "AA2",
    "AA3",
    "AA4",
    "AA5",
    "AA6",
    "AA7",
)

WEDGE_SCRIPT_PATTERNS_V1: Final[tuple[str, ...]] = (
    "unlock_step09",
    "unlock_step10",
    "unlock_step12",
    "execution/restart",
    "graph-density-promotion/run",
)

GateVerdict = Literal["PASS", "FAIL", "ADVISORY"]


def _gate(
    gate_id: str,
    *,
    verdict: GateVerdict,
    criterion: str,
    evidence: dict[str, Any],
    detail: str,
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "verdict": verdict,
        "pass": verdict == "PASS",
        "criterion": criterion,
        "detail": detail,
        "evidence": evidence,
    }


def _resolve_pipeline_run_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None,
) -> CortexSubstratePipelineRun | None:
    if pipeline_run_id is not None:
        return session.get(CortexSubstratePipelineRun, pipeline_run_id)
    run = get_latest_pipeline_run_for_tenant_v1(session, tenant_id=tenant_id)
    if run is not None:
        return run
    return session.scalar(
        select(CortexSubstratePipelineRun)
        .where(
            CortexSubstratePipelineRun.tenant_id == tenant_id,
            CortexSubstratePipelineRun.trigger_kind == PIPELINE_TRIGGER_POST_INGESTION,
        )
        .order_by(CortexSubstratePipelineRun.created_at.desc())
        .limit(1)
    )


def _phase08_output_evidence_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
) -> dict[str, Any]:
    row = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_08_SYNTHESIS)
    out = dict(row.output_json or {}) if row is not None else {}
    receipt = out.get("substrate_phase_receipt") or {}
    outcome = str(out.get("outcome") or "")
    if isinstance(receipt, Mapping):
        outcome = outcome or str(receipt.get("outcome") or "")
    return {
        "phase_08_status": row.status if row else None,
        "phase_08_outcome": outcome,
        "jobs_completed": int(out.get("jobs_completed") or 0),
        "jobs_failed": int(out.get("jobs_failed") or 0),
        "scope_empty": bool(out.get("scope_empty")),
        "scopes_scheduled": int(out.get("scopes_scheduled") or 0),
        "artifacts_published": int(out.get("artifacts_published") or 0),
        "empty_scope_reason": str(out.get("empty_scope_reason") or out.get("error_code") or ""),
        "per_island_mode": bool(out.get("per_island_mode")),
    }


def _lawful_empty_synthesis_v1(out: Mapping[str, Any]) -> bool:
    """Lawful empty: documented scope_empty / COMPLETED_EMPTY — not fake-green completion."""
    if not bool(out.get("scope_empty")):
        return False
    if int(out.get("jobs_completed") or 0) > 0:
        return False
    outcome = str(out.get("phase_08_outcome") or out.get("outcome") or "")
    if outcome == PHASE_OUTCOME_COMPLETED_EMPTY:
        return True
    reason = str(out.get("empty_scope_reason") or "").strip()
    return bool(reason)


def evaluate_aa1_phase_chain_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None,
) -> dict[str, Any]:
    """AA1 — phase chain 05→06→07→08 completed; synthesis jobs_completed>0 or lawful empty."""
    run = _resolve_pipeline_run_v1(
        session, tenant_id=tenant_id, pipeline_run_id=pipeline_run_id
    )
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    phases: dict[str, Any] = {}
    phase08: dict[str, Any] = {}
    if run is not None:
        for pid in (PHASE_05_TRAVERSAL, PHASE_06_TCRE, PHASE_07_RETRIEVAL, PHASE_08_SYNTHESIS):
            row = get_phase_run_v1(session, pipeline_run_id=run.id, phase_id=pid)
            phases[pid] = {
                "status": row.status if row else None,
                "started_at": row.started_at.isoformat() if row and row.started_at else None,
                "completed_at": row.completed_at.isoformat() if row and row.completed_at else None,
            }
        phase08 = _phase08_output_evidence_v1(session, pipeline_run_id=run.id)
    p05_ok = phases.get(PHASE_05_TRAVERSAL, {}).get("status") == PHASE_STATUS_COMPLETED
    p06_ok = phases.get(PHASE_06_TCRE, {}).get("status") == PHASE_STATUS_COMPLETED
    p07_ok = phases.get(PHASE_07_RETRIEVAL, {}).get("status") == PHASE_STATUS_COMPLETED
    p08_completed = phase08.get("phase_08_status") == PHASE_STATUS_COMPLETED
    jobs_completed = int(phase08.get("jobs_completed") or 0)
    lawful_empty = _lawful_empty_synthesis_v1(phase08)
    synthesis_ok = jobs_completed > 0 or lawful_empty
    chain_advanced = p05_ok and p06_ok and p07_ok and p08_completed and synthesis_ok
    stall_loop = False
    if lease is not None:
        stall_loop = (
            lease.status == LEASE_STATUS_STALLED
            and int(lease.attempt_count or 0) >= 3
            and bool(lease.last_error)
        )
    passed = chain_advanced and not stall_loop
    detail = "chain_and_synthesis_ok"
    if not p08_completed:
        detail = "phase_08_not_completed"
    elif not synthesis_ok:
        detail = "phase_08_empty_without_lawful_documentation"
    elif not (p05_ok and p06_ok and p07_ok):
        detail = "phase_chain_incomplete"
    return _gate(
        "AA1",
        verdict="PASS" if passed else "FAIL",
        criterion=(
            "Phase chain 05→06→07→08 completed; phase_08 jobs_completed>0 "
            "or lawful documented empty"
        ),
        evidence={
            "pipeline_run_id": str(run.id) if run else None,
            "phases": phases,
            "phase_08": phase08,
            "jobs_completed": jobs_completed,
            "lawful_empty": lawful_empty,
            "lease_status": lease.status if lease else None,
            "attempt_count": int(lease.attempt_count or 0) if lease else 0,
            "last_error_prefix": (lease.last_error or "")[:120] if lease else None,
        },
        detail=detail,
    )


def evaluate_aa2_traversal_propagation_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """AA2 — propagation not blocked OR islands_eligible ≥ 1 (P3′)."""
    density = compute_graph_density_metrics_v1(session, tenant_id=tenant_id)
    dm = dict(density.get("metrics") or {})
    orphan_cls = classify_tenant_graph_orphans_v1(session, tenant_id=tenant_id, sample_limit=0)
    counts = dict(orphan_cls.get("counts_by_class") or {})
    prop = evaluate_traversal_propagation_v1(
        session,
        tenant_id=tenant_id,
        linked_entity_count=int(dm.get("linked_entity_count") or 0),
        entity_count=int(dm.get("entity_count") or 0),
        orphan_disconnected_count=int(counts.get(ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1, 0)),
        orphan_identity_unresolved_count=int(
            counts.get(ORPHAN_CLASS_IDENTITY_UNRESOLVED_V1, 0)
        ),
    )
    blocked = bool(prop.get("traversal_propagation_blocked"))
    islands = int(prop.get("islands_eligible_count") or 0)
    passed = (not blocked) or islands >= 1
    return _gate(
        "AA2",
        verdict="PASS" if passed else "FAIL",
        criterion="traversal_propagation_blocked=false OR islands_eligible≥1",
        evidence={
            "traversal_propagation_blocked": blocked,
            "islands_eligible_count": islands,
            "traversal_propagation_mode": prop.get("traversal_propagation_mode"),
        },
        detail="p3_prime_eligible" if passed else "propagation_blocked_no_islands",
    )


def evaluate_aa3_tcre_jobs_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None,
) -> dict[str, Any]:
    """AA3 — TCRE jobs exist and reach terminal completed state."""
    jobs = list(
        session.scalars(
            select(CortexTcreReconstructionJob).where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.job_kind == "reconstruct",
            )
        ).all()
    )
    if pipeline_run_id is not None:
        prid = str(pipeline_run_id)
        jobs = [
            j
            for j in jobs
            if str((j.scope_json or {}).get("substrate_pipeline_run_id") or "") == prid
        ]
    by_status: dict[str, int] = {}
    for job in jobs:
        st = str(job.status)
        by_status[st] = by_status.get(st, 0) + 1
    completed = int(by_status.get("completed", 0))
    passed = len(jobs) > 0 and completed > 0
    return _gate(
        "AA3",
        verdict="PASS" if passed else "FAIL",
        criterion="COUNT(tcre_jobs)>0 with completed terminal jobs",
        evidence={"jobs_total": len(jobs), "jobs_by_status": by_status},
        detail=f"completed={completed}" if passed else "no_completed_tcre",
    )


def evaluate_aa4_retrieval_spread_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """AA4 — retrieval entries across ≥2 created_at hours (FG-6: not single-batch only)."""
    aa4 = snapshot_retrieval_aa4_footprint_v1(session, tenant_id=tenant_id)
    hours = int(aa4.get("distinct_created_hours") or 0)
    total = int(aa4.get("total_entries") or 0)
    passed = hours >= 2 and total > 0
    advisory_single_hour = hours == 1 and total > 0
    verdict: GateVerdict = "PASS" if passed else ("ADVISORY" if advisory_single_hour else "FAIL")
    return _gate(
        "AA4",
        verdict=verdict,
        criterion="retrieval_entries spread across ≥2 UTC hours",
        evidence=aa4,
        detail="multi_hour_spread" if passed else ("single_hour_batch" if advisory_single_hour else "no_entries"),
    )


def evaluate_aa5_synthesis_started_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None,
) -> dict[str, Any]:
    """AA5 — phase 08 started_at present (FG-7: receipt required for autonomous synthesis)."""
    run = _resolve_pipeline_run_v1(
        session, tenant_id=tenant_id, pipeline_run_id=pipeline_run_id
    )
    started_at = None
    status = None
    if run is not None:
        row = get_phase_run_v1(session, pipeline_run_id=run.id, phase_id=PHASE_08_SYNTHESIS)
        if row is not None:
            started_at = row.started_at.isoformat() if row.started_at else None
            status = row.status
    passed = started_at is not None
    return _gate(
        "AA5",
        verdict="PASS" if passed else "FAIL",
        criterion="phase_08.started_at IS NOT NULL",
        evidence={
            "pipeline_run_id": str(run.id) if run else None,
            "phase_08_status": status,
            "phase_08_started_at": started_at,
        },
        detail="synthesis_phase_started" if passed else "phase_08_never_started",
    )


def evaluate_aa6_forward_progress_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    window_hours: int = 24,
) -> dict[str, Any]:
    """AA6 — convergence_delta_succeeded>0 OR canonical progress_made OR untreated_routable ↓."""
    now = datetime.now(UTC)
    since = now - timedelta(hours=max(1, int(window_hours)))
    bundle_id = resolve_default_bundle_id_for_stub_transform(session, tenant_id=tenant_id)
    phase02_rows = list(
        session.scalars(
            select(CortexSubstratePhaseRun)
            .where(
                CortexSubstratePhaseRun.tenant_id == tenant_id,
                CortexSubstratePhaseRun.phase_id == PHASE_02_CANONICAL,
                CortexSubstratePhaseRun.status == PHASE_STATUS_COMPLETED,
                CortexSubstratePhaseRun.completed_at >= since,
            )
            .order_by(CortexSubstratePhaseRun.completed_at.asc())
        ).all()
    )
    delta_succeeded = 0
    progress_made_in_window = False
    untreated_first: int | None = None
    untreated_last: int | None = None
    for row in phase02_rows:
        raw = dict(row.output_json or {})
        summary = raw.get("canonical_summary") or {}
        if not isinstance(summary, Mapping):
            continue
        slice_succeeded = int(summary.get("total_succeeded") or 0)
        if slice_succeeded > delta_succeeded:
            delta_succeeded = slice_succeeded
        if bool(summary.get("progress_made")):
            progress_made_in_window = True
        est = summary.get("untreated_routable_estimate")
        if est is not None:
            val = int(est)
            if untreated_first is None:
                untreated_first = val
            untreated_last = val
    untreated_now = 0
    if bundle_id:
        untreated_now = list_untreated_routable_count_estimate(
            session, tenant_id=tenant_id, bundle_id=bundle_id
        )
    if untreated_first is None:
        untreated_first = untreated_now
    if untreated_last is None:
        untreated_last = untreated_now
    untreated_decreased = untreated_last < untreated_first
    forward_signals: list[str] = []
    if delta_succeeded > 0:
        forward_signals.append("convergence_delta_succeeded")
    if progress_made_in_window:
        forward_signals.append("progress_made_in_window")
    if untreated_decreased:
        forward_signals.append("untreated_routable_decreased")
    passed = bool(forward_signals)
    mat_only_pass = delta_succeeded == 0 and not progress_made_in_window and not untreated_decreased
    return _gate(
        "AA6",
        verdict="PASS" if passed else "FAIL",
        criterion=(
            f"convergence_delta_succeeded>0 or progress_made or untreated_routable↓ in {window_hours}h "
            "(no mat-count-only pass)"
        ),
        evidence={
            "window_hours": window_hours,
            "convergence_delta_succeeded": delta_succeeded,
            "progress_made_in_window": progress_made_in_window,
            "untreated_routable_first_in_window": untreated_first,
            "untreated_routable_last_in_window": untreated_last,
            "untreated_routable_now": untreated_now,
            "untreated_decreased": untreated_decreased,
            "forward_progress_signals": forward_signals,
            "mat_only_pass": mat_only_pass,
            "canonical_phase02_slices_in_window": len(phase02_rows),
            "bundle_id": bundle_id,
        },
        detail="forward_progress_motion" if passed else "no_drainable_forward_progress",
    )


def evaluate_aa7_no_wedge_scripts_v1(
    *,
    ops_log_text: str | None,
    wedge_free_ack: bool = False,
) -> dict[str, Any]:
    """AA7 — no manual wedge scripts in evaluation window (ops log when provided)."""
    if ops_log_text:
        hits = [p for p in WEDGE_SCRIPT_PATTERNS_V1 if p in ops_log_text]
        passed = len(hits) == 0
        return _gate(
            "AA7",
            verdict="PASS" if passed else "FAIL",
            criterion="No unlock_step09/10/12 or manual execution/restart in ops log",
            evidence={"wedge_hits": hits, "patterns_checked": list(WEDGE_SCRIPT_PATTERNS_V1)},
            detail="ops_log_clean" if passed else "wedge_scripts_detected",
        )
    if wedge_free_ack:
        return _gate(
            "AA7",
            verdict="PASS",
            criterion="Operator wedge-free acknowledgment (no ops log supplied)",
            evidence={"wedge_free_ack": True},
            detail="acknowledged_wedge_free",
        )
    return _gate(
        "AA7",
        verdict="ADVISORY",
        criterion="No wedge scripts in window (requires --ops-log-path or --wedge-free-ack)",
        evidence={"ops_log_supplied": False, "wedge_free_ack": False},
        detail="supply_ops_log_or_ack_for_aa7_pass",
    )


def build_continuity_proof_panel_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    window_hours: int = 24,
    ops_log_text: str | None = None,
    wedge_free_ack: bool = False,
) -> dict[str, Any]:
    """Evaluate AA1–AA7 and return structured panel payload."""
    gates = [
        evaluate_aa1_phase_chain_v1(
            session, tenant_id=tenant_id, pipeline_run_id=pipeline_run_id
        ),
        evaluate_aa2_traversal_propagation_v1(session, tenant_id=tenant_id),
        evaluate_aa3_tcre_jobs_v1(
            session, tenant_id=tenant_id, pipeline_run_id=pipeline_run_id
        ),
        evaluate_aa4_retrieval_spread_v1(session, tenant_id=tenant_id),
        evaluate_aa5_synthesis_started_v1(
            session, tenant_id=tenant_id, pipeline_run_id=pipeline_run_id
        ),
        evaluate_aa6_forward_progress_v1(session, tenant_id=tenant_id, window_hours=window_hours),
        evaluate_aa7_no_wedge_scripts_v1(
            ops_log_text=ops_log_text, wedge_free_ack=wedge_free_ack
        ),
    ]
    pass_count = sum(1 for g in gates if g["verdict"] == "PASS")
    fail_count = sum(1 for g in gates if g["verdict"] == "FAIL")
    advisory_count = sum(1 for g in gates if g["verdict"] == "ADVISORY")
    m3_alive = fail_count == 0 and advisory_count == 0 and pass_count == len(AA_GATE_IDS_V1)
    run = _resolve_pipeline_run_v1(
        session, tenant_id=tenant_id, pipeline_run_id=pipeline_run_id
    )
    return {
        "surface_kind": "continuity_proof_panel",
        "step": P2_2_STEP,
        "strict_aa_panel_schema_version": STRICT_AA_PANEL_SCHEMA_VERSION_V1,
        "tenant_id": str(tenant_id),
        "pipeline_run_id": str(run.id) if run else None,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "window_hours": window_hours,
        "gates": {g["gate_id"]: g for g in gates},
        "gate_order": list(AA_GATE_IDS_V1),
        "summary": {
            "pass_count": pass_count,
            "fail_count": fail_count,
            "advisory_count": advisory_count,
            "total_gates": len(AA_GATE_IDS_V1),
            "m3_autonomously_alive": m3_alive,
            "metric_tier": "M3" if m3_alive else "below_M3",
        },
    }


def format_continuity_proof_panel_text_v1(panel: dict[str, Any]) -> str:
    """Human-readable AA1–AA7 panel for operator runbook."""
    lines = [
        "=== Cortex Continuity Proof Panel (AA1–AA7) ===",
        f"Tenant: {panel.get('tenant_id')}",
        f"Pipeline: {panel.get('pipeline_run_id') or '—'}",
        f"Evaluated: {panel.get('evaluated_at')}",
        f"Window: {panel.get('window_hours')}h (AA6/AA7 context)",
        "",
    ]
    gates = dict(panel.get("gates") or {})
    for gate_id in panel.get("gate_order") or AA_GATE_IDS_V1:
        g = gates.get(gate_id) or {}
        verdict = str(g.get("verdict") or "FAIL")
        lines.append(f"{gate_id}  [{verdict}] {g.get('criterion', '')}")
        lines.append(f"      {g.get('detail', '')}")
    summary = dict(panel.get("summary") or {})
    lines.extend(
        [
            "",
            (
                f"Summary: {summary.get('pass_count', 0)}/{summary.get('total_gates', 7)} PASS"
                f" | {summary.get('fail_count', 0)} FAIL"
                f" | {summary.get('advisory_count', 0)} ADVISORY"
            ),
            f"M3 autonomously alive: {'YES' if summary.get('m3_autonomously_alive') else 'NO'}",
            "=== end panel ===",
        ]
    )
    return "\n".join(lines)


def evaluate_p2_2_proof_panel_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    panel: dict[str, Any],
    panel_text: str,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step 2.2: continuity_proof_panel prints AA1–AA7."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    gates = dict(panel.get("gates") or {})
    gate_ids_in_panel = set(gates.keys())
    text_upper = panel_text.upper()
    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "panel_surface_kind": panel.get("surface_kind") == "continuity_proof_panel",
        "all_aa_gates_evaluated": gate_ids_in_panel >= set(AA_GATE_IDS_V1),
        "panel_prints_aa1": "AA1" in text_upper,
        "panel_prints_aa2": "AA2" in text_upper,
        "panel_prints_aa3": "AA3" in text_upper,
        "panel_prints_aa4": "AA4" in text_upper,
        "panel_prints_aa5": "AA5" in text_upper,
        "panel_prints_aa6": "AA6" in text_upper,
        "panel_prints_aa7": "AA7" in text_upper,
        "panel_summary_line_present": "Summary:" in panel_text,
    }
    checks_advisory = {
        "m3_autonomously_alive": bool((panel.get("summary") or {}).get("m3_autonomously_alive")),
        "aa_gates_pass_count": int((panel.get("summary") or {}).get("pass_count") or 0),
    }
    step_22_pass = all(checks.values())
    return {
        "step": P2_2_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "panel_summary": panel.get("summary"),
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p2_2_pass": step_22_pass,
        "verification": {
            "step_22_pass": step_22_pass,
            "cleared_for_step_23": step_22_pass,
        },
    }
