"""Phase 2 step 2.1 — dual-lane proof evaluator."""

from __future__ import annotations

from datetime import UTC, datetime

from vector.domains.cortex.substrate_pipeline.continuity_p2_dual_lane import (
    evaluate_p2_1_dual_lane_proof_v1,
)


def _snapshot() -> dict:
    return {
        "phase_cursor": "phase_07_retrieval",
        "dual_lane": {
            "dual_lane_enabled": True,
            "canonical_lane": {
                "lane": "canonical",
                "lane_status": "WAITING",
                "topology_wait": True,
                "outcome": "topology_wait",
            },
            "execution_lane": {
                "lane": "execution",
                "lane_status": "WAITING",
                "phase_cursor": "phase_07_retrieval",
                "waiting_reason": "tcre_async",
            },
            "topology_decoupled_from_execution_cursor": True,
        },
        "detail_json_canonical_lane": {"lane": "canonical", "lane_status": "WAITING"},
        "detail_json_execution_lane": {"lane": "execution", "lane_status": "WAITING"},
        "lease_summary": {
            "canonical_lane": "WAITING",
            "execution_lane": "WAITING",
            "phase_cursor": "phase_07_retrieval",
        },
    }


def test_p2_1_pass_when_both_lanes_in_inspect() -> None:
    proof = evaluate_p2_1_dual_lane_proof_v1(
        closure_git_sha="abc" * 10,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=_snapshot(),
        deploy_recorded_at=datetime(2026, 5, 23, 0, 0, 0, tzinfo=UTC),
    )
    assert proof["p2_1_pass"] is True
    assert proof["verification"]["cleared_for_step_22"] is True


def test_p2_1_fails_without_dual_lane_block() -> None:
    snap = _snapshot()
    snap["dual_lane"] = {}
    snap["detail_json_canonical_lane"] = None
    proof = evaluate_p2_1_dual_lane_proof_v1(
        closure_git_sha="abc" * 10,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snap,
    )
    assert proof["p2_1_pass"] is False
