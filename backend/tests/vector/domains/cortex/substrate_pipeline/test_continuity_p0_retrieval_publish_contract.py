"""Phase B step B1 — retrieval publish contract proof evaluator."""

from __future__ import annotations

from vector.domains.cortex.substrate_pipeline.continuity_p0_retrieval_publish_contract import (
    evaluate_p0_b1_retrieval_publish_contract_proof_v1,
    verify_b1_retrieval_publish_contract_wiring_v1,
)


def test_b1_wiring_static() -> None:
    assert verify_b1_retrieval_publish_contract_wiring_v1()["wiring_ok"] is True


def test_b1_pass_when_published_epoch_aligns() -> None:
    snapshot = {
        "published_index_epoch": "epoch-abc",
        "building_epochs_inflight": 0,
        "publish_contract_audit": {
            "epochs_align": True,
            "build_state": "PUBLISHED",
            "entries_in_materialized_epoch": 10,
        },
        "phase_b_retrieval_publish_contract_schema_version": 1,
        "wiring": {"wiring_ok": True},
    }
    proof = evaluate_p0_b1_retrieval_publish_contract_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        trace_only=False,
    )
    assert proof["p0_b1_pass"] is True


def test_b1_fails_when_epochs_misaligned_with_entries() -> None:
    snapshot = {
        "published_index_epoch": "epoch-new",
        "building_epochs_inflight": 1,
        "publish_contract_audit": {
            "epochs_align": False,
            "build_state": "PUBLISHED",
            "entries_in_materialized_epoch": 5,
        },
        "phase_b_retrieval_publish_contract_schema_version": 1,
        "wiring": {"wiring_ok": True},
    }
    proof = evaluate_p0_b1_retrieval_publish_contract_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        trace_only=False,
    )
    assert proof["p0_b1_pass"] is False
