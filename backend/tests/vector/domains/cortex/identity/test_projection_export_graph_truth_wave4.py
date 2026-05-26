"""Wave 4 — projection export hash delta without DB."""

from __future__ import annotations

from unittest.mock import MagicMock

from vector.domains.cortex.identity.projection_export import run_graph_projection_export_for_pipeline_v1


def test_projection_hash_changed_when_prior_differs(monkeypatch) -> None:
    monkeypatch.setattr(
        "vector.domains.cortex.identity.projection_export.build_org_graph_projection_export_document",
        lambda *_a, **_k: {
            "stable_hash_sha256": "new-hash",
            "org_graph_projection_schema_version": 1,
            "engine_build_ref": "test",
            "projection": {"nodes": [], "edges": []},
        },
    )
    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.graph_truth_metrics_v1.snapshot_authoritative_link_topology_v1",
        lambda *_a, **_k: {"auth_edge_rows": 1, "unique_auth_pairs": 1, "dup_factor": 1.0},
    )
    monkeypatch.setattr(
        "vector.domains.cortex.substrate_pipeline.graph_truth_metrics_v1.snapshot_graph_substrate_isolation_v1",
        lambda *_a, **_k: {
            "isolated_pct": 80.0,
            "largest_component_entity_pct": 20.0,
            "entities_in_largest_auth_component": 2,
            "entities_in_auth_graph": 2,
            "entities_isolated": 8,
        },
    )
    out = run_graph_projection_export_for_pipeline_v1(
        MagicMock(),
        tenant_id=__import__("uuid").uuid4(),
        prior_graph_projection_stable_hash="old-hash",
        prior_isolated_pct=85.0,
    )
    assert out["projection_hash_changed"] is True
    assert out["isolated_pct_delta"] == -5.0
