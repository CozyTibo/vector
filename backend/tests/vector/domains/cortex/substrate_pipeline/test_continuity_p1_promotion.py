"""Phase 1 step 1.3 — P1-B promotion proof evaluator."""

from __future__ import annotations

from datetime import UTC, datetime

from vector.domains.cortex.substrate_pipeline.continuity_p1_promotion import (
    P1_B_MIN_PROMOTION_MAX_PER_PASS,
    evaluate_p1_3_promotion_proof_v1,
)


def test_p1_3_pass_when_pending_decreases() -> None:
    proof = evaluate_p1_3_promotion_proof_v1(
        closure_git_sha="abc123" * 5,
        prod_deploy={
            "verification": {"deploy_matches_closure_sha": True},
        },
        worker_path={"m9_promotion_path_ok": True},
        drain_result={
            "max_per_pass": P1_B_MIN_PROMOTION_MAX_PER_PASS,
            "passes_executed": 2,
            "total_promoted": 400,
            "pending_delta": 350,
            "metrics_before": {
                "pending_link_candidates": 3600,
                "pending_candidate_threshold": 10,
            },
            "metrics_after": {
                "pending_link_candidates": 3250,
            },
        },
        deploy_recorded_at=datetime(2026, 5, 22, 23, 0, 0, tzinfo=UTC),
    )
    assert proof["p1_3_pass"] is True
    assert proof["verification"]["step_13_pass"] is True


def test_p1_3_fails_when_pending_flat() -> None:
    proof = evaluate_p1_3_promotion_proof_v1(
        closure_git_sha="abc123" * 5,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        worker_path={"m9_promotion_path_ok": True},
        drain_result={
            "max_per_pass": 400,
            "passes_executed": 1,
            "total_promoted": 0,
            "pending_delta": 0,
            "metrics_before": {"pending_link_candidates": 100, "pending_candidate_threshold": 10},
            "metrics_after": {"pending_link_candidates": 100},
        },
    )
    assert proof["p1_3_pass"] is False
