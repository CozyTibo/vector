"""Phase 2 step 2.4 — M3 AA1–AA7 forty-eight-hour hold clock (T0 baseline)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import (
    AA_GATE_IDS_V1,
    P2_2_STEP,
)

P2_4_STEP = "2.4_aa48_clock"
CONTINUITY_AA_HOLD_HOURS_V1: Final[int] = 48
CONTINUITY_AA_CLOCK_SCHEMA_VERSION_V1: Final[int] = 1
CONTINUITY_AA_CLOCK_BASELINE_PREFIX = "continuity_aa_clock_T0_"


def continuity_aa_clock_baseline_path_v1(
    *,
    repo_root: Any,
    date_suffix: str | None = None,
) -> Any:
    """Dedicated T0 JSON path: ``DOCS/audits/baselines/continuity_aa_clock_T0_<date>.json``."""
    from pathlib import Path

    suffix = date_suffix or datetime.now(UTC).strftime("%Y-%m-%d")
    return Path(repo_root) / "DOCS" / "audits" / "baselines" / f"{CONTINUITY_AA_CLOCK_BASELINE_PREFIX}{suffix}.json"


def _gate_verdicts_from_panel_v1(panel: dict[str, Any]) -> dict[str, str]:
    gates = dict(panel.get("gates") or {})
    return {
        gid: str((gates.get(gid) or {}).get("verdict") or "FAIL")
        for gid in AA_GATE_IDS_V1
    }


def m3_panel_all_pass_v1(panel: dict[str, Any]) -> bool:
    """True when every AA gate is PASS (M3 autonomously alive at capture)."""
    verdicts = _gate_verdicts_from_panel_v1(panel)
    return all(verdicts.get(gid) == "PASS" for gid in AA_GATE_IDS_V1)


def aa_clock_hold_deadline_v1(*, clock_started_at: datetime) -> datetime:
    return clock_started_at + timedelta(hours=CONTINUITY_AA_HOLD_HOURS_V1)


def aa_clock_hold_elapsed_hours_v1(*, clock_started_at: datetime, now: datetime | None = None) -> float:
    ref = now or datetime.now(UTC)
    started = clock_started_at if clock_started_at.tzinfo else clock_started_at.replace(tzinfo=UTC)
    ref = ref if ref.tzinfo else ref.replace(tzinfo=UTC)
    return max(0.0, (ref - started).total_seconds() / 3600.0)


def build_aa_clock_t0_baseline_v1(
    *,
    panel: dict[str, Any],
    closure_git_sha: str,
    tenant_id: uuid.UUID,
    wedge_free_ack: bool = False,
    clock_started_at: datetime | None = None,
) -> dict[str, Any]:
    """Capture T0 when AA1–AA7 are green; starts the forty-eight-hour M3 hold clock."""
    started = clock_started_at or datetime.now(UTC)
    if started.tzinfo is None:
        started = started.replace(tzinfo=UTC)
    summary = dict(panel.get("summary") or {})
    gate_verdicts = _gate_verdicts_from_panel_v1(panel)
    all_pass = m3_panel_all_pass_v1(panel)
    deadline = aa_clock_hold_deadline_v1(clock_started_at=started)
    return {
        "schema_version": CONTINUITY_AA_CLOCK_SCHEMA_VERSION_V1,
        "step": P2_4_STEP,
        "metric_tier": "M3",
        "tenant_id": str(tenant_id),
        "pipeline_run_id": panel.get("pipeline_run_id"),
        "closure_git_sha": closure_git_sha,
        "clock_started_at": started.isoformat(),
        "clock_deadline_at": deadline.isoformat(),
        "hold_hours_required": CONTINUITY_AA_HOLD_HOURS_V1,
        "hold_hours_elapsed": 0.0,
        "wedge_free_ack_at_t0": bool(wedge_free_ack),
        "panel_step": P2_2_STEP,
        "panel_evaluated_at": panel.get("evaluated_at"),
        "gate_verdicts": gate_verdicts,
        "panel_summary": summary,
        "m3_autonomously_alive_at_t0": bool(summary.get("m3_autonomously_alive")) and all_pass,
        "aa_gates_pass_count": int(summary.get("pass_count") or 0),
        "aa_gates_total": len(AA_GATE_IDS_V1),
        "track_m3_signoff_pending": all_pass,
        "track_m3_signoff_note": (
            "Re-run continuity_p2_phase24_aa_clock_proof.py daily; M3 sign-off when AA1–AA7 "
            f"stay PASS for {CONTINUITY_AA_HOLD_HOURS_V1}h without wedge scripts."
            if all_pass
            else "Fix failing AA gates before starting forty-eight-hour hold clock."
        ),
        "proof_panel": {
            "surface_kind": panel.get("surface_kind"),
            "gate_order": list(panel.get("gate_order") or AA_GATE_IDS_V1),
        },
    }


def evaluate_p2_4_aa_clock_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    panel: dict[str, Any],
    t0_baseline: dict[str, Any],
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step 2.4: T0 baseline written and M3 hold clock started."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    summary = dict(panel.get("summary") or {})
    gate_verdicts = _gate_verdicts_from_panel_v1(panel)
    m3_at_capture = m3_panel_all_pass_v1(panel)
    started_raw = t0_baseline.get("clock_started_at")
    deadline_raw = t0_baseline.get("clock_deadline_at")
    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "t0_baseline_schema_version": t0_baseline.get("schema_version")
        == CONTINUITY_AA_CLOCK_SCHEMA_VERSION_V1,
        "clock_started_at_recorded": bool(started_raw),
        "clock_deadline_at_recorded": bool(deadline_raw),
        "hold_hours_required_is_48": int(t0_baseline.get("hold_hours_required") or 0)
        == CONTINUITY_AA_HOLD_HOURS_V1,
        "all_aa_gates_pass_at_t0": m3_at_capture,
        "m3_autonomously_alive_at_t0": bool(t0_baseline.get("m3_autonomously_alive_at_t0")),
        "track_m3_signoff_pending": bool(t0_baseline.get("track_m3_signoff_pending")),
        "gate_verdicts_snapshot_complete": set(gate_verdicts.keys()) >= set(AA_GATE_IDS_V1),
        "t0_gate_verdicts_all_pass": all(
            gate_verdicts.get(gid) == "PASS" for gid in AA_GATE_IDS_V1
        ),
    }
    checks_advisory = {
        "aa_gates_pass_count": int(summary.get("pass_count") or 0),
        "hold_hours_elapsed_at_proof": float(t0_baseline.get("hold_hours_elapsed") or 0),
        "clock_deadline_at": deadline_raw,
    }
    step_24_pass = all(checks.values())
    return {
        "step": P2_4_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "panel_summary": summary,
        "gate_verdicts": gate_verdicts,
        "t0_baseline": t0_baseline,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p2_4_pass": step_24_pass,
        "verification": {
            "step_24_pass": step_24_pass,
            "cleared_for_phase_3": step_24_pass,
            "m3_hold_clock_started": step_24_pass and m3_at_capture,
        },
    }
