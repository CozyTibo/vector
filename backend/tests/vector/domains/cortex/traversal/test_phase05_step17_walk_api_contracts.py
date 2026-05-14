"""P05-17 — walk HTTP API contracts (**RULE API-0**, **RULE API-ERR**, **G-P05-API-01/02**)."""

from __future__ import annotations

import json

import pytest

from vector.domains.cortex.traversal.traversal_vs_reasoning import (
    TraversalReasoningBoundaryError,
    oct_walk_request_minimal_fixture_path,
    validate_oct_walk_request_v1,
)
from vector.domains.cortex.traversal.walk_api_contract import (
    API_WALK_CONTRACT_SCHEMA_VERSION,
    canonical_octs_api_error_body_v1,
    octs_walk_api_openapi_path,
    verify_gp05_api01_openapi_walk_paths_static,
    verify_gp05_api02_openapi_security_static,
    verify_gp05_api03_sync_walk_limits_static,
)


def test_api_walk_contract_schema_version() -> None:
    assert API_WALK_CONTRACT_SCHEMA_VERSION >= 3


def test_verify_gp05_api01_static_passes() -> None:
    out = verify_gp05_api01_openapi_walk_paths_static()
    assert out["id"] == "G-P05-API-01"
    assert out["passed"] is True


def test_verify_gp05_api02_static_passes() -> None:
    out = verify_gp05_api02_openapi_security_static()
    assert out["id"] == "G-P05-API-02"
    assert out["passed"] is True


def test_verify_gp05_api03_static_passes() -> None:
    out = verify_gp05_api03_sync_walk_limits_static()
    assert out["id"] == "G-P05-API-03"
    assert out["passed"] is True


def test_octs_walk_api_openapi_path_exists() -> None:
    p = octs_walk_api_openapi_path()
    assert p.is_file()


def test_canonical_octs_api_error_body_sorted_details() -> None:
    body = canonical_octs_api_error_body_v1("x", {"z": 1, "a": "b"})
    assert body["error_code"] == "x"
    assert list(body["details"].keys()) == ["a", "z"]


def test_oct_walk_request_schema_anyof_temporal_or_inherit() -> None:
    inner = {
        "inherit_walk_id": "00000000-0000-4000-8000-000000000099",
        "walk_policy": {
            "max_hops": 8,
            "max_frontier": 64,
            "max_edges_visited": 500,
            "max_wall_ms": 100,
            "hop_class_allowlist": ["org.handle_links_canonical"],
            "tie_break": ["fingerprint", "org_link_id"],
            "respect_validity": True,
            "policy_version": 1,
        },
        "start_node_ids": ["00000000-0000-0000-0000-000000000003"],
        "walk_execution_strategy": "ONLINE_OBSERVED",
        "exploration_mode": False,
    }
    validate_oct_walk_request_v1(inner)

    bad = {k: v for k, v in inner.items() if k != "inherit_walk_id"}
    with pytest.raises(TraversalReasoningBoundaryError):
        validate_oct_walk_request_v1(bad)


def test_walk_request_minimal_fixture_still_validates() -> None:
    p = oct_walk_request_minimal_fixture_path()
    data = json.loads(p.read_text(encoding="utf-8"))
    validate_oct_walk_request_v1(data)
