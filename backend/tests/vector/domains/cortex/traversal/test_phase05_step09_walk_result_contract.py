"""P05-09 — walk result contract (**G-P05-HASH-01**, **G-P05-HASH-02**)."""

from __future__ import annotations

import json

import pytest

from vector.domains.cortex.traversal.walk_result_contract import (
    WR_RUNTIME_SCHEMA_VERSION,
    WalkResultContractError,
    canonical_walk_result_hash_body_bytes_v1,
    extract_walk_result_hash_body_v1,
    list_fs_wr03_duplicate_hop_sequence_violations,
    list_wr02_forbidden_key_violations_under_hash_body,
    octs_walk_result_fixture_dir,
    validate_walk_result_hash_body_contract_v1,
    verify_gp05_hash01_walk_result_hash_recompute_static,
    verify_gp05_hash02_telemetry_separation_static,
)

_SHA256_A = "sha256:" + "a" * 64


def test_wr_runtime_schema_version() -> None:
    assert WR_RUNTIME_SCHEMA_VERSION >= 1


def test_verify_gp05_hash01_static_passes() -> None:
    out = verify_gp05_hash01_walk_result_hash_recompute_static()
    assert out["id"] == "G-P05-HASH-01"
    assert out["passed"] is True


def test_verify_gp05_hash02_static_passes() -> None:
    out = verify_gp05_hash02_telemetry_separation_static()
    assert out["id"] == "G-P05-HASH-02"
    assert out["passed"] is True


def test_fixture_dir() -> None:
    d = octs_walk_result_fixture_dir()
    assert (d / "hash_body_minimal_v1.json").is_file()


def test_start_node_ids_sorted_in_canonical_bytes() -> None:
    body = {
        "octs_schema_version": 1,
        "temporal_anchor": {
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "export_id": "00000000-0000-0000-0000-000000000002",
            "export_sequence": 1,
            "projection_content_hash": _SHA256_A,
            "snapshot_unix_ns": {"unix_ns": 1},
            "graph_as_of_unix_ns": {"unix_ns": 1},
        },
        "policy_hash": "sha256:" + "b" * 64,
        "start_node_ids": [
            "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        ],
        "termination_reason": "x",
        "hop_receipts": [],
        "execution_path_contains_derived": False,
        "path_edge_fingerprints_ordered": [],
    }
    b1 = canonical_walk_result_hash_body_bytes_v1(body)
    body2 = {
        **body,
        "start_node_ids": [
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        ],
    }
    b2 = canonical_walk_result_hash_body_bytes_v1(body2)
    assert b1 == b2


def test_wr02_rejects_wall_ms_key() -> None:
    body = {
        "octs_schema_version": 1,
        "temporal_anchor": {
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "export_id": "00000000-0000-0000-0000-000000000002",
            "export_sequence": 1,
            "projection_content_hash": _SHA256_A,
            "snapshot_unix_ns": {"unix_ns": 1},
            "graph_as_of_unix_ns": {"unix_ns": 1},
        },
        "policy_hash": "sha256:" + "c" * 64,
        "start_node_ids": ["00000000-0000-0000-0000-000000000003"],
        "termination_reason": "x",
        "hop_receipts": [],
        "execution_path_contains_derived": False,
        "path_edge_fingerprints_ordered": [],
        "wall_ms": 3,
    }
    v = list_wr02_forbidden_key_violations_under_hash_body(body, "")
    assert v


def test_fs_wr03_duplicate_hop_sequence() -> None:
    hr = [
        {"hop_sequence": 0, "edge_fingerprint": "sha256:" + "0" * 64},
        {"hop_sequence": 0, "edge_fingerprint": "sha256:" + "1" * 64},
    ]
    assert list_fs_wr03_duplicate_hop_sequence_violations(hr)


def test_extract_hash_body_from_response() -> None:
    path = octs_walk_result_fixture_dir() / "walk_response_telemetry_variants_v1.json"
    bundle = json.loads(path.read_text(encoding="utf-8"))
    a = extract_walk_result_hash_body_v1(bundle["variant_a"])
    b = extract_walk_result_hash_body_v1(bundle["variant_b"])
    assert a == b


def test_nested_telemetry_fixture_rejected() -> None:
    path = octs_walk_result_fixture_dir() / "hash_body_nested_telemetry_bad_v1.json"
    bad = json.loads(path.read_text(encoding="utf-8"))
    with pytest.raises(WalkResultContractError):
        validate_walk_result_hash_body_contract_v1(bad)
