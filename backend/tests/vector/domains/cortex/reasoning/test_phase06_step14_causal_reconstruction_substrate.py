"""P06-14 — Causal reconstruction substrate (Option A ``TCRECausalEdge_v1``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.ingestion.execution_reconstruction_contracts import DeterministicConfidenceSource
from vector.domains.cortex.reasoning.causal_reconstruction_substrate import (
    PHASE06_CAUSAL_RECONSTRUCTION_SUBSTRATE_RUNTIME_SCHEMA_VERSION,
    TCRE_CAUSAL_EDGE_REGISTRY_VERSION,
    TCRE_WEAK_COORDINATION_DERIVED_KINDS_V1,
    CausalReconstructionSubstrateError,
    primary_tcre_kind_for_coordination_edge_kind_v1,
    validate_cross_system_tcre_support_not_weak_only_v1,
    validate_tcre_causal_edge_v1_reconstruction_substrate,
    verify_gp06_crs01_coordination_to_tcre_primary_map_static,
    verify_gp06_crs02_reconstruction_requires_confidence_static,
    verify_gp06_crs03_cross_system_weak_only_guard_static,
    verify_gp06_crs04_option_a_rejects_coordination_edge_kind_key_static,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_CAUSAL_RECONSTRUCTION_SUBSTRATE_RUNTIME_SCHEMA_VERSION >= 1
    assert TCRE_CAUSAL_EDGE_REGISTRY_VERSION >= 1


def test_static_gates() -> None:
    assert verify_gp06_crs01_coordination_to_tcre_primary_map_static()["passed"] is True
    assert verify_gp06_crs02_reconstruction_requires_confidence_static()["passed"] is True
    assert verify_gp06_crs03_cross_system_weak_only_guard_static()["passed"] is True
    assert verify_gp06_crs04_option_a_rejects_coordination_edge_kind_key_static()["passed"] is True


def test_primary_map_escalation() -> None:
    assert primary_tcre_kind_for_coordination_edge_kind_v1("escalation_of") == "tcre_coordination_escalation"


def test_primary_map_unknown() -> None:
    with pytest.raises(CausalReconstructionSubstrateError, match="unknown CoordinationEdgeKind"):
        primary_tcre_kind_for_coordination_edge_kind_v1("not_a_coordination_kind")


def test_valid_reconstruction_edge() -> None:
    validate_tcre_causal_edge_v1_reconstruction_substrate(
        {
            "tcre_causal_edge_kind": "tcre_coordination_dependency",
            "underlying_coordination_edge_ids": ["coord-edge-9"],
            "derivation_rule_id": "TCRE_MAP_depends_on_v1",
            "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 42}],
            "confidence_source": DeterministicConfidenceSource.CONNECTOR_NATIVE_FIELD.value,
        }
    )


def test_sentinel_negative_signal_with_confidence() -> None:
    validate_tcre_causal_edge_v1_reconstruction_substrate(
        {
            "tcre_causal_edge_kind": "tcre_negative_signal",
            "underlying_coordination_edge_ids": ["__NO_COORDINATION_EDGE__"],
            "derivation_rule_id": "NEG_SIG_v1",
            "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 2}],
            "confidence_source": DeterministicConfidenceSource.EXPLICIT_RULE_ID.value,
        }
    )


def test_cross_system_intra_ok_with_weak_only() -> None:
    validate_cross_system_tcre_support_not_weak_only_v1(
        is_cross_system_causal=False,
        supporting_tcre_kinds=["tcre_coordination_temporal_order"],
    )


def test_cross_system_thread_plus_temporal_rejected() -> None:
    with pytest.raises(CausalReconstructionSubstrateError, match="sole"):
        validate_cross_system_tcre_support_not_weak_only_v1(
            is_cross_system_causal=True,
            supporting_tcre_kinds=[
                "tcre_coordination_thread_context",
                "tcre_coordination_temporal_order",
            ],
        )


def test_doctrine_files_exist() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p1 = root / "DOCS" / "cortex" / "reasoning" / "causal-reconstruction-doctrine.md"
        p2 = root / "DOCS" / "cortex" / "reasoning" / "tcre-causal-edge-registry-v1.md"
        if p1.is_file() and p2.is_file():
            t = p2.read_text(encoding="utf-8")
            assert "TCRECausalEdge_v1" in t
            assert "Option A" in t
            return
    pytest.fail("P06-14 doctrine files not found")


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.TCRE_CAUSAL_EDGE_REGISTRY_VERSION >= 1
    assert len(r.COORDINATION_EDGE_KIND_TO_TCRE_PRIMARY_V1) == 6
    assert "tcre_coordination_temporal_order" in r.TCRE_WEAK_COORDINATION_DERIVED_KINDS_V1
    assert callable(r.validate_tcre_causal_edge_v1_reconstruction_substrate)
