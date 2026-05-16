"""P06-16 — Escalation / dependency / blocker propagation (policy merge tables)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.causal_propagation_policy import (
    PHASE06_CAUSAL_PROPAGATION_POLICY_RUNTIME_SCHEMA_VERSION,
    PROPAGATION_RULE_TABLE_V1_KEY,
    CausalPropagationPolicyError,
    max_underlying_coordination_edges_for_tcre_kind_v1,
    validate_merge_rules_coordination_edges_v1,
    validate_propagation_rule_table_v1_when_present,
    validate_tcre_edge_v1_stub_with_propagation_policy_v1,
    validate_underlying_coordination_edge_ids_propagation_v1,
    verify_gp06_edp01_default_pack_merge_rules_static,
    verify_gp06_edp02_merge_cap_multi_id_oracle_static,
    verify_gp06_edp03_default_stub_conflict_with_multi_id_resolved_static,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_CAUSAL_PROPAGATION_POLICY_RUNTIME_SCHEMA_VERSION >= 1


def test_static_gates() -> None:
    assert verify_gp06_edp01_default_pack_merge_rules_static()["passed"] is True
    assert verify_gp06_edp02_merge_cap_multi_id_oracle_static()["passed"] is True
    assert verify_gp06_edp03_default_stub_conflict_with_multi_id_resolved_static()["passed"] is True


def test_merge_rules_missing_raises() -> None:
    with pytest.raises(CausalPropagationPolicyError, match="merge_rules_coordination_edges must be present"):
        validate_merge_rules_coordination_edges_v1({})


def test_merge_rules_not_list_raises() -> None:
    with pytest.raises(CausalPropagationPolicyError, match="must be a list"):
        validate_merge_rules_coordination_edges_v1({"merge_rules_coordination_edges": {}})


def test_merge_rules_invalid_kind_raises() -> None:
    policy = {
        "merge_rules_coordination_edges": [
            {
                "merge_rule_id": "m1",
                "allowed_tcre_causal_edge_kind": "not_a_tcre_kind",
                "max_underlying_ids": 1,
            }
        ]
    }
    with pytest.raises(CausalPropagationPolicyError, match="allowed_tcre_causal_edge_kind"):
        validate_merge_rules_coordination_edges_v1(policy)


def test_merge_rules_duplicate_id_raises() -> None:
    row = {
        "merge_rule_id": "dup",
        "allowed_tcre_causal_edge_kind": "tcre_coordination_escalation",
        "max_underlying_ids": 2,
    }
    policy = {"merge_rules_coordination_edges": [row, dict(row)]}
    with pytest.raises(CausalPropagationPolicyError, match="duplicate merge_rule_id"):
        validate_merge_rules_coordination_edges_v1(policy)


def test_merge_rules_max_underlying_ids_bool_rejected() -> None:
    policy = {
        "merge_rules_coordination_edges": [
            {
                "merge_rule_id": "b1",
                "allowed_tcre_causal_edge_kind": "tcre_coordination_dependency",
                "max_underlying_ids": True,  # type: ignore[dict-item]
            }
        ]
    }
    with pytest.raises(CausalPropagationPolicyError, match="max_underlying_ids"):
        validate_merge_rules_coordination_edges_v1(policy)


def test_max_cap_is_max_over_matching_rows() -> None:
    policy = {
        "merge_rules_coordination_edges": [
            {
                "merge_rule_id": "r1",
                "allowed_tcre_causal_edge_kind": "tcre_coordination_escalation",
                "max_underlying_ids": 2,
            },
            {
                "merge_rule_id": "r2",
                "allowed_tcre_causal_edge_kind": "tcre_coordination_escalation",
                "max_underlying_ids": 5,
            },
        ]
    }
    assert max_underlying_coordination_edges_for_tcre_kind_v1("tcre_coordination_escalation", policy) == 5


def test_default_cap_one_when_no_row_matches() -> None:
    policy: dict[str, list[object]] = {"merge_rules_coordination_edges": []}
    assert max_underlying_coordination_edges_for_tcre_kind_v1("tcre_coordination_escalation", policy) == 1


def test_underlying_ids_exceeds_policy_cap() -> None:
    policy = {
        "merge_rules_coordination_edges": [
            {
                "merge_rule_id": "one",
                "allowed_tcre_causal_edge_kind": "tcre_coordination_escalation",
                "max_underlying_ids": 1,
            }
        ]
    }
    with pytest.raises(CausalPropagationPolicyError, match="exceeds policy max"):
        validate_underlying_coordination_edge_ids_propagation_v1(
            "tcre_coordination_escalation",
            ["a", "b"],
            policy,
        )


def test_propagation_rule_table_duplicate_raises() -> None:
    policy = {
        "merge_rules_coordination_edges": [],
        PROPAGATION_RULE_TABLE_V1_KEY: [
            {"propagation_rule_id": "p1"},
            {"propagation_rule_id": "p1"},
        ],
    }
    with pytest.raises(CausalPropagationPolicyError, match="duplicate propagation_rule_id"):
        validate_propagation_rule_table_v1_when_present(policy)


def test_propagation_rule_table_row_must_be_mapping() -> None:
    policy = {
        "merge_rules_coordination_edges": [],
        PROPAGATION_RULE_TABLE_V1_KEY: ["not-a-mapping"],
    }
    with pytest.raises(CausalPropagationPolicyError, match="must be a mapping"):
        validate_propagation_rule_table_v1_when_present(policy)


def test_combined_validator_rejects_invalid_stub_even_with_policy() -> None:
    policy = {
        "merge_rules_coordination_edges": [
            {
                "merge_rule_id": "m",
                "allowed_tcre_causal_edge_kind": "tcre_coordination_dependency",
                "max_underlying_ids": 2,
            }
        ]
    }
    edge = {
        "tcre_causal_edge_kind": "tcre_coordination_dependency",
        "underlying_coordination_edge_ids": ["c1", "c2"],
        "derivation_rule_id": "TCRE_MAP_depends_on_v1",
        "evidence_lineage": "not-a-list",
    }
    with pytest.raises(CausalPropagationPolicyError, match="evidence_lineage"):
        validate_tcre_edge_v1_stub_with_propagation_policy_v1(edge, policy)


def test_doctrine_files_exist() -> None:
    start = Path(__file__).resolve()
    names = (
        "causal-reconstruction-doctrine.md",
        "execution-causality-constraints.md",
        "reasoning-policy-pack-v1.md",
    )
    for root in [start, *start.parents]:
        base = root / "DOCS" / "cortex" / "reasoning"
        if not (base / names[0]).is_file():
            continue
        for n in names:
            text = (base / n).read_text(encoding="utf-8")
            assert len(text) > 200
        assert "merge_rules_coordination_edges" in (base / "reasoning-policy-pack-v1.md").read_text(
            encoding="utf-8"
        )
        return
    pytest.fail("reasoning doctrine files for P06-16 not found")


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.PHASE06_CAUSAL_PROPAGATION_POLICY_RUNTIME_SCHEMA_VERSION >= 1
    assert r.PROPAGATION_RULE_TABLE_V1_KEY == "propagation_rule_table_v1"
    assert callable(r.validate_merge_rules_coordination_edges_v1)
    assert callable(r.validate_tcre_edge_v1_stub_with_propagation_policy_v1)
    assert verify_gp06_edp01_default_pack_merge_rules_static()["passed"] is True
