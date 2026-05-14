"""P05-15 — walk execution strategy contract (**G-P05-EQUIV-01**, **G-P05-WES-01/02**)."""

from __future__ import annotations

import json

import pytest

from vector.domains.cortex.traversal.observed_vs_derived import (
    PROVENANCE_CLASS_DERIVED,
    WALK_EXECUTION_STRATEGY_HYBRID_PINNED,
    WALK_EXECUTION_STRATEGY_MATERIALIZED_DERIVED,
)
from vector.domains.cortex.traversal.walk_execution_strategy_contract import (
    WES_RUNTIME_SCHEMA_VERSION,
    WalkExecutionStrategyContractError,
    list_fs_wes03_forbidden_optimization_keys_under_hash_body_v1,
    octs_walk_execution_strategy_fixture_dir,
    validate_fast_path_equivalence_record_v1,
    validate_fs_wes01_materialized_requires_pinned_index_epoch_v1,
    validate_hybrid_policy_integer_threshold_for_strategy_v1,
    validate_materialized_adjacency_hop_receipt_v1,
    validate_temporal_anchor_extension_sorted_keys_v1,
    verify_gp05_equiv01_fast_path_online_equivalence_static,
    verify_gp05_wes01_strategy_affects_policy_hash_static,
    verify_gp05_wes03_forbidden_optimization_hash_body_scan_static,
)
from vector.domains.cortex.traversal.walk_policy import (
    WalkPolicyInvariantError,
    validate_walk_policy_for_request_v1,
)


def test_wes_runtime_schema_version() -> None:
    assert WES_RUNTIME_SCHEMA_VERSION >= 1


def test_verify_gp05_equiv01_static_passes() -> None:
    out = verify_gp05_equiv01_fast_path_online_equivalence_static()
    assert out["id"] == "G-P05-EQUIV-01"
    assert out["passed"] is True


def test_verify_gp05_wes01_static_passes() -> None:
    out = verify_gp05_wes01_strategy_affects_policy_hash_static()
    assert out["id"] == "G-P05-WES-01"
    assert out["passed"] is True


def test_verify_gp05_wes03_static_passes() -> None:
    out = verify_gp05_wes03_forbidden_optimization_hash_body_scan_static()
    assert out["id"] == "G-P05-WES-02"
    assert out["passed"] is True


def test_octs_fixture_dir() -> None:
    d = octs_walk_execution_strategy_fixture_dir()
    assert (d / "equiv_fast_path_online_match_v1.json").is_file()


def test_fs_wes01_materialized_without_pin() -> None:
    with pytest.raises(WalkExecutionStrategyContractError, match="FS-WES-01"):
        validate_fs_wes01_materialized_requires_pinned_index_epoch_v1(
            WALK_EXECUTION_STRATEGY_MATERIALIZED_DERIVED,
            {"tenant_id": "00000000-0000-4000-8000-000000000001"},
        )


def test_fs_wes01_extension_pinned_epoch() -> None:
    validate_fs_wes01_materialized_requires_pinned_index_epoch_v1(
        WALK_EXECUTION_STRATEGY_MATERIALIZED_DERIVED,
        {"extension": {"pinned_index_epoch": 7}},
    )


def test_hybrid_requires_integer_threshold() -> None:
    base = {
        "max_hops": 4,
        "hop_class_allowlist": ["org.handle_links_canonical"],
        "tie_break": ["fingerprint"],
    }
    with pytest.raises(WalkExecutionStrategyContractError, match="HYBRID_PINNED"):
        validate_hybrid_policy_integer_threshold_for_strategy_v1(
            WALK_EXECUTION_STRATEGY_HYBRID_PINNED,
            base,
        )
    validate_hybrid_policy_integer_threshold_for_strategy_v1(
        WALK_EXECUTION_STRATEGY_HYBRID_PINNED,
        {**base, "hybrid_switch_at_index_epoch": 3},
    )


def test_validate_walk_policy_hybrid_wiring() -> None:
    policy = {
        "max_hops": 4,
        "max_frontier": 8,
        "max_edges_visited": 100,
        "max_wall_ms": 50,
        "hop_class_allowlist": ["org.handle_links_canonical"],
        "tie_break": ["fingerprint"],
        "respect_validity": True,
        "hybrid_switch_at_index_epoch": 2,
    }
    validate_walk_policy_for_request_v1(
        policy,
        walk_execution_strategy=WALK_EXECUTION_STRATEGY_HYBRID_PINNED,
        exploration_mode=False,
        enforce_sync_caps=False,
    )
    with pytest.raises(WalkPolicyInvariantError, match="HYBRID_PINNED"):
        validate_walk_policy_for_request_v1(
            {k: v for k, v in policy.items() if k != "hybrid_switch_at_index_epoch"},
            walk_execution_strategy=WALK_EXECUTION_STRATEGY_HYBRID_PINNED,
            exploration_mode=False,
            enforce_sync_caps=False,
        )


def test_extension_sorted_keys() -> None:
    validate_temporal_anchor_extension_sorted_keys_v1({"pinned_index_epoch": 1})
    with pytest.raises(WalkExecutionStrategyContractError, match="sorted"):
        validate_temporal_anchor_extension_sorted_keys_v1(
            {"z_last": 1, "pinned_index_epoch": 0},
        )


def test_materialized_hop_requires_edge_id() -> None:
    with pytest.raises(WalkExecutionStrategyContractError, match="materialized_edge_record_id"):
        validate_materialized_adjacency_hop_receipt_v1(
            {
                "via_materialized_adjacency": True,
                "provenance_class": PROVENANCE_CLASS_DERIVED,
            },
        )
    validate_materialized_adjacency_hop_receipt_v1(
        {
            "via_materialized_adjacency": True,
            "provenance_class": PROVENANCE_CLASS_DERIVED,
            "materialized_edge_record_id": "row:derived_edge:01HZ",
        },
    )


def test_fs_wes03_scan() -> None:
    v = list_fs_wes03_forbidden_optimization_keys_under_hash_body_v1({"merged_hops": []})
    assert any("FS-WES-03" in x for x in v)


def test_fast_path_equivalence_good_fixture() -> None:
    d = octs_walk_execution_strategy_fixture_dir()
    raw = json.loads((d / "equiv_fast_path_online_match_v1.json").read_text(encoding="utf-8"))
    validate_fast_path_equivalence_record_v1(raw)
