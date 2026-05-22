"""Phase 2.4 — forty-eight-hour AA M3 hold clock."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from vector.domains.cortex.substrate_pipeline.continuity_p2_aa_clock import (
    CONTINUITY_AA_HOLD_HOURS_V1,
    aa_clock_hold_deadline_v1,
    aa_clock_hold_elapsed_hours_v1,
    build_aa_clock_t0_baseline_v1,
    evaluate_p2_4_aa_clock_proof_v1,
    m3_panel_all_pass_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_proof_panel import AA_GATE_IDS_V1


def _green_panel() -> dict:
    gates = {
        gid: {"gate_id": gid, "verdict": "PASS", "pass": True, "criterion": "", "detail": "", "evidence": {}}
        for gid in AA_GATE_IDS_V1
    }
    return {
        "surface_kind": "continuity_proof_panel",
        "tenant_id": "c08ef32b-f89a-40f6-9566-e19b5329436f",
        "pipeline_run_id": "ce7df86d-b229-4467-ad28-1109ed119d34",
        "evaluated_at": "2026-05-22T12:00:00+00:00",
        "gates": gates,
        "gate_order": list(AA_GATE_IDS_V1),
        "summary": {
            "pass_count": 7,
            "fail_count": 0,
            "advisory_count": 0,
            "total_gates": 7,
            "m3_autonomously_alive": True,
            "metric_tier": "M3",
        },
    }


def test_m3_panel_all_pass() -> None:
    assert m3_panel_all_pass_v1(_green_panel()) is True
    bad = _green_panel()
    bad["gates"]["AA6"]["verdict"] = "FAIL"
    assert m3_panel_all_pass_v1(bad) is False


def test_build_t0_baseline_starts_clock() -> None:
    started = datetime(2026, 5, 22, 15, 0, 0, tzinfo=UTC)
    t0 = build_aa_clock_t0_baseline_v1(
        panel=_green_panel(),
        closure_git_sha="a" * 40,
        tenant_id=uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f"),
        clock_started_at=started,
    )
    assert t0["m3_autonomously_alive_at_t0"] is True
    assert t0["track_m3_signoff_pending"] is True
    assert t0["hold_hours_required"] == CONTINUITY_AA_HOLD_HOURS_V1
    assert t0["clock_started_at"] == started.isoformat()
    assert aa_clock_hold_deadline_v1(clock_started_at=started) == started + timedelta(hours=48)


def test_p2_4_pass_when_t0_green() -> None:
    panel = _green_panel()
    t0 = build_aa_clock_t0_baseline_v1(
        panel=panel,
        closure_git_sha="a" * 40,
        tenant_id=uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f"),
    )
    proof = evaluate_p2_4_aa_clock_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        panel=panel,
        t0_baseline=t0,
        deploy_recorded_at=datetime(2026, 5, 22, 12, 0, 0, tzinfo=UTC),
    )
    assert proof["p2_4_pass"] is True
    assert proof["verification"]["m3_hold_clock_started"] is True
    assert proof["verification"]["cleared_for_phase_3"] is True


def test_p2_4_fails_when_aa_not_all_pass() -> None:
    panel = _green_panel()
    panel["gates"]["AA2"]["verdict"] = "ADVISORY"
    panel["summary"]["m3_autonomously_alive"] = False
    t0 = build_aa_clock_t0_baseline_v1(
        panel=panel,
        closure_git_sha="a" * 40,
        tenant_id=uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f"),
    )
    proof = evaluate_p2_4_aa_clock_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        panel=panel,
        t0_baseline=t0,
    )
    assert proof["p2_4_pass"] is False


def test_hold_elapsed_hours() -> None:
    started = datetime(2026, 5, 22, 0, 0, 0, tzinfo=UTC)
    now = started + timedelta(hours=12, minutes=30)
    assert aa_clock_hold_elapsed_hours_v1(clock_started_at=started, now=now) == 12.5
