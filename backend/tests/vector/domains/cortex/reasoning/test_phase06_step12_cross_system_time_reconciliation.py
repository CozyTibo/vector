"""P06-12 — Cross-system time reconciliation (``rank(S)``, policy min rank, chronology gates)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.ingestion.execution_reconstruction_contracts import IdentityLinkDerivation
from vector.domains.cortex.reasoning.chronology_legality import load_default_reasoning_policy_pack
from vector.domains.cortex.reasoning.cross_system_time_reconciliation import (
    CONSTITUTIONAL_CROSS_SYSTEM_CAUSAL_MIN_RANK_V1,
    CONTINUITY_BRIDGE_STRENGTHS_V1,
    PHASE06_CROSS_SYSTEM_TIME_RECONCILIATION_RUNTIME_SCHEMA_VERSION,
    CrossSystemTimeReconciliationError,
    continuity_bridge_strength_rank_v1,
    continuity_bridge_strictly_stronger_v1,
    cross_system_causal_effective_min_rank_v1,
    skew_flag_tuple_from_reasoning_snapshot_v1,
    validate_chronology_allows_strict_temporal_order_claim_v1,
    validate_cross_system_causal_continuity_requirements_v1,
    verify_gp06_xst01_rank_table_oracle_static,
    verify_gp06_xst02_default_policy_min_rank_static,
    verify_gp06_xst03_cross_caus_rank4_derivation_gate_static,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_CROSS_SYSTEM_TIME_RECONCILIATION_RUNTIME_SCHEMA_VERSION >= 1


def test_static_gates() -> None:
    assert verify_gp06_xst01_rank_table_oracle_static()["passed"] is True
    assert verify_gp06_xst02_default_policy_min_rank_static()["passed"] is True
    assert verify_gp06_xst03_cross_caus_rank4_derivation_gate_static()["passed"] is True


def test_rank_unknown_strength() -> None:
    with pytest.raises(CrossSystemTimeReconciliationError, match="continuity_bridge_strength"):
        continuity_bridge_strength_rank_v1("nope")


def test_strictly_stronger() -> None:
    assert continuity_bridge_strictly_stronger_v1("direct", "partial") is True
    assert continuity_bridge_strictly_stronger_v1("partial", "direct") is False


def test_same_origin_skips_cross_rule() -> None:
    pack = load_default_reasoning_policy_pack()
    validate_cross_system_causal_continuity_requirements_v1(
        connector_origin_left="linear",
        connector_origin_right="linear",
        continuity_bridge_strength="unverifiable",
        identity_link_derivation="anything",
        policy=pack,
    )


def test_cross_origin_fails_below_min_rank() -> None:
    pack = load_default_reasoning_policy_pack()
    with pytest.raises(CrossSystemTimeReconciliationError, match="CROSS-CAUS-1"):
        validate_cross_system_causal_continuity_requirements_v1(
            connector_origin_left="linear",
            connector_origin_right="slack",
            continuity_bridge_strength="weak",
            identity_link_derivation=IdentityLinkDerivation.EXPLICIT_LINKAGE.value,
            policy=pack,
        )


def test_cross_origin_authoritative_ok() -> None:
    pack = load_default_reasoning_policy_pack()
    validate_cross_system_causal_continuity_requirements_v1(
        connector_origin_left="linear",
        connector_origin_right="slack",
        continuity_bridge_strength="authoritative",
        identity_link_derivation=IdentityLinkDerivation.TEMPORAL_OVERLAP.value,
        policy=pack,
    )


def test_rank4_requires_allowed_derivation() -> None:
    policy = {"cross_system_causal_min_rank": 4}
    with pytest.raises(CrossSystemTimeReconciliationError, match="rank\\(S\\)==4"):
        validate_cross_system_causal_continuity_requirements_v1(
            connector_origin_left="a",
            connector_origin_right="b",
            continuity_bridge_strength="continuity_backed",
            identity_link_derivation=IdentityLinkDerivation.TEMPORAL_OVERLAP.value,
            policy=policy,
        )


def test_rank4_shared_execution_ok() -> None:
    policy = {"cross_system_causal_min_rank": 4}
    validate_cross_system_causal_continuity_requirements_v1(
        connector_origin_left="a",
        connector_origin_right="b",
        continuity_bridge_strength="continuity_backed",
        identity_link_derivation=IdentityLinkDerivation.SHARED_EXECUTION_REFERENCE.value,
        policy=policy,
    )


def test_policy_stricter_min_rank() -> None:
    policy = {"cross_system_causal_min_rank": 5}
    assert cross_system_causal_effective_min_rank_v1(policy) == 5
    with pytest.raises(CrossSystemTimeReconciliationError, match="CROSS-CAUS-1"):
        validate_cross_system_causal_continuity_requirements_v1(
            connector_origin_left="a",
            connector_origin_right="b",
            continuity_bridge_strength="continuity_backed",
            identity_link_derivation=IdentityLinkDerivation.EXPLICIT_LINKAGE.value,
            policy=policy,
        )
    validate_cross_system_causal_continuity_requirements_v1(
        connector_origin_left="a",
        connector_origin_right="b",
        continuity_bridge_strength="direct",
        identity_link_derivation=IdentityLinkDerivation.TEMPORAL_OVERLAP.value,
        policy=policy,
    )


def test_effective_min_constitutional_floor() -> None:
    assert cross_system_causal_effective_min_rank_v1({"cross_system_causal_min_rank": 2}) == 4


def test_skew_tuple_defaults_and_types() -> None:
    assert skew_flag_tuple_from_reasoning_snapshot_v1({}) == (False, False, False)
    assert skew_flag_tuple_from_reasoning_snapshot_v1(
        {"skew_detected": True, "late_arrival": False, "export_sequence_conflict": True}
    ) == (True, False, True)
    with pytest.raises(CrossSystemTimeReconciliationError, match="skew_detected"):
        skew_flag_tuple_from_reasoning_snapshot_v1({"skew_detected": "yes"})


def test_chronology_strict_gate() -> None:
    validate_chronology_allows_strict_temporal_order_claim_v1(
        "chronology_strict",
        asserts_strict_temporal_total_order=True,
    )
    with pytest.raises(CrossSystemTimeReconciliationError, match="strict temporal"):
        validate_chronology_allows_strict_temporal_order_claim_v1(
            "chronology_partial",
            asserts_strict_temporal_total_order=True,
        )


def test_doctrine_files_exist() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p1 = root / "DOCS" / "cortex" / "reasoning" / "cross-system-causal-continuity.md"
        p2 = root / "DOCS" / "cortex" / "reasoning" / "chronology-legality-law.md"
        if p1.is_file() and p2.is_file():
            assert "rank(S)" in p1.read_text(encoding="utf-8")
            assert "chronology_strict" in p2.read_text(encoding="utf-8")
            return
    pytest.fail("P06-12 doctrine files not found")


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.CONSTITUTIONAL_CROSS_SYSTEM_CAUSAL_MIN_RANK_V1 == 4
    assert len(r.CONTINUITY_BRIDGE_STRENGTHS_V1) == 6
    assert callable(r.validate_cross_system_causal_continuity_requirements_v1)
