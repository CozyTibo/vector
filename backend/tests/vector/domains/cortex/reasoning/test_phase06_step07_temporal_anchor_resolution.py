"""P06-07 — Temporal anchor resolution (ordering + ``replay_safe_ordering`` + receipt)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vector.domains.cortex.reasoning.temporal_anchor_resolution import (
    PHASE06_TEMPORAL_ANCHOR_RESOLUTION_RUNTIME_SCHEMA_VERSION,
    REASONING_TEMPORAL_ANCHOR_RESOLUTION_RECEIPT_TYPE,
    TEMPORAL_ANCHOR_RESOLUTION_ORDER_V1,
    TemporalAnchorResolutionError,
    declare_replay_safe_ordering_v1,
    hash_reasoning_receipt_canonical_v1,
    normalize_observed_at_iso,
    reject_median_time_resolution_heuristic,
    resolve_temporal_anchor_chain_v1,
    sort_anchors_temporal_anchor_resolution_order_v1,
    temporal_anchor_resolution_sort_key_v1,
    validate_temporal_anchor_resolution_inputs_v1,
    verify_gp06_tar01_resolution_order_literal_static,
    verify_gp06_tar02_declare_replay_safe_ordering_static,
)


def test_runtime_schema_version() -> None:
    assert PHASE06_TEMPORAL_ANCHOR_RESOLUTION_RUNTIME_SCHEMA_VERSION >= 1


def test_order_literal_matches_spec() -> None:
    assert verify_gp06_tar01_resolution_order_literal_static()["passed"] is True
    assert TEMPORAL_ANCHOR_RESOLUTION_ORDER_V1 == (
        "export_sequence",
        "snapshot_unix_ns",
        "observed_at_iso",
        "raw_record_id",
    )


def test_normalize_observed_at_iso_utc_z() -> None:
    assert normalize_observed_at_iso("2024-06-01T12:00:00Z").endswith("Z")
    out = normalize_observed_at_iso("2024-06-01T14:00:00+02:00")
    assert out.endswith("Z")


def test_normalize_rejects_invalid() -> None:
    with pytest.raises(TemporalAnchorResolutionError):
        normalize_observed_at_iso("not-a-date")


def test_sort_key_ordering() -> None:
    early = {"observed_at_iso": "2020-01-01T00:00:00Z", "export_sequence": 1, "snapshot_unix_ns": 0, "raw_record_id": 1}
    late = {"observed_at_iso": "2020-01-02T00:00:00Z", "export_sequence": 1, "snapshot_unix_ns": 0, "raw_record_id": 1}
    assert temporal_anchor_resolution_sort_key_v1(early) < temporal_anchor_resolution_sort_key_v1(late)


def test_sort_orders_export_before_iso_when_iso_later() -> None:
    """Lower export_sequence sorts first when timestamps disagree (lex tuple)."""
    hi_export = {"observed_at_iso": "2099-01-01T00:00:00Z", "export_sequence": 1, "raw_record_id": 1}
    lo_export = {"observed_at_iso": "2020-01-01T00:00:00Z", "export_sequence": 2, "raw_record_id": 2}
    s = sort_anchors_temporal_anchor_resolution_order_v1([lo_export, hi_export])
    assert temporal_anchor_resolution_sort_key_v1(s[0])[0] == 1


def test_monotonic_cursor_parses_as_export_sequence() -> None:
    a = {"observed_at_iso": "2020-01-01T00:00:00Z", "monotonic_cursor": "42", "raw_record_id": 1}
    assert temporal_anchor_resolution_sort_key_v1(a)[0] == 42


def test_median_rejected() -> None:
    with pytest.raises(TemporalAnchorResolutionError):
        reject_median_time_resolution_heuristic({"median_timestamp_resolution": True})


def test_resolve_end_to_end_strict() -> None:
    anchors = [
        {"anchor_id": "a", "observed_at_iso": "2020-01-01T00:00:00Z", "export_sequence": 1, "raw_record_id": 1},
        {"anchor_id": "b", "observed_at_iso": "2020-01-02T00:00:00Z", "export_sequence": 2, "raw_record_id": 2},
    ]
    sorted_rows, r, receipt, digest = resolve_temporal_anchor_chain_v1(anchors, chain_id="c1")
    assert r == "strict"
    assert len(sorted_rows) == 2
    assert receipt["receipt_type"] == REASONING_TEMPORAL_ANCHOR_RESOLUTION_RECEIPT_TYPE
    assert receipt["replay_safe_ordering"] == "strict"
    assert len(digest) == 64
    assert hash_reasoning_receipt_canonical_v1(receipt) == digest


def test_resolve_partial_when_ingest_out_of_order() -> None:
    a1 = {"anchor_id": "a", "observed_at_iso": "2020-01-01T00:00:00Z", "export_sequence": 1, "raw_record_id": 1}
    a2 = {"anchor_id": "b", "observed_at_iso": "2020-01-02T00:00:00Z", "export_sequence": 2, "raw_record_id": 2}
    _, r, _, _ = resolve_temporal_anchor_chain_v1([a2, a1], chain_id="c2")
    assert r == "partial"


def test_resolve_unresolved_on_duplicate_keys() -> None:
    row = {"observed_at_iso": "2020-01-01T00:00:00Z", "export_sequence": 1, "raw_record_id": 1}
    _, r, _, _ = resolve_temporal_anchor_chain_v1([row, dict(row)], chain_id="c3")
    assert r == "unresolved"


def test_resolve_unresolved_on_export_conflict_flag() -> None:
    a1 = {"observed_at_iso": "2020-01-01T00:00:00Z", "export_sequence": 1, "raw_record_id": 1}
    a2 = {"observed_at_iso": "2020-01-02T00:00:00Z", "export_sequence": 2, "raw_record_id": 2}
    _, r, _, _ = resolve_temporal_anchor_chain_v1(
        [a1, a2], chain_id="c4", export_sequence_conflict=True
    )
    assert r == "unresolved"


def test_verify_gp06_tar02_static() -> None:
    assert verify_gp06_tar02_declare_replay_safe_ordering_static()["passed"] is True


def test_spec_file_exists() -> None:
    start = Path(__file__).resolve()
    for root in [start, *start.parents]:
        p = root / "DOCS" / "cortex" / "reasoning" / "temporal-anchor-resolution-spec.md"
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            assert "temporal_anchor_resolution_order_v1" in text
            assert "replay_safe_ordering" in text
            return
    pytest.fail("temporal-anchor-resolution-spec.md not found")


def test_validate_inputs_rejects_non_mapping_anchor() -> None:
    with pytest.raises(TemporalAnchorResolutionError):
        validate_temporal_anchor_resolution_inputs_v1([{"export_sequence": 1}])
    with pytest.raises(TemporalAnchorResolutionError):
        validate_temporal_anchor_resolution_inputs_v1([[]])  # type: ignore[list-item]


def test_declare_default_ingest_sequence_is_sorted_sequence() -> None:
    """When ``ingest_sequence`` omitted, caller-supplied ``sorted_anchors`` is both orders."""
    a = {"observed_at_iso": "2020-01-01T00:00:00Z", "export_sequence": 1, "raw_record_id": 1}
    b = {"observed_at_iso": "2020-01-02T00:00:00Z", "export_sequence": 2, "raw_record_id": 2}
    s = sort_anchors_temporal_anchor_resolution_order_v1([b, a])
    assert declare_replay_safe_ordering_v1(s) == "strict"


def test_package_reexports_resolve() -> None:
    from vector.domains.cortex.reasoning import resolve_temporal_anchor_chain_v1 as r

    rows, ordering, _, _ = r(
        [{"observed_at_iso": "2020-01-01T00:00:00Z", "export_sequence": 1, "raw_record_id": 1}],
        chain_id="x",
    )
    assert ordering == "strict"
    assert len(rows) == 1
