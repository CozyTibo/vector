"""P06-23 — Unverifiable / degraded causality (``CD‑*`` + DEG‑MON‑1 + legality bridge)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.chronology_degradation_propagation import CD_CHRON, CD_CONT
from vector.domains.cortex.reasoning.unverifiable_degraded_causality import (
    CAUSAL_DEGRADATION_SPEC_MONOTONICITY_REF_V1,
    CAUSAL_LEGALITY_UNVERIFIABLE_V1,
    PHASE06_UNVERIFIABLE_DEGRADED_CAUSALITY_RUNTIME_SCHEMA_VERSION,
    UnverifiableDegradedCausalityError,
    normalize_cd_corpus_tokens_sorted_unique_v1,
    validate_cd_multiset_monotonic_extension_degraded_v1,
    validate_degradation_receipt_entries_sorted_v1,
    validate_unverifiable_causality_requires_cd_codes_v1,
    verify_gp06_udc01_canonical_cd_literal_oracle_static,
    verify_gp06_udc02_severity_rank_table_oracle_static,
    verify_gp06_udc03_monotonic_regression_rejected_static,
    verify_gp06_udc04_unverifiable_requires_cd_static,
    verify_gp06_udc05_degradation_receipt_sort_stable_static,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_UNVERIFIABLE_DEGRADED_CAUSALITY_RUNTIME_SCHEMA_VERSION >= 1


def test_static_gates() -> None:
    assert verify_gp06_udc01_canonical_cd_literal_oracle_static()["passed"] is True
    assert verify_gp06_udc02_severity_rank_table_oracle_static()["passed"] is True
    assert verify_gp06_udc03_monotonic_regression_rejected_static()["passed"] is True
    assert verify_gp06_udc04_unverifiable_requires_cd_static()["passed"] is True
    assert verify_gp06_udc05_degradation_receipt_sort_stable_static()["passed"] is True


def test_unverifiable_requires_non_empty_cd_list() -> None:
    with pytest.raises(UnverifiableDegradedCausalityError, match="non-empty"):
        validate_unverifiable_causality_requires_cd_codes_v1(
            causal_legality_class=CAUSAL_LEGALITY_UNVERIFIABLE_V1,
            cd_codes=[],
        )


def test_unverifiable_rejects_unknown_cd_token() -> None:
    with pytest.raises(UnverifiableDegradedCausalityError):
        validate_unverifiable_causality_requires_cd_codes_v1(
            causal_legality_class=CAUSAL_LEGALITY_UNVERIFIABLE_V1,
            cd_codes=["not-a-cd"],
        )


def test_unverifiable_accepts_normalized_cd() -> None:
    validate_unverifiable_causality_requires_cd_codes_v1(
        causal_legality_class=CAUSAL_LEGALITY_UNVERIFIABLE_V1,
        cd_codes=[CD_CONT],
    )


def test_other_legality_skips_cd_requirement() -> None:
    validate_unverifiable_causality_requires_cd_codes_v1(
        causal_legality_class="causal_replay_equivalent",
        cd_codes=[],
    )


def test_monotonic_extension_accepts_superset() -> None:
    validate_cd_multiset_monotonic_extension_degraded_v1([CD_CHRON], [CD_CHRON, CD_CONT])


def test_monotonic_extension_rejects_regression() -> None:
    with pytest.raises(UnverifiableDegradedCausalityError):
        validate_cd_multiset_monotonic_extension_degraded_v1([CD_CHRON, CD_CONT], [CD_CHRON])


def test_normalize_cd_sorted_unique() -> None:
    assert normalize_cd_corpus_tokens_sorted_unique_v1([CD_CONT, CD_CHRON, CD_CONT]) == [
        CD_CHRON,
        CD_CONT,
    ]


def test_receipt_sort_wrapper() -> None:
    from vector.domains.cortex.reasoning.chronology_degradation_propagation import (
        degradation_receipt_entry_v1,
    )

    a = degradation_receipt_entry_v1(
        code=CD_CONT,
        rule_id="r-b",
        upstream_artifact_ids_sorted=["x"],
        before_hash="h1",
    )
    b = degradation_receipt_entry_v1(
        code=CD_CHRON,
        rule_id="r-a",
        upstream_artifact_ids_sorted=["y"],
        before_hash="h2",
    )
    ordered = validate_degradation_receipt_entries_sorted_v1([a, b])
    assert ordered[0]["code"] == CD_CHRON
    assert ordered[1]["code"] == CD_CONT


def test_doctrine_refs() -> None:
    assert "conflict-resolution-doctrine.md" in CAUSAL_DEGRADATION_SPEC_MONOTONICITY_REF_V1
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        spec = root / "DOCS" / "cortex" / "reasoning" / "causal-degradation-spec.md"
        if spec.is_file():
            txt = spec.read_text(encoding="utf-8")
            assert "DEG‑MON‑1" in txt or "DEG-MON-1" in txt
            assert "CD‑CHRON" in txt or "CD-CHRON" in txt
            return
    pytest.fail("P06-23 causal-degradation-spec.md not found")


def test_package_reexports() -> None:
    import vector.domains.cortex.reasoning as r

    assert r.PHASE06_UNVERIFIABLE_DEGRADED_CAUSALITY_RUNTIME_SCHEMA_VERSION >= 1
    assert r.CAUSAL_LEGALITY_UNVERIFIABLE_V1 == "causal_unverifiable"
    assert verify_gp06_udc01_canonical_cd_literal_oracle_static()["passed"] is True
