"""Phase 0 step 0.5 — baseline closure merge and verification."""

from __future__ import annotations

from vector.domains.cortex.substrate_pipeline.continuity_p0_baseline import (
    apply_step_0_5_to_baseline_v1,
    build_step_0_5_phase0_closure_v1,
    evaluate_phase0_prerequisites_v1,
    merge_step_0_2_deploy_into_baseline_v1,
)

CLOSURE_SHA = "b8ca0065f68eaab6ce7f04749d9818c14b7ce995"


def _sample_baseline() -> dict:
    return {
        "step_0_2_deploy": {"git_sha_full": "0146cd05149c03a8b6e9572e1bc6739f24584b2e"},
        "git_sha_full": "0146cd05149c03a8b6e9572e1bc6739f24584b2e",
        "step_0_3_pipeline_recovery": {
            "verification": {"step_03_pass": True},
        },
        "step_0_4_phase05_proof": {
            "p0_b_pass": True,
            "verification": {"step_04_pass": True},
        },
    }


def _prod_deploy(*, match: bool) -> dict:
    tag = CLOSURE_SHA if match else "0146cd05149c"
    return {
        "git_sha_full": CLOSURE_SHA,
        "git_sha_short": CLOSURE_SHA[:12],
        "api": {"image_tag": tag},
        "worker": {"image_tag": tag},
        "verification": {
            "api_image_matches_closure_sha": match,
            "worker_image_matches_closure_sha": match,
            "both_services_on_same_tag": True,
            "deploy_matches_closure_sha": match,
        },
    }


def test_prerequisites_all_true_when_steps_present() -> None:
    prereq = evaluate_phase0_prerequisites_v1(_sample_baseline())
    assert all(prereq.values())


def test_step_0_5_passes_when_deploy_and_prereqs_ok() -> None:
    closure = build_step_0_5_phase0_closure_v1(
        closure_git_sha=CLOSURE_SHA,
        prod_deploy=_prod_deploy(match=True),
        baseline=_sample_baseline(),
    )
    assert closure["verification"]["step_05_pass"] is True
    assert closure["verification"]["phase_0_complete"] is True


def test_step_0_5_fails_on_deploy_mismatch() -> None:
    closure = build_step_0_5_phase0_closure_v1(
        closure_git_sha=CLOSURE_SHA,
        prod_deploy=_prod_deploy(match=False),
        baseline=_sample_baseline(),
    )
    assert closure["verification"]["step_05_pass"] is False


def test_apply_step_0_5_sets_phase0_complete_flag() -> None:
    baseline = _sample_baseline()
    closure = build_step_0_5_phase0_closure_v1(
        closure_git_sha=CLOSURE_SHA,
        prod_deploy=_prod_deploy(match=True),
        baseline=baseline,
    )
    out = apply_step_0_5_to_baseline_v1(baseline, closure)
    assert out["phase0_closure_git_sha"] == CLOSURE_SHA
    assert out["phase0_complete"] is True
    assert "step_0_5_phase0_closure" in out


def test_merge_step_0_2_preserves_step_0_4() -> None:
    baseline = _sample_baseline()
    deploy = _prod_deploy(match=True)
    deploy["recorded_at"] = "2026-05-22T22:00:00+00:00"
    deploy["aws_region"] = "eu-west-1"
    deploy["ecs_cluster"] = "vector-prod"
    deploy["api"]["service"] = "vector-backend-service"
    deploy["worker"] = {
        "service": "vector-worker-service",
        "task_definition": "arn:worker:1",
        "image": f"ecr/worker:{CLOSURE_SHA}",
        "image_tag": CLOSURE_SHA,
    }
    deploy["api"]["task_definition"] = "arn:api:1"
    deploy["api"]["image"] = f"ecr/api:{CLOSURE_SHA}"
    merged = merge_step_0_2_deploy_into_baseline_v1(baseline, deploy)
    assert merged["step_0_4_phase05_proof"]["p0_b_pass"] is True
    assert merged["step_0_2_deploy"]["git_sha_full"] == CLOSURE_SHA
