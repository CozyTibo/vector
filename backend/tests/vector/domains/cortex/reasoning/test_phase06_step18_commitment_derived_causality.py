"""P06-18 — Commitment-derived causality (``tcre_commitment_transition``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.commitment_derived_causality import (
    PHASE06_COMMITMENT_DERIVED_CAUSALITY_RUNTIME_SCHEMA_VERSION,
    TCRE_COMMITMENT_TRANSITION_DERIVATION_RULE_PREFIX_V1,
    TCRE_COMMITMENT_TRANSITION_KIND,
    CommitmentDerivedCausalityError,
    lineage_includes_commitment_contract_hop_v1,
    lineage_includes_raw_record_hop_v1,
    underlying_coordination_edge_ids_sentinel_only_v1,
    validate_tcre_causal_edge_v1_reconstruction_substrate_commitment_transition_v1,
    validate_tcre_commitment_transition_causality_v1,
    verify_gp06_cmt01_sentinel_requires_raw_and_commitment_hop_static,
    verify_gp06_cmt02_concrete_coordination_skips_extra_commitment_hop_static,
    verify_gp06_cmt03_bad_derivation_rule_prefix_rejected_static,
    verify_gp06_cmt04_wrong_kind_rejected_static,
    verify_gp06_cmt05_substrate_plus_commitment_law_static,
)
from vector.domains.cortex.reasoning.execution_causality_constraints import (
    NO_COORDINATION_EDGE_SENTINEL,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_COMMITMENT_DERIVED_CAUSALITY_RUNTIME_SCHEMA_VERSION >= 1


def test_static_gates() -> None:
    assert verify_gp06_cmt01_sentinel_requires_raw_and_commitment_hop_static()["passed"] is True
    cmt02 = verify_gp06_cmt02_concrete_coordination_skips_extra_commitment_hop_static()
    assert cmt02["passed"] is True
    assert verify_gp06_cmt03_bad_derivation_rule_prefix_rejected_static()["passed"] is True
    assert verify_gp06_cmt04_wrong_kind_rejected_static()["passed"] is True
    assert verify_gp06_cmt05_substrate_plus_commitment_law_static()["passed"] is True


def test_prefix_constant() -> None:
    assert TCRE_COMMITMENT_TRANSITION_DERIVATION_RULE_PREFIX_V1 == "TCRE_MAP_commitment_"


def test_sentinel_only_predicate() -> None:
    assert underlying_coordination_edge_ids_sentinel_only_v1(
        {"underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL]}
    )
    assert not underlying_coordination_edge_ids_sentinel_only_v1(
        {"underlying_coordination_edge_ids": ["e1"]}
    )


def test_lineage_predicates() -> None:
    assert lineage_includes_raw_record_hop_v1([{"hop_kind": "raw_record", "raw_record_id": 1}])
    assert not lineage_includes_raw_record_hop_v1([{"hop_kind": "raw_record"}])
    assert lineage_includes_commitment_contract_hop_v1([{"commitment_id": "x"}])
    assert not lineage_includes_commitment_contract_hop_v1(
        [{"hop_kind": "raw_record", "raw_record_id": 1}]
    )


def test_sentinel_rejects_raw_without_commitment_id() -> None:
    edge = {
        "tcre_causal_edge_kind": TCRE_COMMITMENT_TRANSITION_KIND,
        "underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL],
        "derivation_rule_id": "TCRE_MAP_commitment_lifecycle_v1",
        "evidence_lineage": [
            {"hop_kind": "raw_record", "raw_record_id": 1},
            {"hop_kind": "cross_link"},
        ],
    }
    with pytest.raises(CommitmentDerivedCausalityError, match="commitment_id"):
        validate_tcre_commitment_transition_causality_v1(edge)


def test_combined_substrate_rejects_missing_confidence() -> None:
    edge = {
        "tcre_causal_edge_kind": TCRE_COMMITMENT_TRANSITION_KIND,
        "underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL],
        "derivation_rule_id": "TCRE_MAP_commitment_transition_v1",
        "evidence_lineage": [
            {"hop_kind": "raw_record", "raw_record_id": 1},
            {"commitment_id": "c1"},
        ],
    }
    with pytest.raises(CommitmentDerivedCausalityError, match="confidence_source"):
        validate_tcre_causal_edge_v1_reconstruction_substrate_commitment_transition_v1(edge)


def test_doctrine_files_exist() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p = root / "DOCS" / "cortex" / "reasoning" / "tcre-causal-edge-registry-v1.md"
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            assert "tcre_commitment_transition" in text
            assert "CommitmentLifecycle" in text
            cr = root / "DOCS" / "cortex" / "reasoning" / "causal-reconstruction-doctrine.md"
            assert cr.is_file()
            assert "TCRE" in cr.read_text(encoding="utf-8")
            return
    pytest.fail("P06-18 doctrine files not found")


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.PHASE06_COMMITMENT_DERIVED_CAUSALITY_RUNTIME_SCHEMA_VERSION >= 1
    assert r.TCRE_COMMITMENT_TRANSITION_KIND == "tcre_commitment_transition"
    assert callable(r.validate_tcre_commitment_transition_causality_v1)
    assert verify_gp06_cmt01_sentinel_requires_raw_and_commitment_hop_static()["passed"] is True
