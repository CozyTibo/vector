"""S5.5 — execution reality inspection contract tests."""

from __future__ import annotations

from vector.domains.cortex.substrate_pipeline.execution_reality_inspection_v1 import (
    build_execution_reality_inspection_v1,
)


def test_execution_reality_inspection_shape_from_semantic_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.execution_reality_inspection_v1._sample_execution_thread_v1",
        lambda *a, **k: {
            "status": "sample",
            "sample_limit": 8,
            "primary_surface": "pipeline_semantic_readiness",
            "tcre_jobs": [],
            "recent_transitions": [],
        },
    )
    semantic = {
        "graph_truth": {
            "unique_auth_pairs": 10,
            "dup_factor": 1.0,
            "dup_factor_severity": "ok",
            "entities_in_auth_graph_pct": 80.0,
            "entities_isolated": 2,
            "promotion_rule_count": 3,
            "promotions_by_rule_id": [],
        },
        "identity_continuity": {
            "distinct_candidate_pairs": 5,
            "candidate_rows": 6,
            "candidate_inflation_ratio": 1.2,
            "candidate_inflation_severity": "ok",
            "anchors_missing_org_entity_pct": 10.0,
            "promotable_by_rule_id": [],
            "promotion_rule_count_green_min": 3,
        },
        "retrieval": {
            "published_index_epoch": "epoch-1",
            "entry_count": 100,
            "index_kind_counts": [{"index_kind": "walk", "count": 60}],
            "org_link_pct": 20.0,
            "execution_index_pct": 70.0,
            "org_link_pct_severity": "ok",
            "execution_index_pct_severity": "ok",
        },
    }
    inspection = build_execution_reality_inspection_v1(
        session=None,  # type: ignore[arg-type]
        tenant_id=__import__("uuid").UUID("00000000-0000-0000-0000-000000000001"),
        semantic_payload=semantic,
    )
    assert inspection["surface_kind"] == "execution_reality_inspection"
    assert "identity_continuity" in inspection
    assert "execution_thread" in inspection
    assert "retrieval_mix" in inspection
    assert "graph_truth" in inspection
    assert inspection["retrieval_mix"]["org_link_pct"] == 20.0
