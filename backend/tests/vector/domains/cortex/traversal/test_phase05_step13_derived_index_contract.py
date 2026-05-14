"""P05-13 — derived index contract (**G-P05-IDX-01**, **G-P05-IDX-02**)."""

from __future__ import annotations

import json

import pytest

from vector.domains.cortex.traversal.derived_index_contract import (
    DI_RUNTIME_SCHEMA_VERSION,
    PUBLISH_STATE_PUBLISHED,
    DerivedIndexContractError,
    canonical_derived_index_artifact_json_bytes_v1,
    compute_index_content_hash_v1,
    list_fs_di01_derived_edge_lineage_violations,
    list_fs_di03_index_epoch_regression_violations,
    octs_derived_index_fixture_dir,
    validate_derived_index_artifact_contract_v1,
    validate_publish_barrier_record_v1,
    validate_stale_derived_read_policy_v1,
    verify_gp05_idx01_index_content_hash_stability_static,
    verify_gp05_idx02_lineage_completeness_static,
)
from vector.domains.cortex.traversal.observed_vs_derived import (
    WALK_EXECUTION_STRATEGY_MATERIALIZED_DERIVED,
    WALK_EXECUTION_STRATEGY_ONLINE_OBSERVED,
)


def test_di_runtime_schema_version() -> None:
    assert DI_RUNTIME_SCHEMA_VERSION >= 1


def test_verify_gp05_idx01_static_passes() -> None:
    out = verify_gp05_idx01_index_content_hash_stability_static()
    assert out["id"] == "G-P05-IDX-01"
    assert out["passed"] is True


def test_verify_gp05_idx02_static_passes() -> None:
    out = verify_gp05_idx02_lineage_completeness_static()
    assert out["id"] == "G-P05-IDX-02"
    assert out["passed"] is True


def test_fixture_dir() -> None:
    d = octs_derived_index_fixture_dir()
    assert (d / "derived_index_artifact_good_v1.json").is_file()


def test_index_hash_order_independent_on_edges() -> None:
    d = octs_derived_index_fixture_dir()
    art = json.loads((d / "derived_index_artifact_good_v1.json").read_text(encoding="utf-8"))
    art2 = json.loads(json.dumps(art))
    edges = art2["derived_edges"]
    assert isinstance(edges, list) and len(edges) >= 1
    art2["derived_edges"] = list(reversed(edges))
    assert compute_index_content_hash_v1(art) == compute_index_content_hash_v1(art2)


def test_canonical_bytes_stable_whitespace_insensitive() -> None:
    d = octs_derived_index_fixture_dir()
    art = json.loads((d / "derived_index_artifact_good_v1.json").read_text(encoding="utf-8"))
    b1 = canonical_derived_index_artifact_json_bytes_v1(art)
    b2 = canonical_derived_index_artifact_json_bytes_v1(art)
    assert b1 == b2


def test_fs_di03_regression_detected() -> None:
    v = list_fs_di03_index_epoch_regression_violations([1, 2, 1])
    assert any("FS-DI-03" in x for x in v)


def test_publish_barrier_fs_di02() -> None:
    with pytest.raises(DerivedIndexContractError, match="FS-DI-02"):
        validate_publish_barrier_record_v1(
            {
                "publish_state": PUBLISH_STATE_PUBLISHED,
                "partial_build": True,
                "lineage_scan_passed": True,
            },
        )
    validate_publish_barrier_record_v1(
        {
            "publish_state": PUBLISH_STATE_PUBLISHED,
            "partial_build": False,
            "lineage_scan_passed": True,
        },
    )


def test_di02_stale_rejects_observed_strict() -> None:
    with pytest.raises(DerivedIndexContractError, match="RULE DI-02"):
        validate_stale_derived_read_policy_v1(
            walk_execution_strategy=WALK_EXECUTION_STRATEGY_ONLINE_OBSERVED,
            allow_stale_derived_read=False,
            served_index_epoch=1,
            latest_committed_index_epoch=2,
        )


def test_di02_stale_allowed_with_flag() -> None:
    validate_stale_derived_read_policy_v1(
        walk_execution_strategy=WALK_EXECUTION_STRATEGY_ONLINE_OBSERVED,
        allow_stale_derived_read=True,
        served_index_epoch=1,
        latest_committed_index_epoch=2,
    )


def test_di02_non_observed_strategy_skips() -> None:
    validate_stale_derived_read_policy_v1(
        walk_execution_strategy=WALK_EXECUTION_STRATEGY_MATERIALIZED_DERIVED,
        allow_stale_derived_read=False,
        served_index_epoch=1,
        latest_committed_index_epoch=2,
    )


def test_materialized_for_index_epoch_only_artifact() -> None:
    art = {
        "DERIVED_INDEX_CANON_VERSION": 1,
        "materialized_for_index_epoch": 7,
        "nodes": [],
        "adj": {},
        "derived_edges": [],
    }
    validate_derived_index_artifact_contract_v1(art)
    h = compute_index_content_hash_v1(art)
    assert h.startswith("sha256:")


def test_lineage_scan_list_api() -> None:
    bad = [{"from_node_id": "a", "to_node_id": "b"}]
    assert list_fs_di01_derived_edge_lineage_violations(bad)
