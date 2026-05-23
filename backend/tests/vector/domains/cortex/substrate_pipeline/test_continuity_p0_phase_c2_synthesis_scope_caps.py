"""Phase C2 — continuity proof evaluator unit tests."""

from __future__ import annotations

from vector.domains.cortex.synthesis.synthesis_per_island_scope_cap_gate import (
    PHASE_C2_SCOPE_CAP_SCHEMA_VERSION,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_phase_c2_synthesis_scope_caps import (
    evaluate_p0_c2_synthesis_scope_caps_proof_v1,
)


def _snapshot(**overrides: object) -> dict:
    base = {
        "phase_c2_schema_version": PHASE_C2_SCOPE_CAP_SCHEMA_VERSION,
        "wiring": {
            "wiring_ok": True,
            "fail_loud_enabled": True,
        },
        "artifact_stats": {
            "artifacts_primary_island": 3,
            "artifacts_total": 5,
        },
        "slices_with_cap_audit": 1,
        "max_scopes_on_capped_slice": 8,
        "slices_with_jobs_completed": 1,
    }
    base.update(overrides)
    return base


def test_c2_proof_passes_when_checks_met() -> None:
    proof = evaluate_p0_c2_synthesis_scope_caps_proof_v1(
        closure_git_sha="abc123",
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=_snapshot(),
    )
    assert proof["p0_c2_pass"] is True
    assert proof["checks"]["primary_island_synthesis_velocity_48h"] is True


def test_c2_proof_passes_with_cap_law_when_artifacts_sparse() -> None:
    proof = evaluate_p0_c2_synthesis_scope_caps_proof_v1(
        closure_git_sha="abc123",
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=_snapshot(
            artifact_stats={"artifacts_primary_island": 0, "artifacts_total": 0},
            slices_with_cap_audit=1,
            max_scopes_on_capped_slice=8,
            slices_with_jobs_completed=0,
        ),
    )
    assert proof["p0_c2_pass"] is True
    assert proof["checks"]["per_island_scope_cap_law_exercised"] is True


def test_c2_proof_fails_without_artifacts_or_cap_law() -> None:
    proof = evaluate_p0_c2_synthesis_scope_caps_proof_v1(
        closure_git_sha="abc123",
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=_snapshot(
            artifact_stats={"artifacts_primary_island": 0, "artifacts_total": 0},
            slices_with_cap_audit=0,
            max_scopes_on_capped_slice=0,
            slices_with_jobs_completed=0,
        ),
    )
    assert proof["p0_c2_pass"] is False
    assert proof["checks"]["primary_island_synthesis_velocity_48h"] is False
