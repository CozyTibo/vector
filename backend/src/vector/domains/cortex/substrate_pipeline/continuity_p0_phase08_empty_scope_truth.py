"""Phase C step C1 — phase 08 empty scope truth proof."""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.phase08_empty_scope_truth_gate import (
    PHASE_C1_EMPTY_SCOPE_GATE_SCHEMA_VERSION,
    P0_C1_STEP,
    evaluate_phase08_empty_scope_truth_v1,
    is_phase08_empty_scope_truth_gate_enabled_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_08_SYNTHESIS
from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import (
    evaluate_aa1_phase_chain_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    PHASE_OUTCOME_COMPLETED_EMPTY,
    PHASE_OUTCOME_FAILED,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
    CortexSubstratePhaseRun,
    CortexSubstratePipelineRun,
)

DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def verify_c1_phase08_empty_scope_truth_wiring_v1() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.synthesis import synthesis_pipeline as sp_mod
    from vector.domains.cortex.substrate_pipeline import continuity_proof_panel as panel_mod

    p08_src = inspect.getsource(sp_mod.run_substrate_phase_08_synthesis_v1)
    for needle in (
        "attach_phase08_empty_scope_truth_gate_v1",
        "should_fail_phase08_for_empty_scope_violation_v1",
        "fail_phase_with_receipt_v1",
    ):
        if needle not in p08_src:
            errors.append(f"phase_08_runner_missing_{needle}")

    panel_src = inspect.getsource(panel_mod._lawful_empty_synthesis_v1)
    if "empty_scope_violation" not in panel_src:
        errors.append("aa1_lawful_empty_missing_violation_check")
    if "retrieval_entries_in_epoch" not in panel_src:
        errors.append("aa1_lawful_empty_missing_entries_check")

    return {
        "wiring_ok": not errors,
        "errors": errors,
        "phase_c1_schema_version": PHASE_C1_EMPTY_SCOPE_GATE_SCHEMA_VERSION,
        "gate_enabled": is_phase08_empty_scope_truth_gate_enabled_v1(),
    }


def snapshot_phase08_empty_scope_truth_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    lookback_hours: int = 168,
) -> dict[str, Any]:
    from vector.domains.cortex.synthesis.phase08_empty_scope_truth_gate import (
        count_retrieval_entries_in_published_epoch_v1,
    )

    cutoff = datetime.now(UTC) - timedelta(hours=lookback_hours)
    entry_stats = count_retrieval_entries_in_published_epoch_v1(session, tenant_id=tenant_id)
    runs = list(
        session.scalars(
            select(CortexSubstratePipelineRun)
            .where(CortexSubstratePipelineRun.tenant_id == tenant_id)
            .order_by(CortexSubstratePipelineRun.created_at.desc())
            .limit(24)
        ).all()
    )
    from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1

    slice_summaries: list[dict[str, Any]] = []
    empty_scope_lies = 0
    legacy_empty_scope_lies = 0
    post_gate_empty_scope_lies = 0
    explicit_fails = 0
    jobs_completed_slices = 0
    truthful_slices = 0
    for run in runs:
        if run.created_at is not None and run.created_at < cutoff:
            continue
        p08 = get_phase_run_v1(session, pipeline_run_id=run.id, phase_id=PHASE_08_SYNTHESIS)
        if p08 is None:
            continue
        raw = dict(p08.output_json or {})
        receipt = dict(raw.get("substrate_phase_receipt") or {})
        outcome = str(receipt.get("outcome") or raw.get("outcome") or "")
        jobs = int(raw.get("jobs_completed") or 0)
        scopes = int(raw.get("scopes_scheduled") or 0)
        entries = int(raw.get("retrieval_entries_in_epoch") or entry_stats["retrieval_entries_in_epoch"])
        gate_eval = evaluate_phase08_empty_scope_truth_v1(
            raw,
            retrieval_entries_in_epoch=entries,
        )
        has_gate = "phase08_empty_scope_gate" in raw
        is_lie = (
            outcome == PHASE_OUTCOME_COMPLETED_EMPTY
            and entries > 0
            and scopes == 0
            and jobs == 0
        )
        if is_lie:
            empty_scope_lies += 1
            if has_gate:
                post_gate_empty_scope_lies += 1
            else:
                legacy_empty_scope_lies += 1
        if outcome == PHASE_OUTCOME_FAILED and bool(raw.get("empty_scope_violation")):
            explicit_fails += 1
        if jobs > 0:
            jobs_completed_slices += 1
        truthful = (
            jobs > 0
            or entries == 0
            or (outcome == PHASE_OUTCOME_FAILED and bool(raw.get("empty_scope_violation")))
            or (outcome == PHASE_OUTCOME_FAILED and scopes > 0)
        )
        if truthful:
            truthful_slices += 1
        aa1 = evaluate_aa1_phase_chain_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=run.id,
        )
        slice_summaries.append(
            {
                "pipeline_run_id": str(run.id),
                "completed_at": p08.completed_at.isoformat() if p08.completed_at else None,
                "phase_08_status": p08.status,
                "receipt_outcome": outcome,
                "jobs_completed": jobs,
                "scopes_scheduled": scopes,
                "retrieval_entries_in_epoch": entries,
                "empty_scope_lie": is_lie,
                "legacy_empty_scope_lie": is_lie and not has_gate,
                "has_phase08_empty_scope_gate": has_gate,
                "phase08_empty_scope_gate_ok": gate_eval["ok"],
                "aa1_verdict": aa1.get("verdict"),
            }
        )

    return {
        "tenant_id": str(tenant_id),
        "lookback_hours": lookback_hours,
        "retrieval_entries_in_published_epoch": entry_stats["retrieval_entries_in_epoch"],
        "published_index_epoch": entry_stats["published_index_epoch"],
        "phase_08_slices": slice_summaries,
        "empty_scope_completed_empty_lies": empty_scope_lies,
        "legacy_empty_scope_lies": legacy_empty_scope_lies,
        "post_gate_empty_scope_lies": post_gate_empty_scope_lies,
        "explicit_empty_scope_failures": explicit_fails,
        "slices_with_jobs_completed": jobs_completed_slices,
        "truthful_phase08_slices": truthful_slices,
        "wiring": verify_c1_phase08_empty_scope_truth_wiring_v1(),
        "phase_c1_schema_version": PHASE_C1_EMPTY_SCOPE_GATE_SCHEMA_VERSION,
    }


def evaluate_p0_c1_phase08_empty_scope_truth_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    wiring = dict(snapshot.get("wiring") or {})
    lies = int(snapshot.get("empty_scope_completed_empty_lies") or 0)
    legacy_lies = int(snapshot.get("legacy_empty_scope_lies") or 0)
    post_gate_lies = int(snapshot.get("post_gate_empty_scope_lies") or 0)
    jobs_slices = int(snapshot.get("slices_with_jobs_completed") or 0)
    truthful_slices = int(snapshot.get("truthful_phase08_slices") or 0)
    entries = int(snapshot.get("retrieval_entries_in_published_epoch") or 0)
    drive = dict(snapshot.get("phase08_drive") or {})

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "phase08_empty_scope_gate_enabled": bool(wiring.get("gate_enabled")),
        "phase_c1_schema_version": int(snapshot.get("phase_c1_schema_version") or 0)
        >= PHASE_C1_EMPTY_SCOPE_GATE_SCHEMA_VERSION,
        "no_post_gate_completed_empty_lies": post_gate_lies == 0,
        "no_legacy_empty_scope_lies": legacy_lies == 0,
        "recent_truthful_phase08_slice": truthful_slices >= 1 or entries == 0,
        "phase08_drive_ok_when_run": (not drive) or bool(drive.get("ok")),
    }
    checks_advisory = {
        "empty_scope_completed_empty_lies": lies,
        "legacy_empty_scope_lies": legacy_lies,
        "post_gate_empty_scope_lies": post_gate_lies,
        "slices_with_jobs_completed": jobs_slices,
        "truthful_phase08_slices": truthful_slices,
        "retrieval_entries_in_published_epoch": entries,
        "phase08_drive": drive,
        "phase_08_slices": snapshot.get("phase_08_slices"),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    p0_c1_pass = all(checks.values())
    return {
        "step": P0_C1_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_c1_pass": p0_c1_pass,
        "verification": {
            "step_c1_pass": p0_c1_pass,
            "cleared_for_c2": p0_c1_pass,
            "c1_phase08_truth": post_gate_lies == 0 and legacy_lies == 0,
        },
    }


def _rerun_phase08_on_run_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
) -> dict[str, Any]:
    from vector.domains.cortex.synthesis.synthesis_pipeline import run_substrate_phase_08_synthesis_v1
    from vector.domains.cortex.substrate_pipeline.constants import PHASE_08_SYNTHESIS
    from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1

    try:
        out = run_substrate_phase_08_synthesis_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
        )
    except ValueError as exc:
        return {
            "ok": False,
            "pipeline_run_id": str(pipeline_run_id),
            "error": str(exc),
            "phase08_rerun": True,
        }
    p08 = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_08_SYNTHESIS)
    receipt = dict((p08.output_json or {}) if p08 else {})
    return {
        "ok": True,
        "phase08_rerun": True,
        "pipeline_run_id": str(pipeline_run_id),
        "jobs_completed": int(out.get("jobs_completed") or 0),
        "empty_scope_violation": bool(out.get("empty_scope_violation")),
        "phase_08_status": p08.status if p08 else None,
        "receipt_outcome": str(receipt.get("outcome") or ""),
        "has_phase08_empty_scope_gate": "phase08_empty_scope_gate" in receipt,
    }


def drive_phase08_truth_on_latest_run_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    prefer_pipeline_run_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Re-run phase 08 (applies C1 gate); prefer a legacy-lie run when provided."""
    from vector.domains.cortex.substrate_pipeline.constants import PHASE_07_RETRIEVAL, PHASE_STATUS_COMPLETED
    from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1

    if prefer_pipeline_run_id is not None:
        p07 = get_phase_run_v1(
            session, pipeline_run_id=prefer_pipeline_run_id, phase_id=PHASE_07_RETRIEVAL
        )
        if p07 is not None and p07.status == PHASE_STATUS_COMPLETED:
            return _rerun_phase08_on_run_v1(
                session, tenant_id=tenant_id, pipeline_run_id=prefer_pipeline_run_id
            )

    for run in _runs_ordered_v1(session, tenant_id):
        p07 = get_phase_run_v1(session, pipeline_run_id=run.id, phase_id=PHASE_07_RETRIEVAL)
        if p07 is None or p07.status != PHASE_STATUS_COMPLETED:
            continue
        return _rerun_phase08_on_run_v1(session, tenant_id=tenant_id, pipeline_run_id=run.id)
    return {"ok": False, "reason": "no_pipeline_with_completed_phase_07", "phase08_rerun": True}


def _runs_ordered_v1(session: Session, tenant_id: uuid.UUID) -> list[CortexSubstratePipelineRun]:
    return list(
        session.scalars(
            select(CortexSubstratePipelineRun)
            .where(CortexSubstratePipelineRun.tenant_id == tenant_id)
            .order_by(CortexSubstratePipelineRun.created_at.desc())
            .limit(12)
        ).all()
    )
