"""Phase 03 Step 1 — structural ontology frozen definitions."""

from __future__ import annotations

import uuid

from vector.domains.cortex.canonical.ontology import (
    ONTOLOGY_SCHEMA_VERSION,
    CanonicalLayerKind,
    CanonicalObjectKind,
    CanonicalStructuralEdgeKind,
    build_phase03_step01_ontology_public_document,
    is_known_object_kind,
    layer_for_kind,
)


def test_ontology_schema_version_stable() -> None:
    assert ONTOLOGY_SCHEMA_VERSION == 20


def test_layer_maps_every_object_kind() -> None:
    for k in CanonicalObjectKind:
        layer_for_kind(k)


def test_public_document_shape_and_sorted_ids() -> None:
    tid = uuid.uuid4()
    doc = build_phase03_step01_ontology_public_document(tenant_id=tid)
    assert doc["ontology_schema_version"] == ONTOLOGY_SCHEMA_VERSION
    assert doc["phase"] == "03"
    assert doc["implementation_step"] == 18
    assert doc["completed_implementation_steps"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]
    assert doc["tenant_id"] == str(tid)
    ids = [x["id"] for x in doc["object_kinds"]]
    assert ids == sorted(ids)
    k0 = doc["object_kinds"][0]
    assert set(k0.keys()) >= {
        "id",
        "layer",
        "taxonomy_family",
        "structural_role",
        "structural_examples",
        "description",
    }
    assert doc["taxonomy_families"]
    assert doc["kind_taxonomy"]
    assert doc["taxonomy_hard_rules"]
    assert doc["logical_key_profile_version"] >= 1
    assert doc["logical_keys_by_kind"]
    assert doc["mapping_contract_schema_version"] >= 1
    assert doc["evidence_grades"]
    assert doc["forbidden_operations"]
    assert doc["mapping_table_row_shape"]
    assert doc["mapping_registry_surface_version"] >= 1
    assert doc["mapping_registry_admin_route"]
    assert doc["transform_runtime_surface_version"] >= 1
    assert doc["transform_materialize_route"]
    assert doc["transform_lineage_route"]
    assert doc["transform_runtime_doctrine_anchors"]
    assert doc["ambiguity_runtime_surface_version"] >= 1
    assert doc["ambiguity_list_route"]
    assert doc["ambiguity_open_route"]
    assert doc["ambiguity_detail_route"]
    assert doc["ambiguity_lifecycle_route"]
    assert doc["ambiguity_runtime_doctrine_anchors"]
    assert doc["transform_lineage_includes_confidence"] is True
    assert doc["confidence_propagation_schema_version"] >= 1
    assert doc["confidence_summary_admin_route"]
    assert doc["confidence_allowed_classes"]
    assert doc["confidence_forbidden_classes"]
    assert doc["identity_runtime_surface_version"] >= 1
    assert doc["identity_anchors_list_route"]
    assert doc["identity_anchor_detail_route"]
    assert doc["identity_runtime_doctrine_anchors"]
    assert doc["replay_job_run_route"]
    assert doc["replay_jobs_list_route"]
    assert doc["replay_job_detail_route"]
    assert doc["replay_divergence_taxonomy"]
    assert doc["provenance_by_raw_record_route"]
    assert doc["provenance_by_materialization_route"]
    assert doc["temporal_supersessions_list_route"]
    assert doc["temporal_rebuild_preview_route"]
    assert doc["temporal_ordering_precedence"]
    assert doc["transform_persists_temporal_ordering"] is True
    assert doc["canonical_query_route"]
    assert doc["canonical_query_classes"]
    assert doc["canonical_control_plane_surface_version"] >= 1
    assert "control-plane" in doc["canonical_control_plane_route"]
    assert doc["canonical_control_plane_doctrine_anchors"]
    assert doc["stabilization_proof_surface_version"] >= 1
    assert "stabilization-proof" in doc["canonical_stabilization_proof_route"]
    assert "stabilization-proof/run" in doc["canonical_stabilization_proof_run_route"]
    assert doc["stabilization_proof_doctrine_anchors"]
    assert doc["certification_pack_surface_version"] >= 1
    assert "certification-pack" in doc["canonical_certification_pack_route"]
    assert "certification-pack/archive" in doc["canonical_certification_pack_archive_route"]
    assert "certification-pack/archives" in doc["canonical_certification_pack_archives_route"]
    assert doc["certification_pack_doctrine_anchors"]
    assert len(doc["structural_arcs"]) >= 1
    arc = doc["structural_arcs"][0]
    assert set(arc.keys()) == {"from_kind", "edge_kind", "to_kind"}


def test_is_known_object_kind() -> None:
    assert is_known_object_kind("person") is True
    assert is_known_object_kind("not_a_kind") is False


def test_enums_include_expected_discriminants() -> None:
    assert CanonicalLayerKind.ENTITY.value == "entity"
    assert CanonicalStructuralEdgeKind.CONTAINED_IN.value == "contained_in"
