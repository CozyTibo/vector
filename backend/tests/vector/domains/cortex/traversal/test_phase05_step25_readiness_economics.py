"""P05-25 — OCTS readiness + economics receipts + **G-P05-ECO-01..03**."""

from __future__ import annotations

import uuid

from vector.domains.cortex.traversal.traversal_readiness_economics import (
    assert_hostile_hub_fixture_breaches_thresholds_v1,
    build_octs_traversal_readiness_economics_receipt_v1,
    compute_economics_receipt_hash_v1,
    verify_gp05_eco01_max_out_degree_golden_static,
    verify_gp05_eco02_walk_wall_budget_golden_static,
    verify_gp05_eco03_derived_index_bytes_per_edge_golden_static,
    verify_octs_readiness_economics_receipt_v1_shape,
)


def test_gp05_eco_static_gates_pass() -> None:
    for fn in (
        verify_gp05_eco01_max_out_degree_golden_static,
        verify_gp05_eco02_walk_wall_budget_golden_static,
        verify_gp05_eco03_derived_index_bytes_per_edge_golden_static,
    ):
        out = fn()
        assert out["passed"] is True, out


def test_economics_receipt_hash_stable() -> None:
    h1 = compute_economics_receipt_hash_v1({"a": 1, "b": 2})
    h2 = compute_economics_receipt_hash_v1({"b": 2, "a": 1})
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_clean_receipt_shape_and_empty_violations() -> None:
    tid = uuid.uuid4()
    doc = build_octs_traversal_readiness_economics_receipt_v1(tenant_id=tid, profile="clean")
    assert verify_octs_readiness_economics_receipt_v1_shape(doc) == []
    assert doc["economics_violations"] == []
    assert doc["probe_profile"] == "clean"
    assert doc["octs_economics_threshold_table_version"] == doc["economics_stats"][
        "octs_economics_threshold_table_version"
    ]


def test_hostile_fixture_predictable_breaches() -> None:
    o = assert_hostile_hub_fixture_breaches_thresholds_v1()
    assert o["breach_max_out_degree"] is True
    assert o["breach_wall_budget"] is True


def test_hostile_receipt_lists_violations() -> None:
    tid = uuid.uuid4()
    doc = build_octs_traversal_readiness_economics_receipt_v1(tenant_id=tid, profile="hostile")
    assert "P05_ECO_MAX_OUT_DEGREE" in doc["economics_violations"]
    assert "P05_ECO_WALK_WALL_BUDGET" in doc["economics_violations"]
    assert doc["economics_stats"]["eco_violation_count"] >= 2
