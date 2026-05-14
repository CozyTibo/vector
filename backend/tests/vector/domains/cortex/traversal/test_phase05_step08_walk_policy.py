"""P05-08 — walk policy (**G-P05-POL-01**, **G-P05-POL-02**)."""

from __future__ import annotations

import pytest

from vector.domains.cortex.traversal.walk_policy import (
    SYNC_MAX_HOPS,
    WP_RUNTIME_SCHEMA_VERSION,
    WalkPolicyInvariantError,
    list_walk_policy_sync_cap_violations_v1,
    octs_walk_policy_fixture_dir,
    validate_oct_walk_policy_v1_jsonschema,
    validate_walk_policy_for_request_v1,
    verify_gp05_pol01_walk_policy_schema_and_hash_static,
    verify_gp05_pol02_sync_caps_reject_static,
    walk_policy_canonical_json_bytes_for_hash_v1,
)


def test_wp_runtime_schema_version() -> None:
    assert WP_RUNTIME_SCHEMA_VERSION >= 1


def test_verify_gp05_pol01_static_passes() -> None:
    out = verify_gp05_pol01_walk_policy_schema_and_hash_static()
    assert out["id"] == "G-P05-POL-01"
    assert out["passed"] is True


def test_verify_gp05_pol02_static_passes() -> None:
    out = verify_gp05_pol02_sync_caps_reject_static()
    assert out["id"] == "G-P05-POL-02"
    assert out["passed"] is True


def test_fixture_dir_resolves() -> None:
    d = octs_walk_policy_fixture_dir()
    assert (d / "bundle_good_v1.json").is_file()


def test_policy_hash_stable_on_key_order() -> None:
    p1 = {"max_hops": 3, "hop_class_allowlist": ["a"], "tie_break": ["fingerprint"]}
    p2 = {"tie_break": ["fingerprint"], "max_hops": 3, "hop_class_allowlist": ["a"]}
    h = "ONLINE_OBSERVED"
    assert walk_policy_canonical_json_bytes_for_hash_v1(
        p1, walk_execution_strategy=h
    ) == walk_policy_canonical_json_bytes_for_hash_v1(p2, walk_execution_strategy=h)


def test_strips_human_label_from_hash_material() -> None:
    base = {
        "max_hops": 2,
        "hop_class_allowlist": ["x"],
        "tie_break": ["fingerprint"],
        "human_label": "do not hash",
    }
    b1 = walk_policy_canonical_json_bytes_for_hash_v1(base, walk_execution_strategy="ONLINE_OBSERVED")
    b2 = walk_policy_canonical_json_bytes_for_hash_v1(
        {k: v for k, v in base.items() if k != "human_label"},
        walk_execution_strategy="ONLINE_OBSERVED",
    )
    assert b1 == b2


def test_wildcard_hop_requires_exploration() -> None:
    pol = {
        "max_hops": 4,
        "hop_class_allowlist": ["*"],
        "tie_break": ["fingerprint"],
    }
    with pytest.raises(WalkPolicyInvariantError, match="fs_wp_02"):
        validate_walk_policy_for_request_v1(
            pol,
            walk_execution_strategy="ONLINE_OBSERVED",
            exploration_mode=False,
            enforce_sync_caps=False,
        )


def test_sync_caps_detect_max_hops() -> None:
    pol = {
        "max_hops": SYNC_MAX_HOPS + 1,
        "hop_class_allowlist": ["org.handle_links_canonical"],
        "tie_break": ["fingerprint"],
    }
    v = list_walk_policy_sync_cap_violations_v1(pol)
    assert v


def test_edge_weights_rejected() -> None:
    pol = {
        "max_hops": 2,
        "hop_class_allowlist": ["a"],
        "tie_break": ["fingerprint"],
        "edge_weights": {"x": 1},
    }
    with pytest.raises(WalkPolicyInvariantError, match="schema violation"):
        validate_oct_walk_policy_v1_jsonschema(pol)
