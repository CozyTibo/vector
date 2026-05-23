"""Phase C4 — 48h AA clock restart after A+B+C."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from vector.domains.cortex.substrate_pipeline.continuity_p0_phase_c4_aa_clock_restart import (
    C4_ABC_PREREQUISITE_STEP_KEYS_V1,
    C4_CLOCK_RESTART_GENERATION_V1,
    build_aa_clock_c4_restart_t0_v1,
    evaluate_abc_prerequisites_from_baseline_v1,
    evaluate_aa_clock_hold_progress_v1,
    evaluate_p0_c4_aa_clock_restart_proof_v1,
    mark_prior_t0_superseded_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import AA_GATE_IDS_V1


def _green_panel() -> dict:
    gates = {
        gid: {"gate_id": gid, "verdict": "PASS", "pass": True}
        for gid in AA_GATE_IDS_V1
    }
    return {
        "surface_kind": "continuity_proof_panel",
        "strict_aa_panel_schema_version": 2,
        "gates": gates,
        "gate_order": list(AA_GATE_IDS_V1),
        "summary": {
            "pass_count": 7,
            "fail_count": 0,
            "advisory_count": 0,
            "m3_autonomously_alive": True,
        },
    }


def _full_abc_baseline() -> dict:
    baseline: dict = {}
    for key in C4_ABC_PREREQUISITE_STEP_KEYS_V1:
        baseline[key] = {"p0_x_pass": True, "trace_only": False, "signoff_grade": "prod"}
    return baseline


def test_abc_prerequisites_pass_when_all_steps_signed() -> None:
    abc = evaluate_abc_prerequisites_from_baseline_v1(_full_abc_baseline())
    assert abc["all_prerequisites_pass"] is True
    assert abc["missing_steps"] == []


def test_abc_prerequisites_fail_when_step_missing() -> None:
    baseline = _full_abc_baseline()
    del baseline["step_c3_continuity_audit_snapshot"]
    abc = evaluate_abc_prerequisites_from_baseline_v1(baseline)
    assert abc["all_prerequisites_pass"] is False
    assert "step_c3_continuity_audit_snapshot" in abc["missing_steps"]


def test_c4_restart_t0_supersedes_prior() -> None:
    prior = {
        "clock_started_at": "2026-05-22T00:00:00+00:00",
        "m3_autonomously_alive_at_t0": True,
        "closure_git_sha": "oldsha",
    }
    started = datetime(2026, 5, 23, 3, 0, 0, tzinfo=UTC)
    t0 = build_aa_clock_c4_restart_t0_v1(
        panel=_green_panel(),
        closure_git_sha="a" * 40,
        tenant_id=uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f"),
        abc_prerequisites={"all_prerequisites_pass": True},
        prior_t0=prior,
        clock_started_at=started,
    )
    assert t0["clock_restart_generation"] == C4_CLOCK_RESTART_GENERATION_V1
    assert t0["prior_t0_superseded"] is True
    assert t0["prior_t0_clock_started_at"] == prior["clock_started_at"]


def test_mark_prior_superseded_metadata() -> None:
    prior = {"clock_started_at": "2026-05-22T12:00:00+00:00"}
    now = datetime(2026, 5, 23, 3, 0, 0, tzinfo=UTC)
    out = mark_prior_t0_superseded_v1(
        prior,
        superseded_at=now,
        superseded_by_step="step_c4_aa48_clock_restart",
        new_clock_started_at=now,
    )
    assert out["superseded"] is True
    assert "superseded_at" in out


def test_c4_proof_passes_with_abc_and_restart() -> None:
    panel = _green_panel()
    started = datetime(2026, 5, 23, 3, 0, 0, tzinfo=UTC)
    abc = {"all_prerequisites_pass": True, "missing_steps": [], "trace_only_steps": []}
    prior = {"clock_started_at": "2026-05-22T00:00:00+00:00"}
    t0 = build_aa_clock_c4_restart_t0_v1(
        panel=panel,
        closure_git_sha="b" * 40,
        tenant_id=uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f"),
        abc_prerequisites=abc,
        prior_t0=prior,
        clock_started_at=started,
    )
    proof = evaluate_p0_c4_aa_clock_restart_proof_v1(
        closure_git_sha="b" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        panel=panel,
        t0_baseline=t0,
        abc_prerequisites=abc,
        prior_t0=prior,
    )
    assert proof["p0_c4_pass"] is True


def test_hold_progress_not_complete_before_48h() -> None:
    started = datetime(2026, 5, 23, 0, 0, 0, tzinfo=UTC)
    t0 = build_aa_clock_c4_restart_t0_v1(
        panel=_green_panel(),
        closure_git_sha="c" * 40,
        tenant_id=uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f"),
        abc_prerequisites={"all_prerequisites_pass": True},
        clock_started_at=started,
    )
    progress = evaluate_aa_clock_hold_progress_v1(
        t0_baseline=t0,
        panel=_green_panel(),
        now=started,
    )
    assert progress["hold_window_complete"] is False
    assert progress["m3_signoff_ready"] is False
