"""Phase 06 P06-07 — temporal anchor resolution (ordering + receipts).

Normative: ``DOCS/cortex/reasoning/temporal-anchor-resolution-spec.md``.
Substrate anchors: ``execution_reconstruction_contracts.TemporalAnchor``.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any, Final

PHASE06_TEMPORAL_ANCHOR_RESOLUTION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

TEMPORAL_ANCHOR_RESOLUTION_ORDER_V1: Final[tuple[str, str, str, str]] = (
    "export_sequence",
    "snapshot_unix_ns",
    "observed_at_iso",
    "raw_record_id",
)

REASONING_TEMPORAL_ANCHOR_RESOLUTION_RECEIPT_TYPE: Final[str] = (
    "reasoning_temporal_anchor_resolution_receipt"
)


class TemporalAnchorResolutionError(ValueError):
    """Fail-closed temporal anchor normalization / ordering / declaration."""


def _parse_iso8601(value: str) -> datetime:
    s = value.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def normalize_observed_at_iso(value: object) -> str:
    """§2 — normalize timezone + string format to UTC ``…Z`` for deterministic lex order."""
    if not isinstance(value, str) or not value.strip():
        raise TemporalAnchorResolutionError("observed_at_iso must be a non-empty string")
    try:
        dt = _parse_iso8601(value)
    except ValueError as exc:
        raise TemporalAnchorResolutionError(f"observed_at_iso is not valid ISO-8601: {exc}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _int_non_bool(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _coerce_int_field(value: object, default: int) -> int:
    got = _int_non_bool(value)
    return default if got is None else got


def export_sequence_for_resolution_v1(anchor: Mapping[str, Any]) -> int:
    """§3 — ``export_sequence`` field or numeric ``monotonic_cursor`` (connector export cursor)."""
    ex = anchor.get("export_sequence")
    got = _int_non_bool(ex)
    if got is not None:
        return got
    mc = anchor.get("monotonic_cursor")
    if isinstance(mc, str) and mc.strip():
        s = mc.strip()
        if re.fullmatch(r"-?\d+", s):
            return int(s)
    return 0


def snapshot_unix_ns_for_resolution_v1(anchor: Mapping[str, Any]) -> int:
    """§3 — materialized snapshot nanoseconds; ``0`` when absent (stable low tie-break)."""
    v = anchor.get("snapshot_unix_ns")
    got = _int_non_bool(v)
    return 0 if got is None else got


def raw_record_id_for_resolution_v1(anchor: Mapping[str, Any]) -> int:
    """§3 — ``raw_record_id`` tie-break; ``0`` when absent."""
    v = anchor.get("raw_record_id")
    got = _int_non_bool(v)
    return 0 if got is None else got


def temporal_anchor_resolution_sort_key_v1(anchor: Mapping[str, Any]) -> tuple[int, int, str, int]:
    """§3 ``temporal_anchor_resolution_order_v1`` lexicographic key (ascending sort)."""
    iso = normalize_observed_at_iso(anchor.get("observed_at_iso"))
    return (
        export_sequence_for_resolution_v1(anchor),
        snapshot_unix_ns_for_resolution_v1(anchor),
        iso,
        raw_record_id_for_resolution_v1(anchor),
    )


def reject_median_time_resolution_heuristic(payload: Mapping[str, Any]) -> None:
    """§Conflicts — never pick “median time”; reject explicit median-resolution flags."""
    if payload.get("median_timestamp_resolution") is True:
        raise TemporalAnchorResolutionError("median_timestamp_resolution is forbidden")
    if payload.get("resolution_method") == "median_time":
        raise TemporalAnchorResolutionError("resolution_method median_time is forbidden")


def validate_temporal_anchor_resolution_inputs_v1(
    anchors: Sequence[Mapping[str, Any]],
    *,
    chain_context: Mapping[str, Any] | None = None,
) -> None:
    """Validate ingest-stage anchors and forbid forbidden conflict shortcuts."""
    if chain_context is not None:
        reject_median_time_resolution_heuristic(chain_context)
    for i, a in enumerate(anchors):
        if not isinstance(a, Mapping):
            raise TemporalAnchorResolutionError(f"anchors[{i}] must be a mapping")
        _ = temporal_anchor_resolution_sort_key_v1(a)


def sort_anchors_temporal_anchor_resolution_order_v1(
    anchors: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """§3 — stable deterministic sort using ``temporal_anchor_resolution_order_v1``."""
    enriched: list[tuple[tuple[int, int, str, int], int, dict[str, Any]]] = []
    for idx, raw in enumerate(anchors):
        if not isinstance(raw, Mapping):
            raise TemporalAnchorResolutionError("each anchor must be a mapping")
        m = raw
        key = temporal_anchor_resolution_sort_key_v1(m)
        row = dict(m)
        row["_resolution_sort_key_v1"] = {
            "export_sequence": key[0],
            "snapshot_unix_ns": key[1],
            "observed_at_iso_normalized": key[2],
            "raw_record_id": key[3],
        }
        enriched.append((key, idx, row))
    enriched.sort(key=lambda t: (t[0], t[1]))
    return [t[2] for t in enriched]


def declare_replay_safe_ordering_v1(
    sorted_anchors: Sequence[Mapping[str, Any]],
    *,
    ingest_sequence: Sequence[Mapping[str, Any]] | None = None,
    export_sequence_conflict: bool = False,
    chronology_conflict: bool = False,
) -> str:
    """§4 — declare ``replay_safe_ordering`` from ordered anchors + known conflict flags.

    **strict** only when ingest order is already non-decreasing by §3 keys and keys are
    pairwise distinct (total order visible without reorder). If resolution **sort** permutes
    ingest rows while preserving determinism, outcome is **partial** (tie/export semantics).

    Delegates to **unresolved** when substrate conflict flags are set. Never applies median time.
    """
    if export_sequence_conflict or chronology_conflict:
        return "unresolved"
    keys_sorted = [temporal_anchor_resolution_sort_key_v1(a) for a in sorted_anchors]
    if len(keys_sorted) != len(set(keys_sorted)):
        return "unresolved"
    if len(keys_sorted) <= 1:
        return "strict"
    seq = ingest_sequence if ingest_sequence is not None else sorted_anchors
    keys_ingest = [temporal_anchor_resolution_sort_key_v1(a) for a in seq]
    ingest_non_decreasing = all(keys_ingest[i] <= keys_ingest[i + 1] for i in range(len(keys_ingest) - 1))
    ingest_strict = all(keys_ingest[i] < keys_ingest[i + 1] for i in range(len(keys_ingest) - 1))
    if not ingest_non_decreasing:
        return "partial"
    if not ingest_strict:
        return "partial"
    return "strict"


def temporal_anchor_resolution_receipt_v1(
    *,
    sorted_anchors: Sequence[Mapping[str, Any]],
    replay_safe_ordering: str,
    chain_id: str,
) -> dict[str, Any]:
    """§5 — resolution receipt body (canonical hashing per ``reasoning-receipts-and-proof-artifacts.md`` §2)."""
    if replay_safe_ordering not in ("strict", "partial", "unresolved"):
        raise TemporalAnchorResolutionError(f"invalid replay_safe_ordering: {replay_safe_ordering!r}")
    anchor_refs: list[dict[str, Any]] = []
    for a in sorted_anchors:
        m = a
        aid = m.get("anchor_id")
        kid = m.get("_resolution_sort_key_v1")
        if isinstance(kid, Mapping):
            kid_dict = {
                "export_sequence": _coerce_int_field(kid.get("export_sequence"), 0),
                "snapshot_unix_ns": _coerce_int_field(kid.get("snapshot_unix_ns"), 0),
                "observed_at_iso_normalized": str(kid.get("observed_at_iso_normalized", "")),
                "raw_record_id": _coerce_int_field(kid.get("raw_record_id"), 0),
            }
        else:
            k0, k1, k2, k3 = temporal_anchor_resolution_sort_key_v1(m)
            kid_dict = {
                "export_sequence": k0,
                "snapshot_unix_ns": k1,
                "observed_at_iso_normalized": k2,
                "raw_record_id": k3,
            }
        anchor_refs.append(
            {
                "anchor_id": aid if isinstance(aid, str) else "",
                "resolution_sort_key_v1": kid_dict,
            }
        )
    anchor_refs.sort(key=lambda r: (r["anchor_id"], json.dumps(r["resolution_sort_key_v1"], sort_keys=True)))
    return {
        "receipt_type": REASONING_TEMPORAL_ANCHOR_RESOLUTION_RECEIPT_TYPE,
        "temporal_anchor_resolution_order_v1": list(TEMPORAL_ANCHOR_RESOLUTION_ORDER_V1),
        "phase06_temporal_anchor_resolution_runtime_schema_version": (
            PHASE06_TEMPORAL_ANCHOR_RESOLUTION_RUNTIME_SCHEMA_VERSION
        ),
        "chain_id": chain_id,
        "replay_safe_ordering": replay_safe_ordering,
        "sorted_anchor_refs": anchor_refs,
    }


def hash_reasoning_receipt_canonical_v1(body: Mapping[str, Any]) -> str:
    """Sorted-keys JSON UTF-8 ``sha256`` hex (``reasoning-receipts-and-proof-artifacts.md`` §2)."""
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_temporal_anchor_chain_v1(
    anchors: Sequence[Mapping[str, Any]],
    *,
    chain_id: str,
    chain_context: Mapping[str, Any] | None = None,
    export_sequence_conflict: bool = False,
    chronology_conflict: bool = False,
) -> tuple[list[dict[str, Any]], str, dict[str, Any], str]:
    """Stages §1–§5 — sort, declare ``replay_safe_ordering``, emit receipt + digest."""
    validate_temporal_anchor_resolution_inputs_v1(anchors, chain_context=chain_context)
    sorted_rows = sort_anchors_temporal_anchor_resolution_order_v1(anchors)
    r = declare_replay_safe_ordering_v1(
        sorted_rows,
        ingest_sequence=anchors,
        export_sequence_conflict=export_sequence_conflict,
        chronology_conflict=chronology_conflict,
    )
    receipt = temporal_anchor_resolution_receipt_v1(
        sorted_anchors=sorted_rows,
        replay_safe_ordering=r,
        chain_id=chain_id,
    )
    digest = hash_reasoning_receipt_canonical_v1(receipt)
    return sorted_rows, r, receipt, digest


def verify_gp06_tar01_resolution_order_literal_static() -> dict[str, Any]:
    """Static: ``TEMPORAL_ANCHOR_RESOLUTION_ORDER_V1`` matches doctrine §3 tuple."""
    expected = ("export_sequence", "snapshot_unix_ns", "observed_at_iso", "raw_record_id")
    passed = TEMPORAL_ANCHOR_RESOLUTION_ORDER_V1 == expected
    return {
        "id": "P06-07-tar-order-v1",
        "name": "temporal_anchor_resolution_order_v1_literal",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_temporal_anchor_resolution_runtime_schema_version": (
                PHASE06_TEMPORAL_ANCHOR_RESOLUTION_RUNTIME_SCHEMA_VERSION
            ),
            "expected": list(expected),
            "actual": list(TEMPORAL_ANCHOR_RESOLUTION_ORDER_V1),
        },
    }


def verify_gp06_tar02_declare_replay_safe_ordering_static() -> dict[str, Any]:
    """Static: small oracle table for ``declare_replay_safe_ordering_v1``."""
    errors: list[str] = []
    a1 = {"observed_at_iso": "2020-01-01T00:00:00Z", "export_sequence": 1, "snapshot_unix_ns": 0, "raw_record_id": 10}
    a2 = {"observed_at_iso": "2020-01-02T00:00:00Z", "export_sequence": 2, "snapshot_unix_ns": 0, "raw_record_id": 20}
    ingest = [a1, a2]
    s = sort_anchors_temporal_anchor_resolution_order_v1(ingest)
    if declare_replay_safe_ordering_v1(s, ingest_sequence=ingest) != "strict":
        errors.append("strict_pair_failed")
    dup = [
        {"observed_at_iso": "2020-01-01T00:00:00Z", "export_sequence": 1, "raw_record_id": 1},
        {"observed_at_iso": "2020-01-01T00:00:00Z", "export_sequence": 1, "raw_record_id": 1},
    ]
    s2 = sort_anchors_temporal_anchor_resolution_order_v1(dup)
    if declare_replay_safe_ordering_v1(s2, ingest_sequence=dup) != "unresolved":
        errors.append("duplicate_key_expected_unresolved")
    if declare_replay_safe_ordering_v1(s, ingest_sequence=ingest, export_sequence_conflict=True) != "unresolved":
        errors.append("export_conflict_expected_unresolved")
    reorder = [a2, a1]
    s_re = sort_anchors_temporal_anchor_resolution_order_v1(reorder)
    if declare_replay_safe_ordering_v1(s_re, ingest_sequence=reorder) != "partial":
        errors.append("reorder_expected_partial")
    passed = len(errors) == 0
    return {
        "id": "P06-07-tar-declare-rso",
        "name": "declare_replay_safe_ordering_v1_oracles",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {
            "phase06_temporal_anchor_resolution_runtime_schema_version": (
                PHASE06_TEMPORAL_ANCHOR_RESOLUTION_RUNTIME_SCHEMA_VERSION
            ),
            "errors": errors,
        },
    }
