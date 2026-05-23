"""Phase B step B4 — phase 05 walks persisted proof evaluator."""

from __future__ import annotations

from vector.domains.cortex.substrate_pipeline.continuity_p0_phase05_walks_persisted import (
    evaluate_p0_b4_phase05_walks_persisted_proof_v1,
    verify_b4_phase05_walks_persisted_wiring_v1,
)


def test_b4_wiring_static() -> None:
    assert verify_b4_phase05_walks_persisted_wiring_v1()["wiring_ok"] is True


def test_b4_pass_when_recent_slices_have_walks() -> None:
    snapshot = {
        "has_durable_walks": True,
        "slices_with_walks_persisted_or_available": 2,
        "eligible_completed_empty_violations": 0,
        "latest_phase_05": {"walks_persisted": 3, "walks_available": 3},
        "phase_b4_schema_version": 1,
        "wiring": {"wiring_ok": True},
    }
    proof = evaluate_p0_b4_phase05_walks_persisted_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        trace_only=False,
    )
    assert proof["p0_b4_pass"] is True
