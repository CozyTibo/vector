"""Phase C step C1 — phase 08 empty scope truth proof evaluator."""

from __future__ import annotations

from vector.domains.cortex.substrate_pipeline.continuity_p0_phase08_empty_scope_truth import (
    evaluate_p0_c1_phase08_empty_scope_truth_proof_v1,
    verify_c1_phase08_empty_scope_truth_wiring_v1,
)


def test_c1_wiring_static() -> None:
    assert verify_c1_phase08_empty_scope_truth_wiring_v1()["wiring_ok"] is True


def test_c1_pass_when_no_lies() -> None:
    snapshot = {
        "empty_scope_completed_empty_lies": 0,
        "legacy_empty_scope_lies": 0,
        "post_gate_empty_scope_lies": 0,
        "slices_with_jobs_completed": 2,
        "truthful_phase08_slices": 2,
        "retrieval_entries_in_published_epoch": 1200,
        "phase_c1_schema_version": 1,
        "wiring": {"wiring_ok": True, "gate_enabled": True},
    }
    proof = evaluate_p0_c1_phase08_empty_scope_truth_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        trace_only=False,
    )
    assert proof["p0_c1_pass"] is True
    assert proof["verification"]["cleared_for_c2"] is True


def test_c1_fails_when_legacy_lies_present() -> None:
    snapshot = {
        "empty_scope_completed_empty_lies": 1,
        "legacy_empty_scope_lies": 1,
        "post_gate_empty_scope_lies": 0,
        "slices_with_jobs_completed": 0,
        "truthful_phase08_slices": 0,
        "retrieval_entries_in_published_epoch": 50,
        "phase_c1_schema_version": 1,
        "wiring": {"wiring_ok": True, "gate_enabled": True},
    }
    proof = evaluate_p0_c1_phase08_empty_scope_truth_proof_v1(
        closure_git_sha="b" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        trace_only=False,
    )
    assert proof["p0_c1_pass"] is False
