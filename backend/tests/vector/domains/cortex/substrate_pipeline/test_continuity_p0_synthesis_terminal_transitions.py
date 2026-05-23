"""Phase A step A6 — synthesis terminal transitions proof evaluator."""

from __future__ import annotations

import uuid

from vector.domains.cortex.substrate_pipeline.continuity_p0_synthesis_terminal_transitions import (
    evaluate_p0_a6_synthesis_terminal_transitions_proof_v1,
    verify_a6_synthesis_terminal_transitions_wiring_v1,
)


def test_a6_wiring_static() -> None:
    assert verify_a6_synthesis_terminal_transitions_wiring_v1()["wiring_ok"] is True


def test_a6_pass_when_running_stable() -> None:
    snapshot = {
        "histogram": {"running": 0, "queued": 0, "failed": 10, "completed": 1},
        "running_count": 0,
        "stale_running_count": 0,
        "stale_queued_count": 0,
        "running_alert_threshold": 10,
        "phase_a_synthesis_terminal_runtime_schema_version": 1,
        "wiring": {"wiring_ok": True},
    }
    proof = evaluate_p0_a6_synthesis_terminal_transitions_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        reconcile_drive={"health_after": snapshot},
        trace_only=False,
    )
    assert proof["p0_a6_pass"] is True
