"""P05-06 — multigraph model (fingerprints, MG-01 neighbor order, MG-02 collisions)."""

from __future__ import annotations

import json

import pytest

from vector.domains.cortex.identity.projection_export import ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF
from vector.domains.cortex.traversal.multigraph_model import (
    MG_RUNTIME_SCHEMA_VERSION,
    MultigraphModelError,
    canonical_diagnostic_multiset_fingerprints_v1,
    compute_edge_fingerprint_v1,
    edge_eligible_at_t_as_of_unix_ns,
    list_fs_mg01_duplicate_fingerprint_violations,
    neighbor_expansion_fingerprints_ordered_v1,
    octs_multigraph_neighbor_order_fixture_dir,
    verify_gp05_mg01_neighbor_order_golden_static,
    verify_gp05_mg02_fingerprint_uniqueness_static,
)


def test_mg_runtime_schema_version() -> None:
    assert MG_RUNTIME_SCHEMA_VERSION >= 1


def test_verify_gp05_mg01_static_passes() -> None:
    out = verify_gp05_mg01_neighbor_order_golden_static()
    assert out["id"] == "G-P05-MG-01"
    assert out["passed"] is True


def test_verify_gp05_mg02_static_passes() -> None:
    out = verify_gp05_mg02_fingerprint_uniqueness_static()
    assert out["id"] == "G-P05-MG-02"
    assert out["passed"] is True


def test_neighbor_order_independent_of_edge_list_order() -> None:
    """**FS-MG-02** — expansion order does not follow DB / list insertion order."""
    n1 = "11111111-1111-1111-1111-111111111111"
    n2 = "22222222-2222-2222-2222-222222222222"

    def edge(eid: str, stable: str) -> dict:
        return {
            "kind": "org_meaning_link",
            "id": eid,
            "link_type": "org.handle_links_canonical",
            "source_entity_id": n1,
            "target_entity_id": n2,
            "link_class": "authoritative",
            "link_authority": "authoritative",
            "confidence_class": "declared",
            "evidence_raw_record_ids": [1, 2],
            "rule_id": None,
            "valid_from": None,
            "valid_to": None,
            "revoked_at": None,
            "supersedes_link_id": None,
            "promoted_from_candidate_id": None,
            "promotion_policy_id": None,
            "link_row_stable_id": stable,
        }

    e1 = edge("00000000-0000-0000-0000-000000000001", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    e2 = edge("00000000-0000-0000-0000-000000000002", "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    e3 = edge("00000000-0000-0000-0000-000000000003", "cccccccc-cccc-cccc-cccc-cccccccccccc")
    forward = neighbor_expansion_fingerprints_ordered_v1([e1, e2, e3], source_node_id=n1)
    backward = neighbor_expansion_fingerprints_ordered_v1([e3, e1, e2], source_node_id=n1)
    assert forward == backward


def test_parallel_edges_distinct_fingerprints() -> None:
    """**INVARIANT EFP-02** — different ``link_row_stable_id`` ⇒ different fingerprint."""
    n1 = "11111111-1111-1111-1111-111111111111"
    n2 = "22222222-2222-2222-2222-222222222222"

    def edge(eid: str, stable: str) -> dict:
        return {
            "kind": "org_meaning_link",
            "id": eid,
            "link_type": "org.handle_links_canonical",
            "source_entity_id": n1,
            "target_entity_id": n2,
            "link_class": "authoritative",
            "link_authority": "authoritative",
            "confidence_class": "declared",
            "evidence_raw_record_ids": [1, 2],
            "rule_id": None,
            "valid_from": None,
            "valid_to": None,
            "revoked_at": None,
            "supersedes_link_id": None,
            "promoted_from_candidate_id": None,
            "promotion_policy_id": None,
            "link_row_stable_id": stable,
        }

    a = edge("00000000-0000-0000-0000-000000000001", "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    b = edge("00000000-0000-0000-0000-000000000002", "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    assert compute_edge_fingerprint_v1(a) != compute_edge_fingerprint_v1(b)


def test_temporal_filter_before_ordering() -> None:
    """**§6** — ineligible edges excluded before **RULE MG-01** sort."""
    n1 = "11111111-1111-1111-1111-111111111111"
    n2 = "22222222-2222-2222-2222-222222222222"
    expired = {
        "kind": "org_meaning_link",
        "id": "00000000-0000-0000-0000-000000000099",
        "link_type": "org.handle_links_canonical",
        "source_entity_id": n1,
        "target_entity_id": n2,
        "link_class": "authoritative",
        "link_authority": "authoritative",
        "confidence_class": "declared",
        "evidence_raw_record_ids": [1, 2],
        "rule_id": None,
        "valid_from": "1970-01-01T00:00:00Z",
        "valid_to": "1970-01-02T00:00:00Z",
        "revoked_at": None,
        "supersedes_link_id": None,
        "promoted_from_candidate_id": None,
        "promotion_policy_id": None,
        "link_row_stable_id": "dddddddd-dddd-dddd-dddd-dddddddddddd",
    }
    t_late = 1700000000000000000  # ns ≈ 2023 — after valid_to
    assert not edge_eligible_at_t_as_of_unix_ns(expired, t_late)
    active = {
        "kind": "org_meaning_link",
        "id": "00000000-0000-0000-0000-000000000001",
        "link_type": "org.handle_links_canonical",
        "source_entity_id": n1,
        "target_entity_id": n2,
        "link_class": "authoritative",
        "link_authority": "authoritative",
        "confidence_class": "declared",
        "evidence_raw_record_ids": [1, 2],
        "rule_id": None,
        "valid_from": None,
        "valid_to": None,
        "revoked_at": None,
        "supersedes_link_id": None,
        "promoted_from_candidate_id": None,
        "promotion_policy_id": None,
        "link_row_stable_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    }
    ordered = neighbor_expansion_fingerprints_ordered_v1(
        [expired, active], source_node_id=n1, t_as_of_unix_ns=t_late
    )
    assert ordered == [compute_edge_fingerprint_v1(active)]


def test_diagnostic_multiset_sorts() -> None:
    a = "sha256:" + "b" * 64
    b = "sha256:" + "a" * 64
    assert canonical_diagnostic_multiset_fingerprints_v1([a, b]) == sorted([a, b])


def test_compute_fingerprint_rejects_missing_fields() -> None:
    with pytest.raises(MultigraphModelError, match="missing required field"):
        compute_edge_fingerprint_v1({"kind": "org_meaning_link", "id": "x"})


def test_fs_mg01_lists_distinct_links_same_inputs() -> None:
    sid = "11111111-1111-1111-1111-111111111111"
    tid = "22222222-2222-2222-2222-222222222222"
    stable = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
    base = {
        "kind": "org_meaning_link",
        "link_type": "org.handle_links_canonical",
        "source_entity_id": sid,
        "target_entity_id": tid,
        "link_class": "authoritative",
        "link_authority": "authoritative",
        "confidence_class": "declared",
        "evidence_raw_record_ids": [1],
        "rule_id": None,
        "valid_from": None,
        "valid_to": None,
        "revoked_at": None,
        "supersedes_link_id": None,
        "promoted_from_candidate_id": None,
        "promotion_policy_id": None,
        "link_row_stable_id": stable,
    }
    v = list_fs_mg01_duplicate_fingerprint_violations(
        [{**base, "id": "00000000-0000-0000-0000-0000000000a1"}, {**base, "id": "00000000-0000-0000-0000-0000000000b2"}]
    )
    assert v


def test_golden_fixture_dir_resolves() -> None:
    d = octs_multigraph_neighbor_order_fixture_dir()
    assert (d / "neighbor_order_inner_v1.json").is_file()


def test_golden_inner_matches_engine_ref_in_repo() -> None:
    path = octs_multigraph_neighbor_order_fixture_dir() / "neighbor_order_inner_v1.json"
    inner = json.loads(path.read_text(encoding="utf-8"))
    assert inner.get("engine_build_ref") == ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF
