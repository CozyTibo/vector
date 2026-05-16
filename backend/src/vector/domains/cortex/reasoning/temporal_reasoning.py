"""Phase 06 P06-05 — temporal reasoning substrate (lawful intervals + anchors).

Normative: ``DOCS/cortex/reasoning/temporal-reasoning-doctrine.md``.
Substrate types: ``execution_reconstruction_contracts`` (``TemporalAnchorChain``, windows, etc.).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Final

PHASE06_TEMPORAL_REASONING_RUNTIME_SCHEMA_VERSION: Final[int] = 1

REPLAY_SAFE_ORDERING_LITERALS: Final[frozenset[str]] = frozenset({"strict", "partial", "unresolved"})


class TemporalReasoningInvariantError(ValueError):
    """Raised when temporal substrate / interval law (T‑TEMP‑*) is violated."""


def validate_replay_safe_ordering_read_only_value(value: object) -> None:
    """§2 — ``replay_safe_ordering`` must be one of the substrate literals (read-only consumption)."""
    if value not in REPLAY_SAFE_ORDERING_LITERALS:
        raise TemporalReasoningInvariantError(
            f"replay_safe_ordering must be one of {sorted(REPLAY_SAFE_ORDERING_LITERALS)}; got {value!r}"
        )


def validate_no_replay_safe_ordering_mutation_claim(payload: Mapping[str, Any]) -> None:
    """§2 — Phase **06** must not mutate ``replay_safe_ordering`` in place."""
    if payload.get("mutated_replay_safe_ordering") is True:
        raise TemporalReasoningInvariantError(
            "mutated_replay_safe_ordering must not be true for Phase 06 temporal substrate"
        )
    if payload.get("replay_safe_ordering_rewrite") is True:
        raise TemporalReasoningInvariantError("replay_safe_ordering_rewrite is forbidden")


def validate_reasoning_interval_has_anchor_or_raw_lineage(interval: Mapping[str, Any]) -> None:
    """T‑TEMP‑01 — no reasoning interval without ≥1 anchor or raw id in lineage."""
    dr = interval.get("derivation_rule_id")
    if not isinstance(dr, str) or not dr.strip():
        raise TemporalReasoningInvariantError("reasoning interval requires non-empty derivation_rule_id")

    anchor_ids = interval.get("anchor_ids")
    raw_ids = interval.get("source_raw_record_ids")
    lineage = interval.get("lineage")

    has_anchor_list = isinstance(anchor_ids, list) and any(
        isinstance(x, str) and x.strip() for x in anchor_ids
    )
    has_raw_list = isinstance(raw_ids, list) and any(
        isinstance(x, int) and not isinstance(x, bool) for x in raw_ids
    )

    has_lineage_evidence = False
    if isinstance(lineage, list) and lineage:
        for hop in lineage:
            if not isinstance(hop, Mapping):
                continue
            if isinstance(hop.get("anchor_id"), str) and hop["anchor_id"].strip():
                has_lineage_evidence = True
                break
            rid = hop.get("raw_record_id")
            if isinstance(rid, int) and not isinstance(rid, bool):
                has_lineage_evidence = True
                break

    if not (has_anchor_list or has_raw_list or has_lineage_evidence):
        raise TemporalReasoningInvariantError(
            "T-TEMP-01: reasoning interval requires anchor_ids, source_raw_record_ids, "
            "or lineage hops citing anchor_id / raw_record_id"
        )


def validate_late_arrival_append_only(evidence: Mapping[str, Any]) -> None:
    """T‑TEMP‑02 — late arrival must not rewrite committed historical labels."""
    if evidence.get("rewrites_historical_labels") is True:
        raise TemporalReasoningInvariantError("T-TEMP-02: rewrites_historical_labels must not be true")
    if evidence.get("label_rewrite_committed_history") is True:
        raise TemporalReasoningInvariantError(
            "T-TEMP-02: label_rewrite_committed_history must not be true; append superseding evidence only"
        )


def validate_cross_source_temporal_reference_contract(ref: Mapping[str, Any]) -> None:
    """T‑TEMP‑03 — ``CrossSourceTemporalReference`` substrate shape (continuity law linkage only)."""
    ver = ref.get("execution_reconstruction_contract_version")
    if not isinstance(ver, int) or isinstance(ver, bool):
        raise TemporalReasoningInvariantError(
            "CrossSourceTemporalReference requires execution_reconstruction_contract_version int"
        )
    for key in ("reference_id", "left_anchor_id", "right_anchor_id"):
        v = ref.get(key)
        if not isinstance(v, str) or not v.strip():
            raise TemporalReasoningInvariantError(
                f"CrossSourceTemporalReference requires non-empty string {key}"
            )
    for flag in ("skew_detected", "late_arrival"):
        if flag in ref and not isinstance(ref[flag], bool):
            raise TemporalReasoningInvariantError(f"CrossSourceTemporalReference.{flag} must be bool when set")


def _parse_iso8601(value: str) -> datetime:
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def validate_half_open_interval_iso(*, start_iso: object, end_iso: object | None) -> None:
    """Half-open ``[start, end)`` for bounded intervals using ISO-8601 strings."""
    if not isinstance(start_iso, str) or not start_iso.strip():
        raise TemporalReasoningInvariantError("start_iso must be a non-empty ISO-8601 string")
    if end_iso is None:
        return
    if not isinstance(end_iso, str) or not end_iso.strip():
        raise TemporalReasoningInvariantError("end_iso must be a non-empty ISO-8601 string when provided")
    try:
        start_dt = _parse_iso8601(start_iso)
        end_dt = _parse_iso8601(end_iso)
    except ValueError as exc:
        raise TemporalReasoningInvariantError(f"invalid ISO-8601 interval endpoint: {exc}") from exc
    if start_dt >= end_dt:
        raise TemporalReasoningInvariantError(
            "half-open interval requires start_iso < end_iso (strict lower bound)"
        )


def verify_gp06_tr01_interval_lineage_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_reasoning_interval_has_anchor_or_raw_lineage(
            {
                "derivation_rule_id": "INT_OBL_v1",
                "lineage": [{"anchor_id": "a1"}],
            }
        )
    except TemporalReasoningInvariantError as exc:
        errors.append(f"unexpected_reject_good_lineage:{exc}")
    try:
        validate_reasoning_interval_has_anchor_or_raw_lineage(
            {"derivation_rule_id": "INT_BAD", "lineage": []}
        )
    except TemporalReasoningInvariantError:
        pass
    else:
        errors.append("expected_t_temp_01_empty_lineage")
    passed = len(errors) == 0
    return {
        "id": "P06-05-tr-temp-01",
        "name": "interval_anchor_or_raw_lineage",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_temporal_reasoning_runtime_schema_version": (
                PHASE06_TEMPORAL_REASONING_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_tr02_late_arrival_append_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_late_arrival_append_only({})
    except TemporalReasoningInvariantError as exc:
        errors.append(f"unexpected_reject_clean:{exc}")
    try:
        validate_late_arrival_append_only({"rewrites_historical_labels": True})
    except TemporalReasoningInvariantError:
        pass
    else:
        errors.append("expected_t_temp_02_reject_rewrite")
    passed = len(errors) == 0
    return {
        "id": "P06-05-tr-temp-02",
        "name": "late_arrival_append_only",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_temporal_reasoning_runtime_schema_version": (
                PHASE06_TEMPORAL_REASONING_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_tr03_cross_source_reference_static() -> dict[str, Any]:
    errors: list[str] = []
    good = {
        "execution_reconstruction_contract_version": 1,
        "reference_id": "ref-1",
        "left_anchor_id": "L",
        "right_anchor_id": "R",
        "skew_detected": False,
        "late_arrival": False,
    }
    try:
        validate_cross_source_temporal_reference_contract(good)
    except TemporalReasoningInvariantError as exc:
        errors.append(f"unexpected_reject_good_ref:{exc}")
    bad = dict(good)
    del bad["left_anchor_id"]
    try:
        validate_cross_source_temporal_reference_contract(bad)
    except TemporalReasoningInvariantError:
        pass
    else:
        errors.append("expected_reject_missing_anchor")
    passed = len(errors) == 0
    return {
        "id": "P06-05-tr-temp-03",
        "name": "cross_source_temporal_reference",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_temporal_reasoning_runtime_schema_version": (
                PHASE06_TEMPORAL_REASONING_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_tr04_half_open_interval_static() -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_half_open_interval_iso(start_iso="2025-01-01T00:00:00Z", end_iso="2025-01-02T00:00:00Z")
    except TemporalReasoningInvariantError as exc:
        errors.append(f"unexpected_reject_good_half_open:{exc}")
    try:
        validate_half_open_interval_iso(start_iso="2025-01-02T00:00:00Z", end_iso="2025-01-01T00:00:00Z")
    except TemporalReasoningInvariantError:
        pass
    else:
        errors.append("expected_reject_inverted_interval")
    passed = len(errors) == 0
    return {
        "id": "P06-05-tr-half-open",
        "name": "half_open_iso_interval",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_temporal_reasoning_runtime_schema_version": (
                PHASE06_TEMPORAL_REASONING_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }
