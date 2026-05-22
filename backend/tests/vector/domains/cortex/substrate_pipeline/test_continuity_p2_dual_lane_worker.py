"""Phase 2.3 — dual-lane worker proof evaluator."""

from __future__ import annotations

from datetime import UTC, datetime

from vector.domains.cortex.substrate_pipeline.continuity_p2_dual_lane_worker import (
    evaluate_p2_3_dual_lane_worker_proof_v1,
)


def _snapshot() -> dict:
    return {
        "dual_lane_enabled": True,
        "budgets": {
            "total_seconds": 540,
            "canonical_lane_seconds": 180,
            "execution_lane_seconds": 360,
        },
        "schedule": {
            "canonical_lane_owed": True,
            "execution_lane_owed": False,
            "execution_phase_cursor": "phase_07_retrieval",
            "canonical_parallel_while_execution": True,
        },
        "lease": {"phase_cursor": "phase_07_retrieval", "status": "waiting"},
        "last_dual_lane_slice": {
            "dual_lane_mode": True,
            "canonical_lane_ran": True,
            "execution_lane_ran": False,
            "execution_phase_cursor_before": "phase_07_retrieval",
            "execution_phase_cursor_after": "phase_07_retrieval",
            "canonical_budget_seconds": 180,
            "execution_budget_seconds": 360,
        },
    }


def test_p2_3_pass_when_canonical_ran_parallel() -> None:
    proof = evaluate_p2_3_dual_lane_worker_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=_snapshot(),
        slice_drive={
            "acquired": True,
            "canonical_only": True,
            "cursor_before": "phase_07_retrieval",
            "cursor_after": "phase_07_retrieval",
            "slice_result": {
                "dual_lane": {"dual_lane_mode": True, "canonical_lane_ran": True},
            },
        },
        deploy_recorded_at=datetime(2026, 5, 23, 0, 0, 0, tzinfo=UTC),
    )
    assert proof["p2_3_pass"] is True
    assert proof["verification"]["cleared_for_step_24"] is True


def test_p2_3_fails_without_canonical_ran() -> None:
    snap = _snapshot()
    snap["last_dual_lane_slice"] = {}
    snap["schedule"]["canonical_parallel_while_execution"] = False
    proof = evaluate_p2_3_dual_lane_worker_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snap,
    )
    assert proof["p2_3_pass"] is False
