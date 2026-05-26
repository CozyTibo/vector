"""Phase D2 — GitHub caps code-defaults proof evaluator."""

from __future__ import annotations

from pathlib import Path

from vector.domains.cortex.substrate_pipeline.continuity_p0_phase_d2_github_caps_align import (
    PHASE_D2_GITHUB_CAPS_SCHEMA_VERSION,
    evaluate_p0_d2_github_caps_align_proof_v1,
    verify_d2_github_caps_align_wiring_v1,
)

from vector.domains.cortex.substrate_pipeline.substrate_deploy_contract_v1 import (
    default_repo_root_v1,
)

REPO_ROOT = default_repo_root_v1()


def test_d2_wiring_ok() -> None:
    wiring = verify_d2_github_caps_align_wiring_v1(repo_root=REPO_ROOT)
    assert wiring["wiring_ok"] is True
    assert wiring["settings_defaults_ok"] is True
    assert wiring["infra_ecs_json_ok"] is True


def test_d2_proof_passes_with_aligned_ecs() -> None:
    snapshot = {
        "wiring": {
            "wiring_ok": True,
            "settings_defaults_ok": True,
            "infra_ecs_json_ok": True,
            "phase_d2_schema_version": PHASE_D2_GITHUB_CAPS_SCHEMA_VERSION,
        },
        "settings_caps": {
            "meets_fix6_recommended": True,
            "fix6_require_recommended_pass": True,
        },
        "deferral_totals": {"deferred_total": 466},
        "ecs_github_cap_env": {
            "skipped": False,
            "api": {"matches_code_defaults": True, "has_legacy_low_override": False},
            "worker": {"matches_code_defaults": True, "has_legacy_low_override": False},
        },
    }
    proof = evaluate_p0_d2_github_caps_align_proof_v1(
        closure_git_sha="abc",
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        require_prod_ecs_aligned=True,
    )
    assert proof["p0_d2_pass"] is True
