"""Phase 06 P06-23 — unverifiable / degraded causality (``CD‑*`` + monotonicity).

Normative:
``DOCS/cortex/reasoning/causal-degradation-spec.md`` (§§1–4, 6),
``DOCS/cortex/reasoning/execution-causality-constraints.md`` (``causal_unverifiable``),
``DOCS/cortex/reasoning/chronology-degradation-propagation`` (P06-11 substrate).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.chronology_degradation_propagation import (
    CANONICAL_DEGRADATION_CODES,
    CD_CHRON,
    CD_COMMIT,
    CD_CONT,
    CD_NEG,
    CD_REPLAY,
    ChronologyDegradationPropagationError,
    degradation_receipt_entry_v1,
    degradation_severity_rank_v1,
    normalize_degradation_corpus_token_v1,
    sort_degradation_receipt_entries_v1,
    validate_degradation_multiset_monotonic_extension_v1,
)
from vector.domains.cortex.reasoning.execution_causality_constraints import (
    ExecutionCausalityConstraintError,
    validate_causal_legality_class,
)

PHASE06_UNVERIFIABLE_DEGRADED_CAUSALITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

CAUSAL_LEGALITY_UNVERIFIABLE_V1: Final[str] = "causal_unverifiable"

CAUSAL_DEGRADATION_SPEC_MONOTONICITY_REF_V1: Final[str] = (
    "DOCS/cortex/continuity/conflict-resolution-doctrine.md §6"
)


class UnverifiableDegradedCausalityError(ValueError):
    """Fail-closed unverifiable / degraded causality (``CD‑*`` + DEG‑MON‑1)."""


def _udc_detail(errors: list[str]) -> dict[str, Any]:
    return {
        "errors": errors,
        "phase06_unverifiable_degraded_causality_runtime_schema_version": (
            PHASE06_UNVERIFIABLE_DEGRADED_CAUSALITY_RUNTIME_SCHEMA_VERSION
        ),
    }


def validate_unverifiable_causality_requires_cd_codes_v1(
    *,
    causal_legality_class: str,
    cd_codes: object,
) -> None:
    """``causal_unverifiable`` must cite a non-empty multiset of normalized ``CD‑*`` codes."""
    try:
        validate_causal_legality_class(causal_legality_class)
    except ExecutionCausalityConstraintError as exc:
        raise UnverifiableDegradedCausalityError(str(exc)) from exc
    if causal_legality_class != CAUSAL_LEGALITY_UNVERIFIABLE_V1:
        return
    if not isinstance(cd_codes, list) or len(cd_codes) == 0:
        raise UnverifiableDegradedCausalityError(
            "causal_unverifiable requires non-empty cd_codes listing CD evidence"
        )
    for i, c in enumerate(cd_codes):
        if not isinstance(c, str) or not c.strip():
            raise UnverifiableDegradedCausalityError(f"cd_codes[{i}] must be a non-empty string")
        try:
            normalize_degradation_corpus_token_v1(c.strip())
        except ChronologyDegradationPropagationError as exc:
            raise UnverifiableDegradedCausalityError(str(exc)) from exc


def validate_cd_multiset_monotonic_extension_degraded_v1(
    before_codes: Sequence[str],
    after_codes: Sequence[str],
) -> None:
    """``causal-degradation-spec`` §6 — DEG‑MON‑1 multiset law (delegated normalization)."""
    try:
        validate_degradation_multiset_monotonic_extension_v1(before_codes, after_codes)
    except ChronologyDegradationPropagationError as exc:
        raise UnverifiableDegradedCausalityError(str(exc)) from exc


def normalize_cd_corpus_tokens_sorted_unique_v1(codes: Sequence[str]) -> list[str]:
    """Return sorted unique canonical ``CD‑*`` literals for provenance lists."""
    out: list[str] = []
    for i, c in enumerate(codes):
        if not isinstance(c, str) or not c.strip():
            raise UnverifiableDegradedCausalityError(f"codes[{i}] must be a non-empty string")
        try:
            out.append(normalize_degradation_corpus_token_v1(c.strip()))
        except ChronologyDegradationPropagationError as exc:
            raise UnverifiableDegradedCausalityError(str(exc)) from exc
    return sorted(set(out))


def validate_degradation_receipt_entries_sorted_v1(
    entries: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """``causal-degradation-spec`` §4 — deterministic receipt row order (delegated)."""
    try:
        return sort_degradation_receipt_entries_v1(entries)
    except ChronologyDegradationPropagationError as exc:
        raise UnverifiableDegradedCausalityError(str(exc)) from exc


def verify_gp06_udc01_canonical_cd_literal_oracle_static() -> dict[str, Any]:
    """P06-23 — five canonical ``CD‑*`` codes match doctrine §1 table."""
    errors: list[str] = []
    oracle = frozenset({CD_CHRON, CD_CONT, CD_REPLAY, CD_NEG, CD_COMMIT})
    if CANONICAL_DEGRADATION_CODES != oracle:
        errors.append("canonical_degradation_codes_mismatch_doctrine_v1")
    if len(CANONICAL_DEGRADATION_CODES) != 5:
        errors.append("expected_five_cd_literals")
    passed = len(errors) == 0
    return {
        "id": "P06-23-udc-cd-oracle",
        "name": "gp06_udc01_canonical_cd_literal_oracle",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _udc_detail(errors),
    }


def verify_gp06_udc02_severity_rank_table_oracle_static() -> dict[str, Any]:
    """P06-23 — ``severity_rank`` matches ``causal-degradation-spec`` §2."""
    errors: list[str] = []
    expected = {
        CD_COMMIT: 5,
        CD_REPLAY: 4,
        CD_NEG: 4,
        CD_CHRON: 3,
        CD_CONT: 2,
    }
    for code, rank in expected.items():
        try:
            got = degradation_severity_rank_v1(code)
        except ChronologyDegradationPropagationError as exc:
            errors.append(f"rank_exc:{code!r}:{exc}")
            continue
        if got != rank:
            errors.append(f"rank_mismatch:{code!r}:want={rank}:got={got}")
    passed = len(errors) == 0
    return {
        "id": "P06-23-udc-severity-rank",
        "name": "gp06_udc02_severity_rank_table_oracle",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _udc_detail(errors),
    }


def verify_gp06_udc03_monotonic_regression_rejected_static() -> dict[str, Any]:
    """P06-23 — DEG‑MON‑1 rejects multiset regression (§2 / §6)."""
    errors: list[str] = []
    try:
        validate_cd_multiset_monotonic_extension_degraded_v1([CD_CHRON], [])
    except UnverifiableDegradedCausalityError:
        pass
    else:
        errors.append("expected_reject_monotonic_regression")
    passed = len(errors) == 0
    return {
        "id": "P06-23-udc-monotonic",
        "name": "gp06_udc03_monotonic_regression_rejected",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _udc_detail(errors),
    }


def verify_gp06_udc04_unverifiable_requires_cd_static() -> dict[str, Any]:
    """P06-23 — ``causal_unverifiable`` without ``cd_codes`` fails."""
    errors: list[str] = []
    try:
        validate_unverifiable_causality_requires_cd_codes_v1(
            causal_legality_class=CAUSAL_LEGALITY_UNVERIFIABLE_V1,
            cd_codes=[],
        )
    except UnverifiableDegradedCausalityError:
        pass
    else:
        errors.append("expected_reject_empty_cd_under_unverifiable")
    passed = len(errors) == 0
    return {
        "id": "P06-23-udc-unverifiable-cd",
        "name": "gp06_udc04_unverifiable_requires_cd",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _udc_detail(errors),
    }


def verify_gp06_udc05_degradation_receipt_sort_stable_static() -> dict[str, Any]:
    """P06-23 — §4 receipt sort is permutation-invariant for same rows."""
    errors: list[str] = []
    try:
        a = degradation_receipt_entry_v1(
            code=CD_CONT,
            rule_id="r1",
            upstream_artifact_ids_sorted=["z", "a"],
            before_hash="h1",
        )
        b = degradation_receipt_entry_v1(
            code=CD_CHRON,
            rule_id="r2",
            upstream_artifact_ids_sorted=["b"],
            before_hash="h2",
        )
        s1 = validate_degradation_receipt_entries_sorted_v1([a, b])
        s2 = validate_degradation_receipt_entries_sorted_v1([b, a])
        if s1 != s2:
            errors.append("receipt_sort_order_not_stable")
    except UnverifiableDegradedCausalityError as exc:
        errors.append(str(exc))
    passed = len(errors) == 0
    return {
        "id": "P06-23-udc-receipt-sort",
        "name": "gp06_udc05_degradation_receipt_sort_stable",
        "passed": passed,
        "severity": "hard_fail",
        "detail": _udc_detail(errors),
    }
