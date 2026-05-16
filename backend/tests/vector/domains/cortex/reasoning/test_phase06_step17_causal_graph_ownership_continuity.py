"""P06-17 — Ownership continuity in causal graphs (authoritative org links + coordination ids)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.causal_graph_ownership_continuity import (
    PHASE06_CAUSAL_GRAPH_OWNERSHIP_CONTINUITY_RUNTIME_SCHEMA_VERSION,
    CausalGraphOwnershipContinuityError,
    tcre_edge_cites_concrete_coordination_edge_ids_v1,
    validate_tcre_causal_edge_v1_reconstruction_substrate_with_ownership_v1,
    validate_tcre_causal_graph_ownership_continuity_v1,
    verify_gp06_own01_concrete_ids_require_authoritative_org_support_static,
    verify_gp06_own02_sentinel_path_skips_org_link_support_static,
    verify_gp06_own03_non_authoritative_org_support_rejected_static,
    verify_gp06_own04_substrate_plus_ownership_combined_entry_static,
)
from vector.domains.cortex.reasoning.execution_causality_constraints import (
    NO_COORDINATION_EDGE_SENTINEL,
)
from vector.domains.cortex.reasoning.organizational_continuity_reasoning import (
    AMB_BRIDGE_WEAK,
    AMB_NONE,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_CAUSAL_GRAPH_OWNERSHIP_CONTINUITY_RUNTIME_SCHEMA_VERSION >= 1


def test_static_gates() -> None:
    assert (
        verify_gp06_own01_concrete_ids_require_authoritative_org_support_static()["passed"] is True
    )
    assert verify_gp06_own02_sentinel_path_skips_org_link_support_static()["passed"] is True
    assert verify_gp06_own03_non_authoritative_org_support_rejected_static()["passed"] is True
    assert verify_gp06_own04_substrate_plus_ownership_combined_entry_static()["passed"] is True


def test_cites_concrete_coordination_ids() -> None:
    assert tcre_edge_cites_concrete_coordination_edge_ids_v1(
        {"underlying_coordination_edge_ids": ["a"]}
    )
    assert tcre_edge_cites_concrete_coordination_edge_ids_v1(
        {"underlying_coordination_edge_ids": ["a", "b"]}
    )
    assert not tcre_edge_cites_concrete_coordination_edge_ids_v1(
        {"underlying_coordination_edge_ids": [NO_COORDINATION_EDGE_SENTINEL]}
    )
    assert not tcre_edge_cites_concrete_coordination_edge_ids_v1(
        {"underlying_coordination_edge_ids": "x"}
    )


def test_lineage_required_by_default() -> None:
    edge = {
        "tcre_causal_edge_kind": "tcre_coordination_dependency",
        "underlying_coordination_edge_ids": ["z1"],
        "derivation_rule_id": "r",
        "evidence_lineage": [],
    }
    with pytest.raises(CausalGraphOwnershipContinuityError, match="evidence_lineage"):
        validate_tcre_causal_graph_ownership_continuity_v1(
            edge,
            org_link_support={"link_authority": "authoritative", "temporal_validity_ok": True},
        )


def test_sole_candidate_wrapped() -> None:
    edge = {
        "tcre_causal_edge_kind": "tcre_coordination_dependency",
        "underlying_coordination_edge_ids": ["z1"],
        "derivation_rule_id": "r",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 1}],
    }
    with pytest.raises(CausalGraphOwnershipContinuityError, match="BRIDGE"):
        validate_tcre_causal_graph_ownership_continuity_v1(
            edge,
            org_link_support={"link_authority": "authoritative", "temporal_validity_ok": True},
            sole_support_bundle={"sole_support_kind": "candidate", "ambiguity_class_id": AMB_NONE},
        )


def test_sole_candidate_allowed_with_bridge_weak() -> None:
    edge = {
        "tcre_causal_edge_kind": "tcre_coordination_dependency",
        "underlying_coordination_edge_ids": ["z1"],
        "derivation_rule_id": "r",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 1}],
    }
    validate_tcre_causal_graph_ownership_continuity_v1(
        edge,
        org_link_support={"link_authority": "authoritative", "temporal_validity_ok": True},
        sole_support_bundle={
            "sole_support_kind": "candidate",
            "ambiguity_class_id": AMB_BRIDGE_WEAK,
        },
    )


def test_combined_rejects_bad_substrate_before_ownership() -> None:
    edge = {
        "tcre_causal_edge_kind": "tcre_coordination_dependency",
        "underlying_coordination_edge_ids": ["z1"],
        "derivation_rule_id": "r",
        "evidence_lineage": [{"hop_kind": "raw_record", "raw_record_id": 1}],
        # missing confidence_source
    }
    with pytest.raises(CausalGraphOwnershipContinuityError, match="confidence_source"):
        validate_tcre_causal_edge_v1_reconstruction_substrate_with_ownership_v1(
            edge,
            org_link_support={"link_authority": "authoritative", "temporal_validity_ok": True},
        )


def test_doctrine_files_exist() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p = root / "DOCS" / "cortex" / "reasoning" / "organizational-continuity-reasoning.md"
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            assert "Authoritative links" in text
            reg = root / "DOCS" / "cortex" / "reasoning" / "tcre-causal-edge-registry-v1.md"
            assert reg.is_file()
            assert "underlying_coordination_edge_ids" in reg.read_text(encoding="utf-8")
            return
    pytest.fail("P06-17 doctrine files not found")


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.PHASE06_CAUSAL_GRAPH_OWNERSHIP_CONTINUITY_RUNTIME_SCHEMA_VERSION >= 1
    assert callable(r.validate_tcre_causal_graph_ownership_continuity_v1)
    assert (
        verify_gp06_own01_concrete_ids_require_authoritative_org_support_static()["passed"] is True
    )
