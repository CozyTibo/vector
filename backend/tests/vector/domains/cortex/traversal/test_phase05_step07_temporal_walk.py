"""P05-07 — temporal walk (anchor laws, **G-P05-TEMP-01**, **G-P05-TEMP-02**)."""

from __future__ import annotations

import json

import pytest

from vector.domains.cortex.traversal.temporal_walk import (
    MAX_CLOCK_SKEW_NS,
    TW_RUNTIME_SCHEMA_VERSION,
    TemporalWalkInvariantError,
    list_export_sequence_monotonicity_violations_v1,
    list_superseded_link_still_present_violations_v1,
    octs_temporal_fixture_dir,
    org_link_eligible_half_open_unix_ns_v1,
    temporal_anchor_canonical_json_bytes_v1,
    validate_graph_as_of_vs_snapshot_clock_skew_v1,
    validate_temporal_anchor_invariants_v1,
    verify_gp05_temp01_sequence_validity_supersession_static,
    verify_gp05_temp02_anchor_roundtrip_and_concurrency_static,
)


def test_tw_runtime_schema_version() -> None:
    assert TW_RUNTIME_SCHEMA_VERSION >= 1


def test_verify_gp05_temp01_static_passes() -> None:
    out = verify_gp05_temp01_sequence_validity_supersession_static()
    assert out["id"] == "G-P05-TEMP-01"
    assert out["passed"] is True


def test_verify_gp05_temp02_static_passes() -> None:
    out = verify_gp05_temp02_anchor_roundtrip_and_concurrency_static()
    assert out["id"] == "G-P05-TEMP-02"
    assert out["passed"] is True


def test_temporal_fixture_dir_resolves() -> None:
    d = octs_temporal_fixture_dir()
    assert (d / "anchor_good_v1.json").is_file()


def test_anchor_round_trip_stable() -> None:
    path = octs_temporal_fixture_dir() / "anchor_good_v1.json"
    anchor = json.loads(path.read_text(encoding="utf-8"))
    b1 = temporal_anchor_canonical_json_bytes_v1(anchor)
    b2 = temporal_anchor_canonical_json_bytes_v1(json.loads(b1.decode("utf-8")))
    assert b1 == b2


def test_clock_skew_rejects_out_of_band() -> None:
    anchor = {
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "export_id": "00000000-0000-0000-0000-000000000002",
        "export_sequence": 1,
        "projection_content_hash": "sha256:" + "b" * 64,
        "snapshot_unix_ns": {"unix_ns": 1_000_000_000_000_000_000},
        "graph_as_of_unix_ns": {"unix_ns": 1_000_000_000_000_000_000 + MAX_CLOCK_SKEW_NS + 1},
    }
    with pytest.raises(TemporalWalkInvariantError, match="TW-02"):
        validate_graph_as_of_vs_snapshot_clock_skew_v1(anchor)


def test_graph_as_of_must_be_exactly_unix_ns_object() -> None:
    anchor = {
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "export_id": "00000000-0000-0000-0000-000000000002",
        "export_sequence": 1,
        "projection_content_hash": "sha256:" + "c" * 64,
        "snapshot_unix_ns": {"unix_ns": 0},
        "graph_as_of_unix_ns": {"unix_ns": 0, "note": "2024-01-01T00:00:00Z"},
    }
    with pytest.raises(TemporalWalkInvariantError, match="ISO-like"):
        validate_temporal_anchor_invariants_v1(anchor)


def test_float_rejected() -> None:
    anchor = {
        "tenant_id": "00000000-0000-0000-0000-000000000001",
        "export_id": "00000000-0000-0000-0000-000000000002",
        "export_sequence": 1.0,
        "projection_content_hash": "sha256:" + "d" * 64,
        "snapshot_unix_ns": {"unix_ns": 0},
        "graph_as_of_unix_ns": {"unix_ns": 0},
    }
    with pytest.raises(TemporalWalkInvariantError, match="floats"):
        validate_temporal_anchor_invariants_v1(anchor)


def test_supersession_detector() -> None:
    path = octs_temporal_fixture_dir() / "supersession_edges_bad_v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    v = list_superseded_link_still_present_violations_v1(data["edges"])
    assert any("22222222" in x for x in v)


def test_sequence_gap_detected() -> None:
    rows = [(1, "a"), (2, "b"), (4, "c")]
    assert list_export_sequence_monotonicity_violations_v1(rows)


def test_half_open_boundary() -> None:
    assert org_link_eligible_half_open_unix_ns_v1(
        valid_from_unix_ns=10,
        valid_to_unix_ns=20,
        graph_as_of_unix_ns=20,
    ) is False
