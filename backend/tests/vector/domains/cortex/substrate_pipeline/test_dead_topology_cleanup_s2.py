"""Phase S2.6 — dead topology cleanup (admin KPIs and receipts)."""

from __future__ import annotations

from vector.domains.cortex.continuity.edge_contracts import (
    ContinuityEdgeKind,
    list_continuity_edge_kinds_schema_only_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_04_GRAPH
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import (
    extract_phase_receipt_detail_v1,
    infer_processed_count_v1,
)
from vector.domains.cortex.substrate_pipeline.wave_s5_cleanup_v1 import (
    DEPRECATED_OPERATOR_PRIMARY_METRICS_V1,
)


def test_continuity_edge_kinds_marked_schema_only_non_kpi() -> None:
    rows = list_continuity_edge_kinds_schema_only_v1()
    assert len(rows) == len(ContinuityEdgeKind)
    assert all(r["operator_kpi"] is False for r in rows)
    assert all(r["retrieval_indexed"] is False for r in rows)


def test_phase_04_receipt_uses_graph_truth_kpis_not_node_count() -> None:
    raw = {
        "graph_projection_stable_hash_sha256": "sha256:abc",
        "node_count": 100,
        "edge_count": 9999,
        "unique_auth_pairs": 42,
        "projection_hash_changed": True,
        "isolated_pct": 91.2,
        "isolated_pct_delta": -0.5,
        "largest_component_entity_pct": 8.0,
    }
    detail = extract_phase_receipt_detail_v1(PHASE_04_GRAPH, raw)
    assert detail["projection_hash_changed"] is True
    assert detail["isolated_pct"] == 91.2
    assert "node_count" not in detail
    assert "edge_count" not in detail
    assert infer_processed_count_v1(PHASE_04_GRAPH, raw) == 1


def test_phase_04_processed_count_zero_when_hash_unchanged() -> None:
    raw = {
        "projection_hash_changed": False,
        "isolated_pct": 50.0,
        "unique_auth_pairs": 99,
    }
    assert infer_processed_count_v1(PHASE_04_GRAPH, raw) == 0


def test_deprecated_topology_metrics_include_edge_count() -> None:
    assert "edge_count_primary" in DEPRECATED_OPERATOR_PRIMARY_METRICS_V1
    assert "phase_04_edge_count_receipt" in DEPRECATED_OPERATOR_PRIMARY_METRICS_V1
