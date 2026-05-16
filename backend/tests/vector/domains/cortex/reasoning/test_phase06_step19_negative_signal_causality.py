"""P06-19 — Negative-signal causality (``tcre_negative_signal`` + silence law)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.ingestion.execution_reconstruction_contracts import NegativeSignalKind
from vector.domains.cortex.reasoning.execution_causality_constraints import (
    NO_COORDINATION_EDGE_SENTINEL,
)
from vector.domains.cortex.reasoning.negative_signal_causality import (
    NEGATIVE_SIGNAL_KINDS_SILENCE_CAUSALITY_LAWFUL_V1,
    PHASE06_NEGATIVE_SIGNAL_CAUSALITY_RUNTIME_SCHEMA_VERSION,
    TCRE_NEGATIVE_SIGNAL_DERIVATION_RULE_PREFIX_V1,
    TCRE_NEGATIVE_SIGNAL_KIND,
    NegativeSignalCausalityError,
    lineage_includes_negative_signal_contract_hop_v1,
    lineage_includes_raw_record_hop_negative_v1,
    resolve_negative_signal_kind_v1,
    underlying_coordination_edge_ids_sentinel_only_negative_v1,
    validate_tcre_causal_edge_v1_reconstruction_substrate_negative_signal_v1,
    validate_tcre_negative_signal_causality_v1,
    verify_gp06_neg01_sentinel_requires_raw_and_signal_hop_static,
    verify_gp06_neg02_concrete_coordination_skips_extra_signal_hop_static,
    verify_gp06_neg03_bad_derivation_rule_prefix_rejected_static,
    verify_gp06_neg04_unlawful_negative_signal_kind_rejected_static,
    verify_gp06_neg05_substrate_plus_negative_signal_law_static,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_NEGATIVE_SIGNAL_CAUSALITY_RUNTIME_SCHEMA_VERSION >= 1


def test_static_gates() -> None:
    assert verify_gp06_neg01_sentinel_requires_raw_and_signal_hop_static()["passed"] is True
    assert verify_gp06_neg02_concrete_coordination_skips_extra_signal_hop_static()["passed"] is True
    assert verify_gp06_neg03_bad_derivation_rule_prefix_rejected_static()["passed"] is True
    assert verify_gp06_neg04_unlawful_negative_signal_kind_rejected_static()["passed"] is True
    assert verify_gp06_neg05_substrate_plus_negative_signal_law_static()["passed"] is True


def test_prefix_constant() -> None:
    assert TCRE_NEGATIVE_SIGNAL_DERIVATION_RULE_PREFIX_V1 == "TCRE_MAP_negative_signal_"


def test_silence_law_allowlist() -> None:
    lawful = NEGATIVE_SIGNAL_KINDS_SILENCE_CAUSALITY_LAWFUL_V1
    assert NegativeSignalKind.STALE_BLOCKER.value not in lawful
    assert NegativeSignalKind.UNANSWERED_REQUEST.value in lawful


def test_sentinel_only_predicate() -> None:
    assert underlying_coordination_edge_ids_sentinel_only_negative_v1(
        {"underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL]}
    )
    assert not underlying_coordination_edge_ids_sentinel_only_negative_v1(
        {"underlying_coordination_edge_ids": ["e1"]}
    )


def test_lineage_predicates() -> None:
    assert lineage_includes_raw_record_hop_negative_v1(
        [{"hop_kind": "raw_record", "raw_record_id": 1}]
    )
    assert not lineage_includes_raw_record_hop_negative_v1([{"hop_kind": "raw_record"}])
    assert lineage_includes_negative_signal_contract_hop_v1([{"signal_id": "x"}])
    assert not lineage_includes_negative_signal_contract_hop_v1(
        [{"hop_kind": "raw_record", "raw_record_id": 1}]
    )


def test_resolve_kind_from_edge() -> None:
    edge = {"source_negative_signal_kind": NegativeSignalKind.REPEATED_FOLLOW_UP.value}
    assert resolve_negative_signal_kind_v1(edge, negative_signal_kind=None) == (
        NegativeSignalKind.REPEATED_FOLLOW_UP.value
    )


def test_sentinel_rejects_raw_without_signal_id() -> None:
    edge = {
        "tcre_causal_edge_kind": TCRE_NEGATIVE_SIGNAL_KIND,
        "underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL],
        "derivation_rule_id": "TCRE_MAP_negative_signal_v1",
        "evidence_lineage": [
            {"hop_kind": "raw_record", "raw_record_id": 1},
            {"hop_kind": "cross_link"},
        ],
        "negative_signal_kind": NegativeSignalKind.UNANSWERED_REQUEST.value,
    }
    with pytest.raises(NegativeSignalCausalityError, match="signal_id"):
        validate_tcre_negative_signal_causality_v1(edge)


def test_combined_substrate_rejects_missing_confidence() -> None:
    edge = {
        "tcre_causal_edge_kind": TCRE_NEGATIVE_SIGNAL_KIND,
        "underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL],
        "derivation_rule_id": "TCRE_MAP_negative_signal_v1",
        "evidence_lineage": [
            {"hop_kind": "raw_record", "raw_record_id": 1},
            {"signal_id": "s1"},
        ],
        "negative_signal_kind": NegativeSignalKind.MISSING_ACKNOWLEDGMENT.value,
    }
    with pytest.raises(NegativeSignalCausalityError, match="confidence_source"):
        validate_tcre_causal_edge_v1_reconstruction_substrate_negative_signal_v1(edge)


def test_doctrine_files_exist() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        reg = root / "DOCS" / "cortex" / "reasoning" / "tcre-causal-edge-registry-v1.md"
        if reg.is_file():
            text = reg.read_text(encoding="utf-8")
            assert "tcre_negative_signal" in text
            silence = root / "DOCS" / "cortex" / "reasoning" / "silence-causality-law.md"
            assert silence.is_file()
            assert "NegativeSignalKind" in silence.read_text(encoding="utf-8")
            cr = root / "DOCS" / "cortex" / "reasoning" / "causal-reconstruction-doctrine.md"
            assert cr.is_file()
            assert "TCRE" in cr.read_text(encoding="utf-8")
            return
    pytest.fail("P06-19 doctrine files not found")


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.PHASE06_NEGATIVE_SIGNAL_CAUSALITY_RUNTIME_SCHEMA_VERSION >= 1
    assert r.TCRE_NEGATIVE_SIGNAL_KIND == "tcre_negative_signal"
    assert callable(r.validate_tcre_negative_signal_causality_v1)
    assert verify_gp06_neg01_sentinel_requires_raw_and_signal_hop_static()["passed"] is True
