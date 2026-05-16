"""Phase 06 P06-08 — interval continuity + half-open closure + chronology receipt binding.

Normative:
``DOCS/cortex/reasoning/temporal-reasoning-doctrine.md`` (§2 half-open graphs, receipts),
``DOCS/cortex/reasoning/chronology-replay-legality-state-machine.md`` (projection + receipts).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, Final

from vector.domains.cortex.reasoning.chronology_legality import (
    ChronologyLegalityError,
    TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
    load_default_reasoning_policy_pack,
    project_chronology_legality_class_v1,
)
from vector.domains.cortex.reasoning.temporal_anchor_resolution import hash_reasoning_receipt_canonical_v1
from vector.domains.cortex.reasoning.temporal_reasoning import (
    TemporalReasoningInvariantError,
    validate_half_open_interval_iso,
    validate_no_replay_safe_ordering_mutation_claim,
    validate_reasoning_interval_has_anchor_or_raw_lineage,
    validate_replay_safe_ordering_read_only_value,
)

PHASE06_INTERVAL_CONTINUITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

REASONING_CHRONOLOGY_RECEIPT_TYPE: Final[str] = "reasoning_chronology_receipt"


class IntervalContinuityError(ValueError):
    """Fail-closed interval graph / half-open chain / chronology receipt binding."""


def _parse_iso8601(value: str) -> datetime:
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def _utc_datetime_from_interval_iso(value: object, *, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise IntervalContinuityError(f"{field} must be a non-empty ISO-8601 string")
    try:
        dt = _parse_iso8601(value)
    except ValueError as exc:
        raise IntervalContinuityError(f"{field} is not valid ISO-8601: {exc}") from exc
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def validate_reasoning_interval_slice_half_open_v1(interval: Mapping[str, Any]) -> None:
    """Half-open slice + **T‑TEMP‑01** lineage on a single reasoning interval."""
    try:
        validate_reasoning_interval_has_anchor_or_raw_lineage(interval)
        start = interval.get("start_iso")
        end = interval.get("end_iso")
        validate_half_open_interval_iso(start_iso=start, end_iso=end)
    except TemporalReasoningInvariantError as exc:
        raise IntervalContinuityError(str(exc)) from exc


def validate_half_open_interval_chain_continuity_v1(
    intervals: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Ordered half-open chain: ``end_i`` meets ``start_{i+1}`` (UTC-normalized), **T‑TEMP‑01** each slice.

    The last interval **may** omit ``end_iso`` (open tail). Interior intervals **must** include
    ``end_iso`` so continuity is well-defined.
    """
    if not intervals:
        raise IntervalContinuityError("interval chain must be non-empty")
    rows: list[dict[str, Any]] = []
    for i, raw in enumerate(intervals):
        if not isinstance(raw, Mapping):
            raise IntervalContinuityError(f"intervals[{i}] must be a mapping")
        row = dict(raw)
        validate_reasoning_interval_slice_half_open_v1(row)
        rows.append(row)

    def start_key(m: Mapping[str, Any]) -> datetime:
        return _utc_datetime_from_interval_iso(m.get("start_iso"), field="start_iso")

    rows.sort(key=start_key)
    for i in range(len(rows) - 1):
        cur, nxt = rows[i], rows[i + 1]
        end_cur = cur.get("end_iso")
        if end_cur is None:
            raise IntervalContinuityError(
                "half-open chain continuity: interior interval must not omit end_iso "
                f"(index {i})"
            )
        t_end = _utc_datetime_from_interval_iso(end_cur, field="end_iso")
        t_next_start = _utc_datetime_from_interval_iso(nxt.get("start_iso"), field="start_iso")
        if t_end != t_next_start:
            raise IntervalContinuityError(
                "half-open chain continuity: end_iso of interval i must equal start_iso of i+1 "
                f"(mismatch at link index {i})"
            )
    return rows


def validate_chronology_snapshot_read_only_replay_safe_ordering_v1(
    snapshot: Mapping[str, Any],
) -> None:
    """**CHRON‑AUTH‑1** alignment — consume ``replay_safe_ordering`` read-only; forbid mutation claims."""
    try:
        validate_replay_safe_ordering_read_only_value(snapshot.get("replay_safe_ordering"))
        validate_no_replay_safe_ordering_mutation_claim(snapshot)
    except TemporalReasoningInvariantError as exc:
        raise IntervalContinuityError(str(exc)) from exc


def reasoning_chronology_receipt_body_v1(
    *,
    anchor_chain_digest: str,
    chronology_projection_snapshot: Mapping[str, Any],
    policy: Mapping[str, Any],
    intervals_chain_digest: str,
    reasoning_rule_pack_id: str,
    tcre_policy_bundle_digest: str,
) -> tuple[dict[str, Any], str, int, bool]:
    """Build ``reasoning_chronology_receipt`` payload + digest; run **§2.1** projection (read-only ``R``)."""
    validate_chronology_snapshot_read_only_replay_safe_ordering_v1(chronology_projection_snapshot)
    if not isinstance(anchor_chain_digest, str) or not anchor_chain_digest.strip():
        raise IntervalContinuityError("anchor_chain_digest must be a non-empty string")
    if not isinstance(intervals_chain_digest, str) or not intervals_chain_digest.strip():
        raise IntervalContinuityError("intervals_chain_digest must be a non-empty string")
    if not isinstance(reasoning_rule_pack_id, str) or not reasoning_rule_pack_id.strip():
        raise IntervalContinuityError("reasoning_rule_pack_id must be a non-empty string")
    if not isinstance(tcre_policy_bundle_digest, str) or not tcre_policy_bundle_digest.strip():
        raise IntervalContinuityError("tcre_policy_bundle_digest must be a non-empty string")

    c, matched_idx, partitioned = project_chronology_legality_class_v1(
        chronology_projection_snapshot,
        policy,
    )
    body: dict[str, Any] = {
        "receipt_type": REASONING_CHRONOLOGY_RECEIPT_TYPE,
        "phase06_interval_continuity_runtime_schema_version": (
            PHASE06_INTERVAL_CONTINUITY_RUNTIME_SCHEMA_VERSION
        ),
        "anchor_chain_digest": anchor_chain_digest.strip(),
        "intervals_chain_digest": intervals_chain_digest.strip(),
        "replay_safe_ordering": chronology_projection_snapshot.get("replay_safe_ordering"),
        "chronology_legality_class": c,
        "chronology_skew_projection_matched_row_canonical_index": matched_idx,
        "partitioned_exception_applied": partitioned,
        "reasoning_rule_pack_id": reasoning_rule_pack_id.strip(),
        "tcre_policy_bundle_digest": tcre_policy_bundle_digest.strip(),
    }
    digest = hash_reasoning_receipt_canonical_v1(body)
    return body, digest, matched_idx, partitioned


def validate_interval_graph_and_emit_chronology_receipt_v1(
    intervals: Sequence[Mapping[str, Any]],
    *,
    chronology_projection_snapshot: Mapping[str, Any],
    policy: Mapping[str, Any],
    anchor_chain_digest: str,
    reasoning_rule_pack_id: str,
    tcre_policy_bundle_digest: str,
) -> tuple[list[dict[str, Any]], dict[str, Any], str, str, int, bool]:
    """§2 doctrine — validate half-open chain, then emit chronology receipt (intervals digest included)."""
    ordered = validate_half_open_interval_chain_continuity_v1(intervals)
    # Deterministic digest of the validated interval chain (canonical JSON).
    interval_refs = [
        {
            "derivation_rule_id": str(m.get("derivation_rule_id", "")),
            "start_iso": str(m.get("start_iso", "")),
            "end_iso": m.get("end_iso"),
        }
        for m in ordered
    ]
    intervals_chain_digest = hash_reasoning_receipt_canonical_v1(
        {"interval_slices_v1": interval_refs},
    )
    body, digest, matched_idx, partitioned = reasoning_chronology_receipt_body_v1(
        anchor_chain_digest=anchor_chain_digest,
        chronology_projection_snapshot=chronology_projection_snapshot,
        policy=policy,
        intervals_chain_digest=intervals_chain_digest,
        reasoning_rule_pack_id=reasoning_rule_pack_id,
        tcre_policy_bundle_digest=tcre_policy_bundle_digest,
    )
    return ordered, body, digest, intervals_chain_digest, matched_idx, partitioned


def verify_gp06_int01_half_open_chain_continuity_static() -> dict[str, Any]:
    """Static: continuity link + interior ``end_iso`` rules."""
    errors: list[str] = []
    try:
        validate_half_open_interval_chain_continuity_v1(
            [
                {
                    "derivation_rule_id": "SEG_v1",
                    "start_iso": "2025-01-01T00:00:00Z",
                    "end_iso": "2025-01-02T00:00:00Z",
                    "anchor_ids": ["a1"],
                },
                {
                    "derivation_rule_id": "SEG_v1",
                    "start_iso": "2025-01-02T00:00:00Z",
                    "end_iso": "2025-01-03T00:00:00Z",
                    "anchor_ids": ["a2"],
                },
            ]
        )
    except IntervalContinuityError as exc:
        errors.append(f"unexpected_reject_good_chain:{exc}")
    try:
        validate_half_open_interval_chain_continuity_v1(
            [
                {
                    "derivation_rule_id": "SEG_v1",
                    "start_iso": "2025-01-01T00:00:00Z",
                    "end_iso": "2025-01-02T00:00:00Z",
                    "anchor_ids": ["a1"],
                },
                {
                    "derivation_rule_id": "SEG_v1",
                    "start_iso": "2025-01-03T00:00:00Z",
                    "end_iso": "2025-01-04T00:00:00Z",
                    "anchor_ids": ["a2"],
                },
            ]
        )
    except IntervalContinuityError:
        pass
    else:
        errors.append("expected_reject_gap_chain")
    passed = len(errors) == 0
    return {
        "id": "P06-08-int-chain",
        "name": "half_open_interval_chain_continuity",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_interval_continuity_runtime_schema_version": (
                PHASE06_INTERVAL_CONTINUITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }


def verify_gp06_int02_chronology_receipt_projection_static() -> dict[str, Any]:
    """Static: receipt binds projection + digests on default policy."""
    errors: list[str] = []
    try:
        pack = load_default_reasoning_policy_pack()
        snap = {
            "replay_safe_ordering": "strict",
            "skew_detected": False,
            "late_arrival": False,
            "export_sequence_conflict": False,
            "active_conflict_classes": [],
        }
        body, digest, _, _ = reasoning_chronology_receipt_body_v1(
            anchor_chain_digest="sha256:aa" * 16,
            chronology_projection_snapshot=snap,
            policy=pack,
            intervals_chain_digest="sha256:bb" * 16,
            reasoning_rule_pack_id="ReasoningPolicyPackV1_Default",
            tcre_policy_bundle_digest=TCRE_REASONING_POLICY_PACK_V1_DEFAULT_DIGEST,
        )
        if body.get("receipt_type") != REASONING_CHRONOLOGY_RECEIPT_TYPE:
            errors.append("receipt_type_mismatch")
        if body.get("chronology_legality_class") != "chronology_strict":
            errors.append("unexpected_chronology_class")
        if len(digest) != 64:
            errors.append("digest_shape")
    except (IntervalContinuityError, ChronologyLegalityError, OSError, ValueError, TypeError) as exc:
        errors.append(f"unexpected:{exc}")
    passed = len(errors) == 0
    return {
        "id": "P06-08-int-chron-receipt",
        "name": "reasoning_chronology_receipt_projection_bind",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_interval_continuity_runtime_schema_version": (
                PHASE06_INTERVAL_CONTINUITY_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }
