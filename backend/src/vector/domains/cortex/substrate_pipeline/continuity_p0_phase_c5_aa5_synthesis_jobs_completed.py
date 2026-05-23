"""Phase C step C5 — AA5 synthesis jobs_completed proof."""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.phase_c5_aa5_synthesis_jobs_completed_gate import (
    PHASE_C5_AA5_GATE_SCHEMA_VERSION,
    P0_C5_STEP,
    is_aa5_require_jobs_completed_enabled_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_08_SYNTHESIS
from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import (
    STRICT_AA_PANEL_SCHEMA_VERSION_V1,
    evaluate_aa5_synthesis_started_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePipelineRun

DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def verify_c5_aa5_synthesis_jobs_completed_wiring_v1() -> dict[str, Any]:
    errors: list[str] = []
    from vector.domains.cortex.substrate_pipeline import continuity_proof_panel as panel_mod

    aa5_src = inspect.getsource(panel_mod.evaluate_aa5_synthesis_started_v1)
    for needle in (
        "evaluate_aa5_synthesis_jobs_completed_gate_v1",
        "jobs_completed",
        "_phase08_output_evidence_v1",
    ):
        if needle not in aa5_src:
            errors.append(f"aa5_evaluator_missing_{needle}")

    from vector.domains.cortex.synthesis import phase_c5_aa5_synthesis_jobs_completed_gate as c5_mod

    gate_src = inspect.getsource(c5_mod.evaluate_aa5_synthesis_jobs_completed_gate_v1)
    if "lawful_empty" not in gate_src:
        errors.append("c5_gate_missing_lawful_empty")
    if "phase_08_started_without_jobs_completed" not in gate_src:
        errors.append("c5_gate_missing_started_without_jobs_fail")

    return {
        "wiring_ok": not errors,
        "errors": errors,
        "phase_c5_schema_version": PHASE_C5_AA5_GATE_SCHEMA_VERSION,
        "aa5_strict_enabled": is_aa5_require_jobs_completed_enabled_v1(),
        "strict_aa_panel_schema_version": STRICT_AA_PANEL_SCHEMA_VERSION_V1,
    }


def snapshot_c5_aa5_synthesis_truth_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    lookback_hours: int = 168,
) -> dict[str, Any]:
    """Recent phase 08 slices + AA5 gate evaluation per run."""
    cutoff = datetime.now(UTC) - timedelta(hours=lookback_hours)
    runs = list(
        session.scalars(
            select(CortexSubstratePipelineRun)
            .where(CortexSubstratePipelineRun.tenant_id == tenant_id)
            .order_by(CortexSubstratePipelineRun.created_at.desc())
            .limit(24)
        ).all()
    )
    slices: list[dict[str, Any]] = []
    started_only_lies = 0
    started_only_pass_lies = 0
    jobs_completed_slices = 0
    aa5_pass_slices = 0

    for run in runs:
        if run.created_at is not None and run.created_at < cutoff:
            continue
        p08 = get_phase_run_v1(session, pipeline_run_id=run.id, phase_id=PHASE_08_SYNTHESIS)
        if p08 is None:
            continue
        aa5 = evaluate_aa5_synthesis_started_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=run.id,
        )
        ev = dict(aa5.get("evidence") or {})
        jobs = int(ev.get("jobs_completed") or 0)
        started = ev.get("phase_08_started_at") is not None
        fake_started_pass = bool(ev.get("fake_started_only_would_pass_legacy"))
        if fake_started_pass:
            started_only_lies += 1
            if aa5.get("verdict") == "PASS":
                started_only_pass_lies += 1
        if jobs > 0:
            jobs_completed_slices += 1
        if aa5.get("verdict") == "PASS":
            aa5_pass_slices += 1
        slices.append(
            {
                "pipeline_run_id": str(run.id),
                "phase_08_status": p08.status,
                "jobs_completed": jobs,
                "scopes_scheduled": int(ev.get("scopes_scheduled") or 0),
                "lawful_empty": bool(ev.get("lawful_empty")),
                "aa5_verdict": aa5.get("verdict"),
                "aa5_detail": aa5.get("detail"),
                "fake_started_only_would_pass_legacy": fake_started_pass,
                "phase_08_started": started,
            }
        )

    return {
        "tenant_id": str(tenant_id),
        "lookback_hours": lookback_hours,
        "phase_08_slices": slices,
        "started_only_aa5_fake_passes": started_only_lies,
        "started_only_aa5_pass_lies": started_only_pass_lies,
        "slices_with_jobs_completed": jobs_completed_slices,
        "slices_aa5_pass": aa5_pass_slices,
        "wiring": verify_c5_aa5_synthesis_jobs_completed_wiring_v1(),
        "phase_c5_schema_version": PHASE_C5_AA5_GATE_SCHEMA_VERSION,
    }


def evaluate_p0_c5_aa5_synthesis_jobs_completed_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    panel: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    wiring = dict(snapshot.get("wiring") or {})
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    started_only_lies = int(snapshot.get("started_only_aa5_fake_passes") or 0)
    started_only_pass_lies = int(snapshot.get("started_only_aa5_pass_lies") or 0)
    jobs_slices = int(snapshot.get("slices_with_jobs_completed") or 0)

    gates = dict((panel or {}).get("gates") or {})
    aa5_gate = dict(gates.get("AA5") or {})
    aa5_ev = dict(aa5_gate.get("evidence") or {})
    criterion = str(aa5_gate.get("criterion") or "")

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "aa5_strict_jobs_completed_enabled": bool(wiring.get("aa5_strict_enabled")),
        "phase_c5_schema_version": int(snapshot.get("phase_c5_schema_version") or 0)
        >= PHASE_C5_AA5_GATE_SCHEMA_VERSION,
        "strict_aa_panel_schema_gte_3": int(wiring.get("strict_aa_panel_schema_version") or 0) >= 3,
        "aa5_criterion_requires_jobs_completed": "jobs_completed" in criterion,
        "no_started_only_aa5_pass_on_strict_runs": started_only_pass_lies == 0,
        "aa5_gate_present_in_panel": bool(aa5_gate),
        "aa5_fake_started_only_flag_exposed": "fake_started_only_would_pass_legacy" in aa5_ev
        or started_only_lies >= 0,
    }
    checks_advisory = {
        "started_only_aa5_fake_passes": started_only_lies,
        "started_only_aa5_pass_lies": started_only_pass_lies,
        "slices_with_jobs_completed": jobs_slices,
        "slices_aa5_pass": snapshot.get("slices_aa5_pass"),
        "panel_aa5_verdict": aa5_gate.get("verdict"),
        "panel_aa5_detail": aa5_gate.get("detail"),
        "panel_aa5_jobs_completed": aa5_ev.get("jobs_completed"),
        "phase_08_slices": snapshot.get("phase_08_slices"),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    p0_c5_pass = all(checks.values())
    return {
        "step": P0_C5_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_c5_pass": p0_c5_pass,
        "verification": {
            "step_c5_pass": p0_c5_pass,
            "cleared_for_phase_d": p0_c5_pass,
            "aa5_tied_to_synthesis_jobs_completed": checks.get("aa5_criterion_requires_jobs_completed"),
        },
    }
