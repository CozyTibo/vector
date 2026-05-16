"""P06-13 — Causal interval closure (half-open chains + hop / breakpoint caps)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.causal_interval_closure import (
    PHASE06_CAUSAL_INTERVAL_CLOSURE_RUNTIME_SCHEMA_VERSION,
    CausalIntervalClosureError,
    canonical_sorted_tcre_causal_edge_ids_v1,
    validate_causal_influence_half_open_chain_v1,
    verify_gp06_cic01_default_policy_caps_static,
    verify_gp06_cic02_half_open_closure_oracle_static,
    verify_gp06_cic03_hop_cap_exceeded_static,
)
from vector.domains.cortex.reasoning.chronology_legality import load_default_reasoning_policy_pack


def _policy_minimal(
    *,
    max_hops: int = 12,
    max_bp: int = 64,
) -> dict:
    return {
        "caps": {
            "max_causal_hops_default": max_hops,
            "max_causal_hops_degraded": max_hops,
            "max_transitive_closure_hops": 0,
            "max_breakpoints_per_chain": max_bp,
            "max_tcre_edges_per_chain": 4096,
        },
        "degradation_thresholds": {"emit_cd_chron_on_any_chronology_non_strict": False},
    }


def test_runtime_schema_version() -> None:
    assert PHASE06_CAUSAL_INTERVAL_CLOSURE_RUNTIME_SCHEMA_VERSION >= 1


def test_static_gates() -> None:
    assert verify_gp06_cic01_default_policy_caps_static()["passed"] is True
    assert verify_gp06_cic02_half_open_closure_oracle_static()["passed"] is True
    assert verify_gp06_cic03_hop_cap_exceeded_static()["passed"] is True


def test_canonical_sorted_unique() -> None:
    assert canonical_sorted_tcre_causal_edge_ids_v1(("z", "a", "m")) == ["a", "m", "z"]


def test_canonical_sorted_rejects_duplicates() -> None:
    with pytest.raises(CausalIntervalClosureError, match="duplicate"):
        canonical_sorted_tcre_causal_edge_ids_v1(["a", "a"])


def test_valid_chain_default_pack() -> None:
    pack = load_default_reasoning_policy_pack()
    intervals = [
        {
            "tcre_causal_edge_id": "tcre_edge_2",
            "derivation_rule_id": "tcre_causal_influence_v1",
            "start_iso": "2025-06-01T00:00:00Z",
            "end_iso": "2025-06-02T00:00:00Z",
            "lineage": [{"anchor_id": "anch-1"}],
        },
        {
            "tcre_causal_edge_id": "tcre_edge_1",
            "derivation_rule_id": "tcre_causal_influence_v1",
            "start_iso": "2025-06-02T00:00:00Z",
            "end_iso": "2025-06-03T00:00:00Z",
            "lineage": [{"anchor_id": "anch-1"}],
        },
    ]
    out = validate_causal_influence_half_open_chain_v1(
        intervals,
        chronology_legality_class="chronology_strict",
        policy=pack,
        breakpoint_ids=[],
    )
    assert out["hop_count"] == 2
    assert out["sorted_tcre_causal_edge_ids"] == ["tcre_edge_1", "tcre_edge_2"]


def test_breakpoint_cap() -> None:
    policy = _policy_minimal(max_bp=1)
    one = [
        {
            "tcre_causal_edge_id": "e1",
            "derivation_rule_id": "tcre_causal_influence_v1",
            "start_iso": "2025-01-01T00:00:00Z",
            "end_iso": "2025-01-02T00:00:00Z",
            "lineage": [{"anchor_id": "a"}],
        },
    ]
    validate_causal_influence_half_open_chain_v1(
        one,
        chronology_legality_class="chronology_strict",
        policy=policy,
        breakpoint_ids=["bp1"],
    )
    with pytest.raises(CausalIntervalClosureError, match="breakpoint cap"):
        validate_causal_influence_half_open_chain_v1(
            one,
            chronology_legality_class="chronology_strict",
            policy=policy,
            breakpoint_ids=("bp1", "bp2"),
        )


def test_gap_in_chain_rejected() -> None:
    policy = _policy_minimal()
    bad = [
        {
            "tcre_causal_edge_id": "e1",
            "derivation_rule_id": "tcre_causal_influence_v1",
            "start_iso": "2025-01-01T00:00:00Z",
            "end_iso": "2025-01-02T00:00:00Z",
            "lineage": [{"anchor_id": "a"}],
        },
        {
            "tcre_causal_edge_id": "e2",
            "derivation_rule_id": "tcre_causal_influence_v1",
            "start_iso": "2025-01-03T00:00:00Z",
            "end_iso": "2025-01-04T00:00:00Z",
            "lineage": [{"anchor_id": "a"}],
        },
    ]
    with pytest.raises(CausalIntervalClosureError, match="half-open chain continuity"):
        validate_causal_influence_half_open_chain_v1(
            bad,
            chronology_legality_class="chronology_strict",
            policy=policy,
        )


def test_open_tail_allowed() -> None:
    policy = _policy_minimal()
    intervals = [
        {
            "tcre_causal_edge_id": "e1",
            "derivation_rule_id": "tcre_causal_influence_v1",
            "start_iso": "2025-01-01T00:00:00Z",
            "end_iso": "2025-01-02T00:00:00Z",
            "lineage": [{"anchor_id": "a"}],
        },
        {
            "tcre_causal_edge_id": "e2",
            "derivation_rule_id": "tcre_causal_influence_v1",
            "start_iso": "2025-01-02T00:00:00Z",
            "lineage": [{"anchor_id": "a"}],
        },
    ]
    validate_causal_influence_half_open_chain_v1(
        intervals,
        chronology_legality_class="chronology_strict",
        policy=policy,
    )


def test_doctrine_files_exist() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p1 = root / "DOCS" / "cortex" / "reasoning" / "deterministic-causal-chain-spec.md"
        p2 = root / "DOCS" / "cortex" / "reasoning" / "reasoning-policy-pack-v1.md"
        if p1.is_file() and p2.is_file():
            assert "max_causal_hops" in p2.read_text(encoding="utf-8")
            assert "causal_chain_id" in p1.read_text(encoding="utf-8")
            return
    pytest.fail("P06-13 doctrine files not found")


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.PHASE06_CAUSAL_INTERVAL_CLOSURE_RUNTIME_SCHEMA_VERSION >= 1
    assert callable(r.validate_causal_influence_half_open_chain_v1)
