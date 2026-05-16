"""P06-03 — Execution causality constraints (observed vs derived boundary)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.execution_causality_constraints import (
    CAUSAL_LEGALITY_CLASSES,
    EXECUTION_CAUSALITY_RUNTIME_SCHEMA_VERSION,
    TCRE_CAUSAL_EDGE_KINDS,
    ExecutionCausalityConstraintError,
    coordination_edge_kind_is_known,
    list_lrel_forbidden_keys_on_mapping,
    validate_causal_legality_class,
    validate_parent_artifact_ids_sorted_unique,
    validate_tcre_edge_v1_stub,
    verify_gp06_ecc01_causal_legality_enum_static,
    verify_gp06_ecc02_parent_artifact_ids_static,
    verify_gp06_ecc03_tcre_edge_shape_static,
)


def test_execution_causality_runtime_schema_version() -> None:
    assert EXECUTION_CAUSALITY_RUNTIME_SCHEMA_VERSION >= 1


def test_validate_causal_legality_class_accepts_enum() -> None:
    for v in CAUSAL_LEGALITY_CLASSES:
        validate_causal_legality_class(v)


def test_validate_causal_legality_class_rejects_unknown() -> None:
    with pytest.raises(ExecutionCausalityConstraintError, match="causal_legality_class"):
        validate_causal_legality_class("causal_magic_inference")


def test_parent_artifact_ids_sorted_unique() -> None:
    validate_parent_artifact_ids_sorted_unique(["01HZABC", "01HZDEF"])


def test_parent_artifact_ids_rejects_unsorted() -> None:
    with pytest.raises(ExecutionCausalityConstraintError, match="sorted"):
        validate_parent_artifact_ids_sorted_unique(["z", "a"])


def test_lrel_flags_score_suffix() -> None:
    hits = list_lrel_forbidden_keys_on_mapping({"utility_score": 1, "ok_field": 2})
    assert "utility_score" in hits


def test_coordination_edge_kind_is_known() -> None:
    assert coordination_edge_kind_is_known("escalation_of") is True
    assert coordination_edge_kind_is_known("magic_edge") is False


def test_tcre_edge_requires_derivation_rule_id() -> None:
    edge = {
        "tcre_causal_edge_kind": "tcre_coordination_block",
        "underlying_coordination_edge_ids": ["e1"],
        "derivation_rule_id": "",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 1}],
    }
    with pytest.raises(ExecutionCausalityConstraintError, match="derivation_rule_id"):
        validate_tcre_edge_v1_stub(edge)


def test_tcre_edge_parent_ids_optional_sorted() -> None:
    edge = {
        "tcre_causal_edge_kind": "tcre_coordination_dependency",
        "underlying_coordination_edge_ids": ["z9"],
        "derivation_rule_id": "RULE_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 3}],
        "parent_artifact_ids": ["p1", "p2"],
    }
    validate_tcre_edge_v1_stub(edge)


def test_tcre_edge_rejects_invalid_causal_legality_class_when_present() -> None:
    edge = {
        "tcre_causal_edge_kind": "tcre_coordination_handoff",
        "underlying_coordination_edge_ids": ["h1"],
        "derivation_rule_id": "RULE_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 9}],
        "causal_legality_class": "causal_magic_inference",
    }
    with pytest.raises(ExecutionCausalityConstraintError, match="causal_legality_class"):
        validate_tcre_edge_v1_stub(edge)


def test_tcre_edge_rejects_unsorted_underlying_ids() -> None:
    edge = {
        "tcre_causal_edge_kind": "tcre_coordination_handoff",
        "underlying_coordination_edge_ids": ["b", "a"],
        "derivation_rule_id": "RULE_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 1}],
    }
    with pytest.raises(ExecutionCausalityConstraintError, match="sorted"):
        validate_tcre_edge_v1_stub(edge)


def test_verify_gp06_ecc01_static_passes() -> None:
    out = verify_gp06_ecc01_causal_legality_enum_static()
    assert out["passed"] is True


def test_verify_gp06_ecc02_static_passes() -> None:
    out = verify_gp06_ecc02_parent_artifact_ids_static()
    assert out["passed"] is True


def test_verify_gp06_ecc03_static_passes() -> None:
    out = verify_gp06_ecc03_tcre_edge_shape_static()
    assert out["passed"] is True


def test_execution_causality_constraints_doctrine_contract() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p = root / "DOCS" / "cortex" / "reasoning" / "execution-causality-constraints.md"
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            assert "## 1. Allowed derivation sources" in text
            assert "## 2. Forbidden derivations" in text
            assert "## 3. Observed vs derived boundary" in text
            assert "## 4. Causal legality class" in text
            assert "causal_replay_equivalent" in text
            assert "## 5. Reliability / volatility firewall" in text
            return
    pytest.fail("execution-causality-constraints.md not found from test parents")


def test_tcre_registry_kinds_match_module_registry() -> None:
    """Drift guard: closed enum in code matches registry §3 rows (count + membership)."""
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        reg = root / "DOCS" / "cortex" / "reasoning" / "tcre-causal-edge-registry-v1.md"
        if reg.is_file():
            text = reg.read_text(encoding="utf-8")
            for k in TCRE_CAUSAL_EDGE_KINDS:
                assert f"`{k}`" in text, f"missing kind {k!r} in registry doc"
            assert len(TCRE_CAUSAL_EDGE_KINDS) == 10
            return
    pytest.fail("tcre-causal-edge-registry-v1.md not found")
