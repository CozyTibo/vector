"""P05-04 — graph import boundary (OrgGraphProjectionV1 for OCTS)."""

from __future__ import annotations

import uuid

import pytest

from vector.domains.cortex.identity.projection_export import (
    ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF,
    org_graph_projection_stable_hash_sha256,
)
from vector.domains.cortex.traversal.graph_import_boundary import (
    GIB_RUNTIME_SCHEMA_VERSION,
    GraphImportBoundaryError,
    list_oct_graph_import_violations,
    validate_inner_projection_matches_stable_hash,
    validate_oct_traversal_import_projection,
    validate_temporal_anchor_has_projection_content_hash,
    verify_gp05_import01_traversable_subset_authoritative_static,
    verify_gp05_import02_forbidden_ingress_tokens_static,
)


def test_gib_runtime_schema_version() -> None:
    assert GIB_RUNTIME_SCHEMA_VERSION >= 1


def test_validate_oct_traversal_import_projection_accepts_authoritative_edge() -> None:
    eid = str(uuid.uuid4())
    inner = {
        "projection_schema_version": 1,
        "tenant_id": str(uuid.UUID(int=0)),
        "engine_build_ref": ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF,
        "nodes": [
            {
                "kind": "org_entity",
                "id": str(uuid.UUID(int=1)),
                "entity_kind": "human_actor",
                "identity_key_fingerprint": "fp",
                "lifecycle_state": "active",
                "tombstoned_at": None,
            }
        ],
        "edges": [
            {
                "kind": "org_meaning_link",
                "id": eid,
                "link_type": "org.handle_links_canonical",
                "source_entity_id": str(uuid.UUID(int=1)),
                "target_entity_id": str(uuid.UUID(int=1)),
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
                "link_row_stable_id": eid,
            }
        ],
    }
    inner["nodes"].sort(key=lambda x: str(x["id"]))
    inner["edges"].sort(key=lambda x: str(x["id"]))
    validate_oct_traversal_import_projection(inner)


def test_rejects_hint_authority_edge() -> None:
    eid = str(uuid.uuid4())
    inner = {
        "projection_schema_version": 1,
        "tenant_id": str(uuid.UUID(int=0)),
        "engine_build_ref": ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF,
        "nodes": [
            {
                "kind": "org_entity",
                "id": str(uuid.UUID(int=1)),
                "entity_kind": "human_actor",
                "identity_key_fingerprint": "fp",
                "lifecycle_state": "active",
                "tombstoned_at": None,
            }
        ],
        "edges": [
            {
                "kind": "org_meaning_link",
                "id": eid,
                "link_type": "org.handle_links_canonical",
                "source_entity_id": str(uuid.UUID(int=1)),
                "target_entity_id": str(uuid.UUID(int=1)),
                "link_class": "hint",
                "link_authority": "non_authoritative",
                "confidence_class": "inferred",
                "evidence_raw_record_ids": [1],
                "rule_id": None,
                "valid_from": None,
                "valid_to": None,
                "revoked_at": None,
                "supersedes_link_id": None,
                "promoted_from_candidate_id": None,
                "promotion_policy_id": None,
                "link_row_stable_id": eid,
            }
        ],
    }
    inner["nodes"].sort(key=lambda x: str(x["id"]))
    inner["edges"].sort(key=lambda x: str(x["id"]))
    with pytest.raises(GraphImportBoundaryError, match="authoritative"):
        validate_oct_traversal_import_projection(inner)


def test_validate_inner_projection_matches_stable_hash() -> None:
    inner = {
        "projection_schema_version": 1,
        "tenant_id": str(uuid.UUID(int=0)),
        "engine_build_ref": ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF,
        "nodes": [
            {
                "kind": "org_entity",
                "id": str(uuid.UUID(int=1)),
                "entity_kind": "human_actor",
                "identity_key_fingerprint": "fp",
                "lifecycle_state": "active",
                "tombstoned_at": None,
            }
        ],
        "edges": [],
    }
    h = org_graph_projection_stable_hash_sha256(inner)
    validate_inner_projection_matches_stable_hash(inner, expected_stable_hash_sha256=h)
    with pytest.raises(GraphImportBoundaryError, match="mismatch"):
        validate_inner_projection_matches_stable_hash(inner, expected_stable_hash_sha256="0" * 64)


def test_validate_temporal_anchor_projection_content_hash() -> None:
    validate_temporal_anchor_has_projection_content_hash(
        {"projection_content_hash": "sha256:abc", "tenant_id": "x"}
    )
    with pytest.raises(GraphImportBoundaryError, match="FS-GIB-03"):
        validate_temporal_anchor_has_projection_content_hash({})


def test_verify_gp05_import01_static_passes() -> None:
    out = verify_gp05_import01_traversable_subset_authoritative_static()
    assert out["id"] == "G-P05-IMPORT-01"
    assert out["passed"] is True


def test_verify_gp05_import02_static_passes() -> None:
    out = verify_gp05_import02_forbidden_ingress_tokens_static()
    assert out["id"] == "G-P05-IMPORT-02"
    assert out["passed"] is True


def test_list_oct_graph_import_violations_empty_for_nodes_only() -> None:
    inner = {
        "projection_schema_version": 1,
        "tenant_id": str(uuid.UUID(int=0)),
        "engine_build_ref": ORG_GRAPH_PROJECTION_ENGINE_BUILD_REF,
        "nodes": [
            {
                "kind": "org_entity",
                "id": str(uuid.UUID(int=1)),
                "entity_kind": "human_actor",
                "identity_key_fingerprint": "fp",
                "lifecycle_state": "active",
                "tombstoned_at": None,
            }
        ],
        "edges": [],
    }
    assert list_oct_graph_import_violations(inner) == []
