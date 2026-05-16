"""Phase 06 P06-10 — temporal conflict resolution (late arrival + skew / export vs observed).

Normative: ``DOCS/cortex/reasoning/temporal-conflict-resolution-law.md``.
Bridges: ``chronology-replay-legality-state-machine.md`` (``chronology_legality_class`` outcomes).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final

from vector.domains.cortex.reasoning.temporal_reasoning import (
    TemporalReasoningInvariantError,
    validate_late_arrival_append_only,
)

PHASE06_TEMPORAL_CONFLICT_RUNTIME_SCHEMA_VERSION: Final[int] = 1

TEMPORAL_CONFLICT_CLASS_IDS: Final[frozenset[str]] = frozenset(
    {
        "chronology_conflict",
        "export_sequence_conflict",
        "anchor_skew",
        "late_arrival_vs_export_order",
    }
)


class TemporalConflictResolutionError(ValueError):
    """Fail-closed temporal conflict law (non-rewrite, precedence, strict chronology)."""


def validate_temporal_active_conflict_classes_v1(classes: object) -> list[str]:
    """Normalize ``active_conflict_classes`` to a sorted list; reject unknown ids."""
    if classes is None:
        return []
    if not isinstance(classes, list):
        raise TemporalConflictResolutionError("active_conflict_classes must be a list or omitted")
    out: list[str] = []
    for i, c in enumerate(classes):
        if not isinstance(c, str) or not c.strip():
            raise TemporalConflictResolutionError(f"active_conflict_classes[{i}] must be a non-empty string")
        cid = c.strip()
        if cid not in TEMPORAL_CONFLICT_CLASS_IDS:
            raise TemporalConflictResolutionError(f"unknown temporal conflict class id: {cid!r}")
        out.append(cid)
    return sorted(set(out))


def validate_temporal_conflict_no_history_rewrite_v1(evidence: Mapping[str, Any]) -> None:
    """Non‑rewrite law — late arrival must not rewrite committed labels (**T‑TEMP‑02** substrate)."""
    try:
        validate_late_arrival_append_only(evidence)
    except TemporalReasoningInvariantError as exc:
        raise TemporalConflictResolutionError(str(exc)) from exc


def temporal_conflict_precedence_rank_v1(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """§Precedence — deterministic rank **1–4** (1 = strongest substrate signal … 4 = law fallback).

    Rank **4** means reducers **must** treat ordering as underdetermined unless amended
    (law: otherwise ``chronology_unresolved`` + degradation).
    """
    validate_temporal_conflict_no_history_rewrite_v1(evidence)
    if evidence.get("immutable_connector_native_timestamp_present") is True:
        return {
            "precedence_rank": 1,
            "precedence_source": "immutable_connector_native_timestamp",
            "requires_unresolved_and_degradation": False,
        }
    if evidence.get("monotonic_export_cursor_present") is True:
        return {
            "precedence_rank": 2,
            "precedence_source": "monotonic_export_cursor",
            "requires_unresolved_and_degradation": False,
        }
    rule_id = evidence.get("fetched_at_tie_break_rule_id")
    if evidence.get("fetched_at_tie_break_explicit") is True and isinstance(rule_id, str) and rule_id.strip():
        return {
            "precedence_rank": 3,
            "precedence_source": "ingestion_fetched_at_with_explicit_rule_id",
            "requires_unresolved_and_degradation": False,
            "fetched_at_tie_break_rule_id": rule_id.strip(),
        }
    return {
        "precedence_rank": 4,
        "precedence_source": "law_fallback_unresolved",
        "requires_unresolved_and_degradation": True,
    }


def validate_chronology_strict_requires_resolved_pairs_v1(
    chronology_legality_class: str,
    *,
    pairwise_ordering_ambiguous: bool,
    documented_tie_break_rule_id: object = None,
) -> None:
    """§Outcomes — ``chronology_strict`` forbidden if pairwise order is ambiguous without tie‑break."""
    if chronology_legality_class != "chronology_strict":
        return
    if not pairwise_ordering_ambiguous:
        return
    if isinstance(documented_tie_break_rule_id, str) and documented_tie_break_rule_id.strip():
        return
    raise TemporalConflictResolutionError(
        "chronology_strict forbidden when pairwise_ordering_ambiguous without documented_tie_break_rule_id"
    )


def validate_export_vs_observed_conflict_flags_v1(snapshot: Mapping[str, Any]) -> None:
    """Substrate booleans for export vs observed / skew / late arrival must be well-typed when present."""
    for key in ("skew_detected", "late_arrival", "export_sequence_conflict"):
        if key in snapshot and not isinstance(snapshot[key], bool):
            raise TemporalConflictResolutionError(f"snapshot.{key} must be bool when present")


def chronology_projection_snapshot_from_temporal_conflict_v1(
    *,
    replay_safe_ordering: str,
    evidence: Mapping[str, Any],
    active_conflict_classes: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Build a **ChronologyLegalityProjectionV1** snapshot dict from conflict evidence + substrate flags."""
    validate_export_vs_observed_conflict_flags_v1(evidence)
    classes = validate_temporal_active_conflict_classes_v1(
        list(active_conflict_classes) if active_conflict_classes is not None else evidence.get("active_conflict_classes")
    )
    snap: dict[str, Any] = {
        "replay_safe_ordering": replay_safe_ordering,
        "skew_detected": bool(evidence.get("skew_detected")),
        "late_arrival": bool(evidence.get("late_arrival")),
        "export_sequence_conflict": bool(evidence.get("export_sequence_conflict")),
        "active_conflict_classes": classes,
    }
    return snap


def verify_gp06_tcr01_precedence_oracle_static() -> dict[str, Any]:
    """Static: precedence ladder returns expected ranks."""
    errors: list[str] = []
    r1 = temporal_conflict_precedence_rank_v1(
        {"immutable_connector_native_timestamp_present": True},
    )
    if r1.get("precedence_rank") != 1:
        errors.append("rank1")
    r2 = temporal_conflict_precedence_rank_v1(
        {"monotonic_export_cursor_present": True},
    )
    if r2.get("precedence_rank") != 2:
        errors.append("rank2")
    r3 = temporal_conflict_precedence_rank_v1(
        {"fetched_at_tie_break_explicit": True, "fetched_at_tie_break_rule_id": "RULE_fetch_v1"},
    )
    if r3.get("precedence_rank") != 3:
        errors.append("rank3")
    r4 = temporal_conflict_precedence_rank_v1({})
    if r4.get("precedence_rank") != 4 or not r4.get("requires_unresolved_and_degradation"):
        errors.append("rank4")
    try:
        temporal_conflict_precedence_rank_v1({"rewrites_historical_labels": True})
        errors.append("expected_rewrite_rejected")
    except TemporalConflictResolutionError:
        pass
    passed = len(errors) == 0
    return {
        "id": "P06-10-tcr-precedence",
        "name": "temporal_conflict_precedence_rank_v1",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_temporal_conflict_runtime_schema_version": (
                PHASE06_TEMPORAL_CONFLICT_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_tcr02_chronology_strict_pairwise_static() -> dict[str, Any]:
    """Static: ``chronology_strict`` + ambiguous pairwise without rule fails."""
    errors: list[str] = []
    try:
        validate_chronology_strict_requires_resolved_pairs_v1(
            "chronology_strict",
            pairwise_ordering_ambiguous=True,
            documented_tie_break_rule_id=None,
        )
    except TemporalConflictResolutionError:
        pass
    else:
        errors.append("expected_strict_rejected")
    try:
        validate_chronology_strict_requires_resolved_pairs_v1(
            "chronology_strict",
            pairwise_ordering_ambiguous=True,
            documented_tie_break_rule_id="  TIE_v1  ",
        )
    except TemporalConflictResolutionError as exc:
        errors.append(f"unexpected_reject_with_rule:{exc}")
    try:
        validate_chronology_strict_requires_resolved_pairs_v1(
            "chronology_partial",
            pairwise_ordering_ambiguous=True,
            documented_tie_break_rule_id=None,
        )
    except TemporalConflictResolutionError as exc:
        errors.append(f"unexpected_reject_partial:{exc}")
    passed = len(errors) == 0
    return {
        "id": "P06-10-tcr-strict-pairwise",
        "name": "chronology_strict_pairwise_law",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_temporal_conflict_runtime_schema_version": (
                PHASE06_TEMPORAL_CONFLICT_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_tcr03_conflict_class_registry_static() -> dict[str, Any]:
    """Static: registry literals match doctrine wording."""
    expected = frozenset(
        {
            "chronology_conflict",
            "export_sequence_conflict",
            "anchor_skew",
            "late_arrival_vs_export_order",
        }
    )
    passed = TEMPORAL_CONFLICT_CLASS_IDS == expected
    return {
        "id": "P06-10-tcr-class-registry",
        "name": "temporal_conflict_class_ids",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_temporal_conflict_runtime_schema_version": (
                PHASE06_TEMPORAL_CONFLICT_RUNTIME_SCHEMA_VERSION
            ),
            "expected": sorted(expected),
            "actual": sorted(TEMPORAL_CONFLICT_CLASS_IDS),
        },
    }
