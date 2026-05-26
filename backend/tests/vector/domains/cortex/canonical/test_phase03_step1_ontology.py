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
    assert ONTOLOGY_SCHEMA_VERSION == 41


def test_layer_maps_every_object_kind() -> None:
    for k in CanonicalObjectKind:
        layer_for_kind(k)


def test_public_document_shape_and_sorted_ids() -> None:
    tid = uuid.uuid4()
    doc = build_phase03_step01_ontology_public_document(tenant_id=tid)
    assert doc["ontology_schema_version"] == ONTOLOGY_SCHEMA_VERSION
    assert doc["phase"] == "03"
    assert doc["implementation_step"] == 22
    assert doc["completed_implementation_steps"] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]
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
    assert doc["org_entity_runtime_surface_version"] >= 1
    assert "cortex/identity/entities" in doc["org_entity_list_route"]
    assert "cortex/identity/entities" in doc["org_entity_detail_route"]
    assert "cortex/identity/handles" in doc["org_handle_explorer_list_route"]
    assert "cortex/identity/handles" in doc["org_handle_explorer_detail_route"]
    assert doc["org_entity_runtime_doctrine_anchors"]
    assert doc["link_ledger_runtime_surface_version"] >= 1
    assert doc["org_link_replay_runtime_surface_version"] >= 1
    assert "replay-jobs" in doc["org_link_replay_jobs_list_route"]
    assert "replay-jobs/run" in doc["org_link_replay_job_run_route"]
    assert doc["org_link_replay_drift_taxonomy"]
    assert "run_org_link_replay_job" in doc["celery_task_run_org_link_replay_job"]
    assert doc["link_rule_version_runtime_surface_version"] >= 1
    assert "link-rule-versions" in doc["link_rule_versions_list_route"]
    assert "link-rule-versions" in doc["link_rule_version_append_route"]
    assert doc["link_rule_version_runtime_doctrine_anchors"]
    assert doc["execution_primitive_persistence_surface_version"] >= 1
    assert "primitive-instances" in doc["org_primitive_instances_list_route"]
    assert "cortex/identity/primitives" in doc["org_primitive_explorer_list_route"]
    assert "primitive-instances" in doc["org_primitive_instance_append_route"]
    assert doc["execution_primitive_persistence_doctrine_anchors"]
    assert doc["org_graph_projection_export_surface_version"] >= 1
    assert "graph-projection" in doc["org_graph_projection_export_route"]
    assert "projection-preview" in doc["org_graph_projection_preview_route"]
    assert doc["org_graph_projection_export_doctrine_anchors"]
    assert doc["org_ambiguity_runtime_surface_version"] >= 1
    assert "org-ambiguities" in doc["org_ambiguities_list_route"]
    assert "ambiguity-queue" in doc["org_ambiguity_queue_list_route"]
    assert "org-ambiguities" in doc["org_ambiguity_append_route"]
    assert doc["org_ambiguity_runtime_doctrine_anchors"]
    assert "cortex/identity/links" in doc["link_ledger_list_route"]
    assert "cortex/identity/links" in doc["link_ledger_detail_route"]
    assert doc["link_ledger_runtime_doctrine_anchors"]
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
    assert "G-P04-08" in doc["verification_engine_gate_ids"]
    assert "G-P04-ORG-01" in doc["verification_engine_gate_ids"]
    assert "G-P04-LINK-01" in doc["verification_engine_gate_ids"]
    assert "G-P04-06" in doc["verification_engine_gate_ids"]
    assert "G-P04-04" in doc["verification_engine_gate_ids"]
    assert "G-P04-05" in doc["verification_engine_gate_ids"]
    assert "G-P04-CAND-01" in doc["verification_engine_gate_ids"]
    assert "G-P04-MRG-01" in doc["verification_engine_gate_ids"]
    assert "G-P04-01" in doc["verification_engine_gate_ids"]
    assert "G-P04-13" in doc["verification_engine_gate_ids"]
    assert "G-P04-02" in doc["verification_engine_gate_ids"]
    assert "G-P04-HINT-01" in doc["verification_engine_gate_ids"]
    assert "G-P04-TMP-01" in doc["verification_engine_gate_ids"]
    assert "G-P04-11" in doc["verification_engine_gate_ids"]
    assert "G-P04-BNDL-01" in doc["verification_engine_gate_ids"]
    assert "G-P04-03" in doc["verification_engine_gate_ids"]
    assert "G-P04-14" in doc["verification_engine_gate_ids"]
    assert "G-P04-RPL-01" in doc["verification_engine_gate_ids"]
    assert "G-P04-RULE-01" in doc["verification_engine_gate_ids"]
    assert "G-P04-09" in doc["verification_engine_gate_ids"]
    assert "G-P04-PRIM-01" in doc["verification_engine_gate_ids"]
    assert "G-P04-10" in doc["verification_engine_gate_ids"]
    assert "G-P04-EXP-01" in doc["verification_engine_gate_ids"]
    assert "G-P04-AMB-01" in doc["verification_engine_gate_ids"]
    assert "G-P04-12" in doc["verification_engine_gate_ids"]
    assert "G-P04-VER-01" in doc["verification_engine_gate_ids"]
    assert "G-P04-19" in doc["verification_engine_gate_ids"]
    assert "G-P04-18" in doc["verification_engine_gate_ids"]
    assert "G-P04-21" in doc["verification_engine_gate_ids"]
    assert "G-P04-22" in doc["verification_engine_gate_ids"]
    assert "G-P04-23" in doc["verification_engine_gate_ids"]
    assert "G-P04-24" in doc["verification_engine_gate_ids"]
    assert "G-P04-25" in doc["verification_engine_gate_ids"]
    assert "G-P04-26" in doc["verification_engine_gate_ids"]
    assert "G-P04-BF-01" in doc["verification_engine_gate_ids"]
    assert "G-P04-ECO-01" in doc["verification_engine_gate_ids"]
    assert "G-P04-CLOSE-01" in doc["verification_engine_gate_ids"]
    assert doc["org_identity_verification_engine_schema_version"] >= 1
    assert "identity/verification/run" in doc["org_identity_verification_run_route"]
    assert doc["org_failure_remediation_surface_version"] >= 1
    assert "identity/failures" in doc["org_failures_route"]
    assert "identity/remediation/validate" in doc["org_remediation_validate_route"]
    assert doc["identity_control_plane_surface_version"] >= 1
    assert "identity/control-plane" in doc["identity_control_plane_route"]
    assert doc["identity_control_plane_contract"] == "identity_control_plane_v1"
    assert doc["identity_control_plane_doctrine_anchors"]
    assert doc["identity_readiness_economics_surface_version"] >= 1
    assert "identity/readiness-economics" in doc["identity_readiness_economics_route"]
    assert doc["identity_readiness_economics_doctrine_anchors"]
    assert doc["org_identity_certification_pack_surface_version"] >= 1
    assert "identity/certification-pack" in doc["org_identity_certification_pack_route"]
    assert doc["org_identity_certification_pack_doctrine_anchors"]
    assert isinstance(doc.get("identity_operator_console_http_routes"), list)
    assert any("identity/handles" in str(x) for x in doc["identity_operator_console_http_routes"])
    assert "links/timeline" in doc["link_temporal_timeline_route"]
    assert "bundle-equivalence" in doc["bundle_equivalence_list_route"]
    assert "bundle-equivalence" in doc["bundle_equivalence_append_route"]
    assert doc["merge_governance_runtime_surface_version"] >= 1
    assert "cortex/identity/merges" in doc["merge_ledger_list_route"]
    assert "merge-queue" in doc["merge_queue_list_route"]
    assert "cortex/identity/merges" in doc["merge_ledger_append_route"]
    assert doc["merge_governance_runtime_doctrine_anchors"]
    assert "links/hints" in doc["link_hint_bucket_route"]
    assert "link-candidates" in doc["link_candidate_queue_route"]
    assert doc["celery_task_regenerate_link_candidates"] is None
    assert "vector.cortex.identity.regenerate_link_candidates" in doc["legacy_celery_tasks_removed_wave3"]


def test_is_known_object_kind() -> None:
    assert is_known_object_kind("person") is True
    assert is_known_object_kind("not_a_kind") is False


def test_enums_include_expected_discriminants() -> None:
    assert CanonicalLayerKind.ENTITY.value == "entity"
    assert CanonicalStructuralEdgeKind.CONTAINED_IN.value == "contained_in"
