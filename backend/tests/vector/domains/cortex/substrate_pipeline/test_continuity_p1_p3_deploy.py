"""Phase 1 step 1.2 — P3′ deploy proof evaluator."""

from __future__ import annotations

from datetime import UTC, datetime

from vector.domains.cortex.substrate_pipeline.continuity_p1_p3_deploy import (
    evaluate_p1_2_p3_deploy_proof_v1,
)


def test_p1_2_pass_when_deploy_and_autonomous_walks() -> None:
    deploy_at = datetime(2026, 5, 22, 22, 10, 0, tzinfo=UTC)
    proof = evaluate_p1_2_p3_deploy_proof_v1(
        closure_git_sha="80aea87" * 5,
        prod_deploy={
            "api": {"image_tag": "80aea87" + "0" * 32},
            "worker": {"image_tag": "80aea87" + "0" * 32},
            "verification": {"deploy_matches_closure_sha": True},
        },
        schedule_pass={
            "evaluation": {
                "should_schedule": True,
                "traversal_propagation_blocked": False,
                "islands_eligible_count": 2,
            },
            "scheduled": True,
            "persisted_new": 3,
            "path": "inline_execution_slice",
        },
        walks_before={
            "total_count": 24,
            "newest_created_at": "2026-05-22T21:36:24+00:00",
        },
        walks_after={
            "total_count": 27,
            "newest_created_at": "2026-05-22T22:15:00+00:00",
        },
        deploy_recorded_at=deploy_at,
    )
    assert proof["p1_2_pass"] is True
    assert proof["verification"]["step_12_pass"] is True


def test_p1_2_fails_when_deploy_mismatch() -> None:
    proof = evaluate_p1_2_p3_deploy_proof_v1(
        closure_git_sha="80aea87" * 5,
        prod_deploy={
            "api": {"image_tag": "0146cd0"},
            "worker": {"image_tag": "0146cd0"},
            "verification": {"deploy_matches_closure_sha": False},
        },
        schedule_pass={
            "evaluation": {"should_schedule": True, "traversal_propagation_blocked": False},
            "scheduled": True,
            "persisted_new": 1,
        },
        walks_before={"total_count": 1, "newest_created_at": "2026-05-22T20:00:00+00:00"},
        walks_after={"total_count": 2, "newest_created_at": "2026-05-22T22:00:00+00:00"},
        deploy_recorded_at=datetime(2026, 5, 22, 22, 0, 0, tzinfo=UTC),
    )
    assert proof["p1_2_pass"] is False
