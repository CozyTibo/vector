"""Phase C step C4 — restart 48h AA M3 hold clock after Phase A+B+C strict gates."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from vector.domains.cortex.substrate_pipeline.continuity_p2_aa_clock import (
    CONTINUITY_AA_CLOCK_SCHEMA_VERSION_V1,
    CONTINUITY_AA_HOLD_HOURS_V1,
    P2_4_STEP,
    aa_clock_hold_elapsed_hours_v1,
    build_aa_clock_t0_baseline_v1,
    evaluate_p2_4_aa_clock_proof_v1,
    m3_panel_all_pass_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import (
    AA_GATE_IDS_V1,
    STRICT_AA_PANEL_SCHEMA_VERSION_V1,
)

P0_C4_STEP: Final[str] = "step_c4_aa48_clock_restart"
PHASE_C4_CLOCK_RESTART_SCHEMA_VERSION: Final[int] = 2
C4_CLOCK_RESTART_GENERATION_V1: Final[int] = 2

# Phase A+B+C steps that must be prod-signed in continuity_p0 baseline before C4 restart.
C4_ABC_PREREQUISITE_STEP_KEYS_V1: Final[tuple[str, ...]] = (
    "step_a1_synthesis_job_reconcile",
    "step_a2_ecs_deploy_align",
    "step_a3_tcre_queued_drain",
    "step_a4_aa_panel_strict",
    "step_a5_trace_only_ban",
    "step_a6_synthesis_terminal_transitions",
    "step_b1_retrieval_publish_contract",
    "step_b2_retrieval_epoch_scope_alignment",
    "step_b3_retrieval_registry_epoch",
    "step_b4_phase05_walks_persisted",
    "step_b5_graph_hash_autonomous_chain",
    "step_b6_post_ingestion_fresh_pipeline_run",
    "step_c1_phase08_empty_scope_truth",
    "step_c2_synthesis_per_island_scope_caps",
    "step_c3_continuity_audit_snapshot",
)


def _step_record_passed_v1(record: dict[str, Any]) -> bool:
    for key, value in record.items():
        if key.endswith("_pass") and isinstance(value, bool):
            return value
    return False


def evaluate_abc_prerequisites_from_baseline_v1(
    baseline: dict[str, Any],
) -> dict[str, Any]:
    """Require Phase A+B+C prod sign-off steps before restarting the 48h clock."""
    missing: list[str] = []
    failed: list[str] = []
    trace_only_violations: list[str] = []
    checked: dict[str, Any] = {}

    for step_key in C4_ABC_PREREQUISITE_STEP_KEYS_V1:
        block = baseline.get(step_key)
        if not isinstance(block, dict):
            missing.append(step_key)
            continue
        passed = _step_record_passed_v1(block)
        checked[step_key] = {
            "present": True,
            "passed": passed,
            "signoff_grade": block.get("signoff_grade"),
            "trace_only": block.get("trace_only"),
        }
        if bool(block.get("trace_only")):
            trace_only_violations.append(step_key)
        if not passed:
            failed.append(step_key)

    all_pass = not missing and not failed and not trace_only_violations
    return {
        "all_prerequisites_pass": all_pass,
        "missing_steps": missing,
        "failed_steps": failed,
        "trace_only_steps": trace_only_violations,
        "prerequisite_count": len(C4_ABC_PREREQUISITE_STEP_KEYS_V1),
        "checked": checked,
    }


def mark_prior_t0_superseded_v1(
    prior_t0: dict[str, Any],
    *,
    superseded_at: datetime,
    superseded_by_step: str,
    new_clock_started_at: datetime,
) -> dict[str, Any]:
    """Return prior T0 document annotated as superseded (C4 honest restart)."""
    out = dict(prior_t0)
    out["superseded"] = True
    out["superseded_at"] = superseded_at.isoformat()
    out["superseded_by_step"] = superseded_by_step
    out["superseded_reason"] = "phase_c4_restart_after_abc_strict_gates"
    out["superseded_by_clock_started_at"] = new_clock_started_at.isoformat()
    return out


def build_aa_clock_c4_restart_t0_v1(
    *,
    panel: dict[str, Any],
    closure_git_sha: str,
    tenant_id: uuid.UUID,
    abc_prerequisites: dict[str, Any],
    prior_t0: dict[str, Any] | None = None,
    wedge_free_ack: bool = False,
    clock_started_at: datetime | None = None,
) -> dict[str, Any]:
    """Build new T0 baseline after A+B+C; supersedes false-green pre-ABC clock."""
    started = clock_started_at or datetime.now(UTC)
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)

    t0 = build_aa_clock_t0_baseline_v1(
        panel=panel,
        closure_git_sha=closure_git_sha,
        tenant_id=tenant_id,
        wedge_free_ack=wedge_free_ack,
        clock_started_at=started,
    )
    all_pass = m3_panel_all_pass_v1(panel)
    strict_schema = int(panel.get("strict_aa_panel_schema_version") or 0) >= (
        STRICT_AA_PANEL_SCHEMA_VERSION_V1
    )

    t0.update(
        {
            "phase_c4_restart_schema_version": PHASE_C4_CLOCK_RESTART_SCHEMA_VERSION,
            "clock_restart_generation": C4_CLOCK_RESTART_GENERATION_V1,
            "clock_restart_step": P0_C4_STEP,
            "prior_t0_superseded": prior_t0 is not None,
            "prior_t0_clock_started_at": (prior_t0 or {}).get("clock_started_at"),
            "prior_t0_m3_at_capture": (prior_t0 or {}).get("m3_autonomously_alive_at_t0"),
            "prior_t0_closure_git_sha": (prior_t0 or {}).get("closure_git_sha"),
            "abc_prerequisites": abc_prerequisites,
            "abc_prerequisites_all_pass": bool(abc_prerequisites.get("all_prerequisites_pass")),
            "strict_aa_panel_at_restart": strict_schema,
            "m3_autonomously_alive_at_t0": all_pass,
            "track_m3_signoff_pending": all_pass,
            "track_m3_signoff_note": (
                f"Phase C4 restarted 48h hold at {started.isoformat()}. "
                f"Re-run continuity_p2_phase24_aa_clock_proof.py daily until "
                f"{CONTINUITY_AA_HOLD_HOURS_V1}h elapsed with AA1–AA7 PASS."
                if all_pass
                else (
                    "C4 clock epoch restarted after A+B+C proofs; AA gates not all PASS yet — "
                    "fix panel before M3 sign-off."
                )
            ),
        }
    )
    return t0


def evaluate_aa_clock_hold_progress_v1(
    *,
    t0_baseline: dict[str, Any],
    panel: dict[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Daily hold check: elapsed hours + current AA verdicts vs T0."""
    ref = now or datetime.now(UTC)
    started_raw = str(t0_baseline.get("clock_started_at") or "")
    started = datetime.fromisoformat(started_raw)
    elapsed = aa_clock_hold_elapsed_hours_v1(clock_started_at=started, now=ref)
    required = int(t0_baseline.get("hold_hours_required") or CONTINUITY_AA_HOLD_HOURS_V1)
    all_pass_now = m3_panel_all_pass_v1(panel)
    hold_complete = elapsed >= float(required) and all_pass_now
    gates = dict(panel.get("gates") or {})
    return {
        "clock_started_at": started_raw,
        "clock_deadline_at": t0_baseline.get("clock_deadline_at"),
        "hold_hours_elapsed": round(elapsed, 2),
        "hold_hours_required": required,
        "hold_window_complete": elapsed >= float(required),
        "all_aa_gates_pass_now": all_pass_now,
        "m3_signoff_ready": hold_complete,
        "gate_verdicts_now": {
            gid: str((gates.get(gid) or {}).get("verdict") or "FAIL") for gid in AA_GATE_IDS_V1
        },
        "clock_restart_generation": t0_baseline.get("clock_restart_generation"),
    }


def verify_c4_aa_clock_restart_wiring_v1() -> dict[str, Any]:
    import inspect

    errors: list[str] = []
    src = inspect.getsource(build_aa_clock_c4_restart_t0_v1)
    for needle in (
        "abc_prerequisites",
        "clock_restart_generation",
        "prior_t0_superseded",
    ):
        if needle not in src:
            errors.append(f"c4_build_missing_{needle}")
    return {
        "wiring_ok": not errors,
        "errors": errors,
        "phase_c4_schema_version": PHASE_C4_CLOCK_RESTART_SCHEMA_VERSION,
        "prerequisite_step_count": len(C4_ABC_PREREQUISITE_STEP_KEYS_V1),
    }


def evaluate_p0_c4_aa_clock_restart_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    panel: dict[str, Any],
    t0_baseline: dict[str, Any],
    abc_prerequisites: dict[str, Any],
    prior_t0: dict[str, Any] | None,
    hold_progress: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """C4: ABC steps signed off, prior false T0 superseded, new hold epoch recorded."""
    p24 = evaluate_p2_4_aa_clock_proof_v1(
        closure_git_sha=closure_git_sha,
        prod_deploy=prod_deploy,
        panel=panel,
        t0_baseline=t0_baseline,
        deploy_recorded_at=deploy_recorded_at,
        trace_only=trace_only,
    )
    checks = {
        "ecs_deploy_matches_closure_sha": bool(
            (prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha")
        )
        or trace_only,
        "abc_prerequisites_all_pass": bool(abc_prerequisites.get("all_prerequisites_pass")),
        "abc_prerequisite_steps_complete": len(abc_prerequisites.get("missing_steps") or []) == 0,
        "no_trace_only_prerequisite_signoffs": len(abc_prerequisites.get("trace_only_steps") or [])
        == 0,
        "prior_t0_superseded_when_present": prior_t0 is None or bool(t0_baseline.get("prior_t0_superseded")),
        "c4_clock_restart_generation": int(t0_baseline.get("clock_restart_generation") or 0)
        >= C4_CLOCK_RESTART_GENERATION_V1,
        "c4_restart_step_recorded": t0_baseline.get("clock_restart_step") == P0_C4_STEP,
        "clock_started_at_recorded": bool(t0_baseline.get("clock_started_at")),
        "clock_deadline_at_recorded": bool(t0_baseline.get("clock_deadline_at")),
        "hold_hours_required_is_48": int(t0_baseline.get("hold_hours_required") or 0)
        == CONTINUITY_AA_HOLD_HOURS_V1,
        "t0_schema_version_valid": t0_baseline.get("schema_version")
        == CONTINUITY_AA_CLOCK_SCHEMA_VERSION_V1,
    }
    checks_advisory = {
        "all_aa_gates_pass_at_restart": m3_panel_all_pass_v1(panel),
        "m3_autonomously_alive_at_t0": t0_baseline.get("m3_autonomously_alive_at_t0"),
        "prior_t0_m3_at_capture": t0_baseline.get("prior_t0_m3_at_capture"),
        "prior_t0_clock_started_at": t0_baseline.get("prior_t0_clock_started_at"),
        "gate_verdicts_at_restart": t0_baseline.get("gate_verdicts"),
        "hold_progress": hold_progress,
        "p2_4_subproof": p24.get("checks"),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    p0_c4_pass = all(checks.values())
    return {
        "step": P0_C4_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "abc_prerequisites": abc_prerequisites,
        "t0_baseline": t0_baseline,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_c4_pass": p0_c4_pass,
        "verification": {
            "step_c4_pass": p0_c4_pass,
            "m3_hold_clock_restarted_after_abc": p0_c4_pass,
            "cleared_for_phase_d_parallel": p0_c4_pass,
            "daily_hold_script": "continuity_p2_phase24_aa_clock_proof.py",
        },
    }


def load_aa_clock_t0_baseline_v1(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_aa_clock_t0_baseline_v1(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path
