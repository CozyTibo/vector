"""Phase B step B2 — epoch scope alignment proof evaluator."""

from __future__ import annotations

from vector.domains.cortex.retrieval.retrieval_epoch_scope_alignment import (
    FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_retrieval_epoch_scope_alignment import (
    evaluate_p0_b2_retrieval_epoch_scope_alignment_proof_v1,
    verify_b2_retrieval_epoch_scope_alignment_wiring_v1,
)


def test_b2_wiring_static() -> None:
    assert verify_b2_retrieval_epoch_scope_alignment_wiring_v1()["wiring_ok"] is True


def test_b2_pass_when_primary_in_scope() -> None:
    snapshot = {
        "published_index_epoch": "epoch-x",
        "primary_island_scope_id": FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
        "retrieval_entries_in_scope": 42,
        "fizzer_primary_in_scope": 42,
        "epoch_scope_alignment_schema_version": 1,
        "wiring": {"wiring_ok": True},
    }
    proof = evaluate_p0_b2_retrieval_epoch_scope_alignment_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        trace_only=False,
    )
    assert proof["p0_b2_pass"] is True
