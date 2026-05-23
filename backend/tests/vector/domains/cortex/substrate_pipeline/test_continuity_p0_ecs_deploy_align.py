"""Phase A step A2 — ECS deploy alignment proof evaluator."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.substrate_pipeline.continuity_p0_ecs_deploy_align import (
    evaluate_p0_a2_ecs_deploy_align_proof_v1,
    verify_a2_ecs_deploy_align_wiring_v1,
)


def test_a2_wiring_static() -> None:
    root = Path(__file__).resolve().parents[6]
    wiring = verify_a2_ecs_deploy_align_wiring_v1(repo_root=root)
    assert wiring["wiring_ok"] is True


def test_a2_pass_when_aligned() -> None:
    sha = "acbbac8e87e750a525719613f2df84f41a2b3d32"
    prod_deploy = {
        "api": {"image_tag": sha},
        "worker": {"image_tag": sha},
        "verification": {
            "api_image_matches_closure_sha": True,
            "worker_image_matches_closure_sha": True,
            "both_services_on_same_tag": True,
            "deploy_matches_closure_sha": True,
        },
    }
    proof = evaluate_p0_a2_ecs_deploy_align_proof_v1(
        closure_git_sha=sha,
        prod_deploy=prod_deploy,
        wiring={"wiring_ok": True},
    )
    assert proof["p0_a2_pass"] is True


def test_a2_fail_on_split_tags() -> None:
    sha = "acbbac8e87e750a525719613f2df84f41a2b3d32"
    prod_deploy = {
        "api": {"image_tag": "2ab8776fafc8861ef69571f1531da1fd4f880a04"},
        "worker": {"image_tag": "8e30ba5aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},
        "verification": {
            "api_image_matches_closure_sha": False,
            "worker_image_matches_closure_sha": False,
            "both_services_on_same_tag": False,
            "deploy_matches_closure_sha": False,
        },
    }
    proof = evaluate_p0_a2_ecs_deploy_align_proof_v1(
        closure_git_sha=sha,
        prod_deploy=prod_deploy,
        wiring={"wiring_ok": True},
    )
    assert proof["p0_a2_pass"] is False
    assert proof["checks"]["both_services_on_same_tag"] is False
