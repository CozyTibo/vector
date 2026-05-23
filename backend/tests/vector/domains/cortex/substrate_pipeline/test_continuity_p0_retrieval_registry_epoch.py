"""Phase B step B3 — registry publish epoch proof evaluator."""

from __future__ import annotations

from vector.domains.cortex.operational_runtime.execution_island_registry import (
    FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_retrieval_registry_epoch import (
    evaluate_p0_b3_retrieval_registry_epoch_proof_v1,
    verify_b3_retrieval_registry_epoch_wiring_v1,
)


def test_b3_wiring_static() -> None:
    assert verify_b3_retrieval_registry_epoch_wiring_v1()["wiring_ok"] is True


def test_b3_pass_when_registry_aligned() -> None:
    snapshot = {
        "published_index_epoch": "epoch-new",
        "registry_epoch_audit": {
            "registry_rows_stale_vs_published": 0,
            "primary_island_epoch_aligned": True,
            "primary_island": {
                "island_scope_id": FIZZER_PRIMARY_ISLAND_SCOPE_ID_V1,
                "entries_in_scope_on_published": 10,
                "epoch_aligned": True,
            },
        },
        "registry_publish_schema_version": 1,
        "wiring": {"wiring_ok": True},
    }
    proof = evaluate_p0_b3_retrieval_registry_epoch_proof_v1(
        closure_git_sha="a" * 40,
        prod_deploy={"verification": {"deploy_matches_closure_sha": True}},
        snapshot=snapshot,
        trace_only=False,
    )
    assert proof["p0_b3_pass"] is True
