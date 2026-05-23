"""Phase A step A4 — strict AA1/AA6 continuity proof panel gates."""

from __future__ import annotations

import inspect
import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import (
    DEFAULT_TENANT_ID,
    evaluate_aa1_phase_chain_v1,
    evaluate_aa6_forward_progress_v1,
)

P0_A4_STEP = "step_a4_aa_panel_strict"

STRICT_AA_PANEL_SCHEMA_VERSION_V1 = 2


def verify_a4_aa_panel_strict_wiring_v1() -> dict[str, Any]:
    """Static wiring: AA1 synthesis truth + AA6 without mat-only fallback."""
    errors: list[str] = []
    aa1_src = inspect.getsource(evaluate_aa1_phase_chain_v1)
    if "jobs_completed" not in aa1_src or "_lawful_empty_synthesis_v1" not in aa1_src:
        errors.append("aa1_missing_synthesis_truth_gate")
    if "p08_started" in aa1_src and "p08_completed" not in aa1_src:
        errors.append("aa1_still_uses_started_only_bootstrap")
    aa6_src = inspect.getsource(evaluate_aa6_forward_progress_v1)
    if "materializations_in_window" in aa6_src and "mats_24h > 0" in aa6_src.replace(" ", ""):
        if "passed = delta_succeeded > 0 or mats_24h > 0" in aa6_src.replace("\n", " "):
            errors.append("aa6_mat_only_fallback_still_present")
    if "untreated_decreased" not in aa6_src and "progress_made_in_window" not in aa6_src:
        errors.append("aa6_missing_drainable_motion_signals")
    return {"wiring_ok": not errors, "errors": errors}


def evaluate_p0_a4_aa_panel_strict_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    panel: dict[str, Any],
    panel_text: str,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step A4: strict AA1/AA6 gates wired; panel records gate evidence."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    wiring = verify_a4_aa_panel_strict_wiring_v1()
    gates = dict(panel.get("gates") or {})
    aa1 = dict(gates.get("AA1") or {})
    aa6 = dict(gates.get("AA6") or {})
    aa1_ev = dict(aa1.get("evidence") or {})
    aa6_ev = dict(aa6.get("evidence") or {})

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "panel_strict_schema": int(panel.get("strict_aa_panel_schema_version") or 0)
        >= STRICT_AA_PANEL_SCHEMA_VERSION_V1,
        "aa1_gate_present": "AA1" in gates,
        "aa6_gate_present": "AA6" in gates,
        "aa1_has_synthesis_evidence": "phase_08" in aa1_ev,
        "aa6_mat_only_pass_documented": "mat_only_pass" in aa6_ev,
        "aa6_forward_progress_signals_documented": isinstance(
            aa6_ev.get("forward_progress_signals"), list
        ),
        "panel_prints_aa1": "AA1" in panel_text.upper(),
        "panel_prints_aa6": "AA6" in panel_text.upper(),
    }
    checks_advisory = {
        "aa1_verdict": aa1.get("verdict"),
        "aa6_verdict": aa6.get("verdict"),
        "aa1_jobs_completed": aa1_ev.get("jobs_completed"),
        "aa1_lawful_empty": aa1_ev.get("lawful_empty"),
        "aa6_delta_succeeded": aa6_ev.get("convergence_delta_succeeded"),
        "aa6_untreated_decreased": aa6_ev.get("untreated_decreased"),
        "m3_autonomously_alive": bool((panel.get("summary") or {}).get("m3_autonomously_alive")),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    step_a4_pass = all(checks.values())
    return {
        "step": P0_A4_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "panel_summary": panel.get("summary"),
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_a4_pass": step_a4_pass,
        "verification": {
            "step_a4_pass": step_a4_pass,
            "cleared_for_a5": step_a4_pass,
        },
    }
