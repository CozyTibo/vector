"""P06-11 — Chronology degradation propagation (CD‑CHRON + corpus + policy caps)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.chronology_degradation_propagation import (
    CD_CHRON,
    CD_REPLAY,
    CANONICAL_DEGRADATION_CODES,
    PHASE06_CHRONOLOGY_DEGRADATION_RUNTIME_SCHEMA_VERSION,
    ChronologyDegradationPropagationError,
    degradation_coarse_tag_v1,
    degradation_receipt_entry_v1,
    effective_max_causal_hops_v1,
    list_cd_chron_from_chronology_legality_v1,
    normalize_degradation_corpus_token_v1,
    normalize_expected_degradation_classes_corpus_v1,
    sort_cd_codes_deg_mon_1_display_v1,
    sort_degradation_receipt_entries_v1,
    validate_degradation_multiset_monotonic_extension_v1,
    validate_policy_caps_g_p06_pol01_v1,
    verify_gp06_deg01_corpus_alias_registry_static,
    verify_gp06_deg02_severity_sort_oracle_static,
    verify_gp06_deg03_default_policy_caps_static,
)
from vector.domains.cortex.reasoning.chronology_legality import load_default_reasoning_policy_pack


def test_runtime_schema_version() -> None:
    assert PHASE06_CHRONOLOGY_DEGRADATION_RUNTIME_SCHEMA_VERSION >= 1


def test_verify_static_gates() -> None:
    assert verify_gp06_deg01_corpus_alias_registry_static()["passed"] is True
    assert verify_gp06_deg02_severity_sort_oracle_static()["passed"] is True
    assert verify_gp06_deg03_default_policy_caps_static()["passed"] is True


def test_normalize_aliases_to_canonical() -> None:
    assert normalize_degradation_corpus_token_v1("replay_skew") == normalize_degradation_corpus_token_v1(
        "CD-REPLAY"
    )
    assert normalize_degradation_corpus_token_v1("chronology_cap_applied") == CD_CHRON


def test_unknown_corpus_token_fails() -> None:
    with pytest.raises(ChronologyDegradationPropagationError, match="unknown"):
        normalize_degradation_corpus_token_v1("not_a_degradation_code")


def test_normalize_expected_degradation_classes_sorted_unique() -> None:
    got = normalize_expected_degradation_classes_corpus_v1(["replay_skew", "CD-CHRON", "replay_skew"])
    assert got == sorted({normalize_degradation_corpus_token_v1("replay_skew"), CD_CHRON})


def test_list_cd_chron_default_pack_partial() -> None:
    pack = load_default_reasoning_policy_pack()
    assert list_cd_chron_from_chronology_legality_v1(
        chronology_legality_class="chronology_partial",
        policy=pack,
    ) == [CD_CHRON]


def test_list_cd_chron_strict_empty() -> None:
    pack = load_default_reasoning_policy_pack()
    assert list_cd_chron_from_chronology_legality_v1(
        chronology_legality_class="chronology_strict",
        policy=pack,
    ) == []


def test_effective_max_causal_hops_degraded_band() -> None:
    pack = load_default_reasoning_policy_pack()
    assert effective_max_causal_hops_v1(chronology_legality_class="chronology_partial", policy=pack) == 4
    assert effective_max_causal_hops_v1(chronology_legality_class="chronology_strict", policy=pack) == 12


def test_policy_caps_rejects_degraded_gt_default() -> None:
    bad = {
        "caps": {
            "max_causal_hops_default": 4,
            "max_causal_hops_degraded": 12,
            "max_transitive_closure_hops": 0,
            "max_breakpoints_per_chain": 1,
            "max_tcre_edges_per_chain": 1,
        }
    }
    with pytest.raises(ChronologyDegradationPropagationError, match="POL-01"):
        validate_policy_caps_g_p06_pol01_v1(bad)


def test_monotonic_multiset() -> None:
    validate_degradation_multiset_monotonic_extension_v1([CD_CHRON], [CD_CHRON, CD_REPLAY])
    with pytest.raises(ChronologyDegradationPropagationError, match="regression"):
        validate_degradation_multiset_monotonic_extension_v1([CD_CHRON, CD_REPLAY], [CD_CHRON])


def test_degradation_receipt_sort() -> None:
    e1 = degradation_receipt_entry_v1(
        code="CD-REPLAY",
        rule_id="r2",
        upstream_artifact_ids_sorted=["b", "a"],
        before_hash="h1",
    )
    e2 = degradation_receipt_entry_v1(
        code=CD_CHRON,
        rule_id="r1",
        upstream_artifact_ids_sorted=["x"],
        before_hash="h0",
    )
    rows = sort_degradation_receipt_entries_v1([e1, e2])
    assert rows[0]["code"] == CD_CHRON and rows[1]["code"] == normalize_degradation_corpus_token_v1("CD-REPLAY")


def test_degradation_coarse_tag() -> None:
    assert degradation_coarse_tag_v1([]) == "none"
    assert degradation_coarse_tag_v1([CD_CHRON]) == "none"
    assert degradation_coarse_tag_v1([CD_CHRON, CD_REPLAY]) == "composite"


def test_sort_display_severity() -> None:
    out = sort_cd_codes_deg_mon_1_display_v1([CD_CHRON, CD_REPLAY])
    assert out[0] == CD_REPLAY


def test_doctrine_files_exist() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p1 = root / "DOCS" / "cortex" / "reasoning" / "causal-degradation-spec.md"
        p2 = root / "DOCS" / "cortex" / "reasoning" / "reasoning-policy-pack-v1.md"
        if p1.is_file() and p2.is_file():
            assert "CD" in p1.read_text(encoding="utf-8")
            assert "caps" in p2.read_text(encoding="utf-8").lower()
            return
    pytest.fail("Phase 06 P06-11 doctrine files not found from test path")


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.PHASE06_CHRONOLOGY_DEGRADATION_RUNTIME_SCHEMA_VERSION >= 1
    assert CD_CHRON in r.CANONICAL_DEGRADATION_CODES
    assert callable(r.list_cd_chron_from_chronology_legality_v1)
    assert callable(r.validate_policy_caps_g_p06_pol01_v1)
