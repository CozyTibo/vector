"""Phase S3.4 — retrieval composition law receipt."""

from __future__ import annotations

from vector.domains.cortex.retrieval.retrieval_semantic_mix_v1 import (
    build_semantic_mix_receipt_v1,
    validate_retrieval_semantic_mix_v1,
)


def test_semantic_mix_receipt_shape() -> None:
    mix = {
        "index_epoch": "epoch-test",
        "entry_count": 100,
        "org_link_pct": 25.0,
        "org_entity_pct": 5.0,
        "execution_index_pct": 65.0,
        "execution_index_count": 65,
        "duplicate_retrieval_lookup_ids": 0,
    }
    ok, _ = validate_retrieval_semantic_mix_v1(mix)
    receipt = build_semantic_mix_receipt_v1(mix, gate_pass=ok)
    assert receipt["gate_pass"] is True
    assert receipt["org_link_pct"] == 25.0
    assert receipt["execution_index_pct"] == 65.0
    assert receipt["index_epoch"] == "epoch-test"
