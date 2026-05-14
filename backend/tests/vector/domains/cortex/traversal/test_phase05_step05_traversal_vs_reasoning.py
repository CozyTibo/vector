"""P05-05 — traversal vs reasoning (TVR strict closure + JSON Schema walk request)."""

from __future__ import annotations

import json

import pytest

from vector.domains.cortex.traversal.traversal_vs_reasoning import (
    TVR_RUNTIME_SCHEMA_VERSION,
    TraversalReasoningBoundaryError,
    list_walk_result_hash_body_unknown_keys_v1,
    oct_walk_request_minimal_fixture_path,
    validate_oct_walk_request_v1,
    validate_walk_result_hash_body_tvr_strict_v1,
    verify_gp05_schema01_oct_walk_request_v1_static,
    verify_gp05_tvr01_walk_result_hash_body_strict_static,
)


def test_tvr_runtime_schema_version() -> None:
    assert TVR_RUNTIME_SCHEMA_VERSION >= 1


def test_validate_minimal_walk_request_fixture() -> None:
    path = oct_walk_request_minimal_fixture_path()
    assert path.is_file(), f"golden fixture missing: {path}"
    raw = json.loads(path.read_text(encoding="utf-8"))
    validate_oct_walk_request_v1(raw)


def test_validate_oct_walk_request_rejects_extra_top_level() -> None:
    path = oct_walk_request_minimal_fixture_path()
    raw = json.loads(path.read_text(encoding="utf-8"))
    bad = {**raw, "extra": 1}
    with pytest.raises(TraversalReasoningBoundaryError, match="schema violation"):
        validate_oct_walk_request_v1(bad)


def test_hash_body_strict_allowlist() -> None:
    body = {
        "octs_schema_version": 1,
        "temporal_anchor": {},
        "policy_hash": "sha256:" + "c" * 64,
        "start_node_ids": [],
        "termination_reason": "budget_exhausted",
        "hop_receipts": [],
        "execution_path_contains_derived": False,
        "path_edge_fingerprints_ordered": [],
    }
    validate_walk_result_hash_body_tvr_strict_v1(body)
    extras = list_walk_result_hash_body_unknown_keys_v1({**body, "walk_result_hash": "x"})
    assert extras


def test_verify_gp05_tvr01_static_passes() -> None:
    out = verify_gp05_tvr01_walk_result_hash_body_strict_static()
    assert out["id"] == "G-P05-TVR-01"
    assert out["passed"] is True


def test_verify_gp05_schema01_static_passes() -> None:
    out = verify_gp05_schema01_oct_walk_request_v1_static()
    assert out["id"] == "G-P05-SCHEMA-01"
    assert out["passed"] is True


def test_repo_finds_schema_from_tests_dir() -> None:
    """Fixture path resolution must work when pytest cwd is ``backend`` (Docker ``/app``)."""
    p = oct_walk_request_minimal_fixture_path()
    assert p.is_file()
