"""P06-20 — Causal legality class closed enum (``execution-causality-constraints`` §4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.execution_causality_constraints import (
    CAUSAL_LEGALITY_CLASSES,
    CAUSAL_LEGALITY_ENUM_VERSION_V1,
    EXECUTION_CAUSALITY_RUNTIME_SCHEMA_VERSION,
    ExecutionCausalityConstraintError,
    validate_causal_legality_class,
    validate_tcre_edge_v1_stub,
    verify_gp06_clc01_literal_table_oracle_static,
    verify_gp06_clc02_tcre_stub_accepts_each_legal_literal_static,
    verify_gp06_clc03_tcre_stub_rejects_unknown_causal_legality_static,
    verify_gp06_clc04_tcre_stub_omits_causal_legality_class_static,
)


def test_causal_legality_enum_version() -> None:
    assert CAUSAL_LEGALITY_ENUM_VERSION_V1 >= 1


def test_execution_causality_runtime_schema_bumped_for_stub_legality() -> None:
    assert EXECUTION_CAUSALITY_RUNTIME_SCHEMA_VERSION >= 2


def test_static_gates() -> None:
    assert verify_gp06_clc01_literal_table_oracle_static()["passed"] is True
    assert verify_gp06_clc02_tcre_stub_accepts_each_legal_literal_static()["passed"] is True
    assert verify_gp06_clc03_tcre_stub_rejects_unknown_causal_legality_static()["passed"] is True
    assert verify_gp06_clc04_tcre_stub_omits_causal_legality_class_static()["passed"] is True


def test_validate_each_literal() -> None:
    for v in CAUSAL_LEGALITY_CLASSES:
        validate_causal_legality_class(v)


def test_tcre_stub_with_valid_causal_legality_class() -> None:
    edge = {
        "tcre_causal_edge_kind": "tcre_coordination_escalation",
        "underlying_coordination_edge_ids": ["e1"],
        "derivation_rule_id": "TCRE_MAP_escalation_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 1}],
        "causal_legality_class": "causal_replay_degraded",
    }
    validate_tcre_edge_v1_stub(edge)


def test_tcre_stub_rejects_invalid_causal_legality_class() -> None:
    edge = {
        "tcre_causal_edge_kind": "tcre_coordination_block",
        "underlying_coordination_edge_ids": ["e2"],
        "derivation_rule_id": "TCRE_MAP_block_v1",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 2}],
        "causal_legality_class": "causal_magic_inference",
    }
    with pytest.raises(ExecutionCausalityConstraintError, match="causal_legality_class"):
        validate_tcre_edge_v1_stub(edge)


def test_doctrine_section_four_table() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p = root / "DOCS" / "cortex" / "reasoning" / "execution-causality-constraints.md"
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            assert "## 4. Causal legality class" in text
            for row in (
                "causal_replay_equivalent",
                "causal_replay_degraded",
                "causal_chronology_blocked",
                "causal_ambiguous_partitioned",
                "causal_forbidden_substrate",
                "causal_unverifiable",
            ):
                assert f"`{row}`" in text
            return
    pytest.fail("execution-causality-constraints.md not found")


def test_registry_mentions_causal_legality_class() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        reg = root / "DOCS" / "cortex" / "reasoning" / "tcre-causal-edge-registry-v1.md"
        if reg.is_file():
            assert "causal_legality_class" in reg.read_text(encoding="utf-8")
            return
    pytest.fail("tcre-causal-edge-registry-v1.md not found")


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.CAUSAL_LEGALITY_ENUM_VERSION_V1 >= 1
    assert callable(r.validate_causal_legality_class)
    assert verify_gp06_clc01_literal_table_oracle_static()["passed"] is True
