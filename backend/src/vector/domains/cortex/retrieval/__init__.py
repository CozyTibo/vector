"""Phase 07 — deterministic retrieval over replay-safe reconstruction artifacts.

P07-01: ``normative.PHASE07_PROGRAM_FREEZE_VERSION`` (``phase-07-normative-index.md``).
P07-02: ``anti_goals`` — forbidden cognition keys + ``G-P07-ANTI-01`` / ``G-P07-ANTI-02`` gates
(``phase-07-anti-goals-doctrine.md``).
P07-03: ``phase_boundaries`` — RET-BND-06/08/09 + acyclic pipeline law
(``phase-07-phase-boundaries-doctrine.md``).
P07-04: ``retrieval_ingress`` — observed vs derived ingress law + ``RD-INDEX-STALE``
(``phase-07-query-contract-doctrine.md`` §Ingress).
P07-05: ``query_contract`` — workload classes + intents + ``G-P07-QC-01``
(``phase-07-query-contract-doctrine.md`` §1–2).
P07-06: ``query_execution`` — lawful envelope + FSM VALIDATE→RECEIPT + ``G-P07-QC-02/03``
(``phase-07-query-contract-doctrine.md`` §3–4).
P07-07: ``retrieval_legality_matrix`` — query legality classes + R-LEG floors + ``G-P07-LEG-01``
(``retrieval-legality-matrix.md``).
P07-08: ``retrieval_replay_equivalence`` — ``retrieval_query_replay_identity`` + pins + ``G-P07-REPLAY-01``
P07-18: ``retrieval_replay_equivalence_proofs`` — stage-C harness + golden double-run + ``G-P07-REPLAY-02`` bundle
P07-19: ``retrieval_degradation_taxonomy`` — propagation table + **RET-DEG-02** + degradation topology admin
P07-20: ``retrieval_completeness_projection`` — 7th pipeline stage + coverage/overview admin
(``phase-07-replay-equivalence-retrieval-spec.md``).
P07-09: ``retrieval_addressing`` — lookup ids + **RET-ADDR-01** + ``G-P07-ADDR-01`` golden vectors
(``phase-07-retrieval-addressing-model.md``).
P07-10: ``retrieval_provenance_evidence`` — provenance envelope + **RET-PROV-01/02** + ``G-P07-PROV-01``
(``phase-07-retrieval-provenance-evidence-doctrine.md``).
P07-11: ``retrieval_temporal`` — temporal scope + **RET-TEMP-01..04** + ``G-P07-TEMP-01``
(``phase-07-temporal-retrieval-doctrine.md``).
P07-12: ``retrieval_ranking_selection`` — integer tuple sort + **RET-RANK-01/02** + ``G-P07-RANK-01``
(``phase-07-retrieval-ranking-selection-doctrine.md``).
P07-13: ``retrieval_bounded_caps`` — policy pack + omission law + **RET-DEG-01/02** + ``G-P07-DEG-01``
(``phase-07-retrieval-degradation-taxonomy.md``).
P07-14: ``retrieval_index_materialization`` — index epochs + **RET-IDX-01** + ``G-P07-REPLAY-02``
(``phase-07-retrieval-runtime-architecture.md`` §Index).
P07-15: ``retrieval_tcre_binding`` — TCRE/chronology/edge bindings + **RET-TCRE-01/02** + ``G-P07-TCRE-01``
(``phase-07-retrieval-runtime-architecture.md`` §TCRE).
P07-16: ``retrieval_octs_binding`` — OCTS walk + traversal bindings + **RET-OCTS-01..03** + ``G-P07-OCTS-01``
(``phase-07-retrieval-runtime-architecture.md`` §OCTS).
P07-17: ``retrieval_graph_binding`` — graph/identity/canonical bindings + **RET-GRAPH-01..03** + ``G-P07-GRAPH-01``
(``phase-07-retrieval-runtime-architecture.md`` §Graph).
P07-21: ``retrieval_artifact_lineage`` — terminal→root lineage explorer + **RET-LINEAGE-01/02** + ``G-P07-LINEAGE-01``
(``phase-07-retrieval-runtime-architecture.md`` §Lineage).
P07-22: ``retrieval_observability`` — metrics + health model + audit trail + **RET-OBS-01..03** + ``G-P07-OBS-01``
(``phase-07-retrieval-observability-doctrine.md``).
P07-23: ``retrieval_control_plane`` — 16 admin surfaces + RBAC + OpenAPI matrix + **G-P07-CP-01**
(``phase-07-retrieval-admin-control-plane-spec.md``).
P07-24: ``retrieval_operator_workflows`` — W1–W3 workflows + SPA route registry + dangerous rebuild gate + **G-P07-WF-01**
(``phase-07-retrieval-admin-control-plane-spec.md`` §Workflows).
P07-25: ``retrieval_tenant_verification_slice`` + ``retrieval_readiness_economics`` — ``org_graph_retrieval`` slice +
**G-P07-TVER-01** / **G-P07-ECO-01..03** (``phase-07-verification-harness-spec.md`` §Tenant).
P07-26: ``retrieval_runtime_legality_matrix`` — **R‑LEG‑01..07** + **R‑FORB‑01..05** production catalog +
**G-P07-RLM-01** (``phase-07-retrieval-runtime-legality-matrix.md``).
P07-27: ``retrieval_verification_harness`` — **G-P07-*** gate catalog + CI stages **A–Z** +
``run_retrieval_gp07_pr_blocking_static_stages_v1`` (``phase-07-verification-harness-spec.md``).
P07-28: ``retrieval_certification_pack`` — **RETRIEVAL-CERT-PACK-1** + **G-P07-CLOSE-01** +
``GET .../cortex/retrieval/certification-pack`` (``phase-07-closure-gates-doctrine.md``).
P07-29: ``retrieval_implementation_sequencing`` — waves **0–5** catalog + critical path +
Phase 08 readiness handoff (**G-P07-SEQ-01..05**).
P07-30: ``retrieval_program_closure`` — **FF-P07-5** program freeze + 10 completion criteria +
``GET .../program-closure`` (**G-P07-P30-CLOSE**).
"""

from vector.domains.cortex.retrieval.anti_goals import (
    PHASE07_ANTI_GOALS_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1,
    RetrievalAntiGoalViolationError,
    enforce_retrieval_query_envelope_anti_goals_v1,
    verify_gp07_anti01_retrieval_package_static,
    verify_gp07_anti02_retrieval_ingress_token_rejection_static,
)
from vector.domains.cortex.retrieval.retrieval_ingress import (
    PHASE07_INGRESS_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1,
    RETRIEVAL_RD_INDEX_STALE_V1,
    RetrievalIngressError,
    build_retrieval_ingress_law_catalog_v1,
    build_retrieval_provenance_inspector_fields_v1,
    enforce_retrieval_ingress_scope_v1,
    verify_gp07_ingress01_observed_derived_partition_static,
)
from vector.domains.cortex.retrieval.phase_boundaries import (
    PHASE07_BOUNDARIES_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_RD_TCRE_GAP_V1,
    RET_BND_RULE_IDS_V1,
    RetrievalPhaseBoundaryError,
    build_retrieval_phase_boundary_catalog_v1,
    enforce_retrieval_envelope_phase06_boundary_v1,
    verify_gp07_bnd06_tcre_boundary_static,
    verify_gp07_bnd08_synthesis_boundary_static,
    verify_gp07_bnd_acyclic_dependency_static,
)
from vector.domains.cortex.retrieval.query_contract import (
    GP07_QC01_GATE_ID_V1,
    PHASE07_QUERY_CONTRACT_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_INTENT_CLASSES_V1,
    RETRIEVAL_RD_ADDRESSING_UNRESOLVED_V1,
    RETRIEVAL_WORKLOAD_CLASSES_V1,
    RetrievalQueryContractError,
    build_retrieval_query_contract_catalog_v1,
    verify_gp07_qc01_workload_intent_registry_static,
)
from vector.domains.cortex.retrieval.query_execution import (
    PHASE07_QUERY_EXECUTION_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_QUERY_EXECUTION_PHASES_V1,
    RetrievalQueryExecutionError,
    execute_retrieval_query_envelope_v1,
    verify_gp07_qc02_addressing_resolution_static,
    verify_gp07_qc03_fsm_phase_order_static,
)
from vector.domains.cortex.retrieval.normative import (
    PHASE07_PROGRAM_FREEZE_VERSION,
    build_phase07_normative_program_document_v1,
)
from vector.domains.cortex.retrieval.retrieval_legality_matrix import (
    GP07_LEG01_GATE_ID_V1,
    PHASE07_RETRIEVAL_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_LEGALITY_MATRIX_CONTRACT_V1,
    aggregate_query_legality_class_v1,
    build_retrieval_legality_matrix_catalog_v1,
    build_retrieval_queries_by_legality_histogram_v1,
    run_retrieval_r_leg_precheck_v1,
    verify_gp07_leg01_retrieval_legality_matrix_static,
)
from vector.domains.cortex.retrieval.retrieval_runtime_legality_matrix import (
    GP07_RLM01_GATE_ID_V1,
    PHASE07_RETRIEVAL_RUNTIME_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1,
    build_retrieval_runtime_legality_matrix_catalog_v1,
    detect_retrieval_forbidden_deployments_v1,
    evaluate_retrieval_production_gates_v1,
    verify_gp07_rlm01_retrieval_runtime_legality_matrix_static_bundle,
)
from vector.domains.cortex.retrieval.retrieval_legality_projection import (
    RETRIEVAL_LEGALITY_CLASSES_V1,
    assert_retrieval_query_lawful_v1,
    classify_retrieval_legality_v1,
)
from vector.domains.cortex.retrieval.retrieval_addressing import (
    GP07_ADDR01_GATE_ID_V1,
    PHASE07_RETRIEVAL_ADDRESSING_RUNTIME_SCHEMA_VERSION,
    build_retrieval_addressing_catalog_v1,
    resolve_retrieval_addressing_v1,
    verify_gp07_addr01_golden_corpus_static,
)
from vector.domains.cortex.retrieval.retrieval_provenance_evidence import (
    GP07_PROV01_GATE_ID_V1,
    PHASE07_RETRIEVAL_PROVENANCE_EVIDENCE_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_EVIDENCE_LEGALITY_CLASSES_V1,
    build_retrieval_provenance_inspector_catalog_v1,
    verify_gp07_prov01_provenance_field_checklist_static,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    GP07_REPLAY02_GATE_ID_V1,
    PHASE07_RETRIEVAL_INDEX_MATERIALIZATION_RUNTIME_SCHEMA_VERSION,
    build_retrieval_index_catalog_v1,
    materialize_retrieval_index_entry_v1,
    verify_gp07_idx01_publish_barrier_static,
    verify_gp07_replay02_index_permutation_invariance_static,
)
from vector.domains.cortex.retrieval.retrieval_tcre_binding import (
    GP07_TCRE01_GATE_ID_V1,
    PHASE07_RETRIEVAL_TCRE_BINDING_RUNTIME_SCHEMA_VERSION,
    apply_retrieval_tcre_binding_to_query_v1,
    build_retrieval_tcre_binding_catalog_v1,
    build_tcre_handoff_lookup_map_v1,
    map_runtime02_ref_to_retrieval_lookup_id_v1,
    materialize_retrieval_index_from_tcre_job_v1,
    verify_gp07_tcre01_runtime02_lookup_map_static,
)
from vector.domains.cortex.retrieval.retrieval_octs_binding import (
    GP07_OCTS01_GATE_ID_V1,
    PHASE07_RETRIEVAL_OCTS_BINDING_RUNTIME_SCHEMA_VERSION,
    apply_retrieval_octs_binding_to_query_v1,
    build_retrieval_traversal_binding_catalog_v1,
    build_retrieval_walk_ref_v1,
    materialize_retrieval_index_from_walk_v1,
    query_walk_scope_v1,
    verify_gp07_octs01_walk_ref_and_scope_queries_static,
)
from vector.domains.cortex.retrieval.retrieval_graph_binding import (
    GP07_GRAPH01_GATE_ID_V1,
    PHASE07_RETRIEVAL_GRAPH_BINDING_RUNTIME_SCHEMA_VERSION,
    apply_retrieval_graph_binding_to_query_v1,
    build_retrieval_graph_binding_catalog_v1,
    map_graph_ref_to_retrieval_lookup_id_v1,
    materialize_retrieval_index_from_graph_ref_v1,
    query_graph_scope_v1,
    verify_gp07_graph01_entity_link_addressing_static,
)
from vector.domains.cortex.retrieval.retrieval_artifact_lineage import (
    GP07_LINEAGE01_GATE_ID_V1,
    PHASE07_RETRIEVAL_ARTIFACT_LINEAGE_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_RD_LINEAGE_GAP_V1,
    apply_retrieval_lineage_binding_to_query_v1,
    build_retrieval_lineage_explorer_catalog_v1,
    build_retrieval_lineage_explorer_chain_v1,
    load_retrieval_lineage_golden_case_v1,
    run_retrieval_golden_lineage_explorer_case_v1,
    verify_gp07_lineage01_golden_corpus_static,
    verify_gp07_lineage01_terminal_to_root_cap_static,
)
from vector.domains.cortex.retrieval.retrieval_observability import (
    GP07_OBS01_GATE_ID_V1,
    PHASE07_RETRIEVAL_OBSERVABILITY_RUNTIME_SCHEMA_VERSION,
    build_retrieval_health_strip_v1,
    build_retrieval_observability_catalog_v1,
    build_retrieval_runtime_health_v1,
    record_retrieval_query_observability_v1,
    snapshot_retrieval_metrics_v1,
    verify_gp07_obs01_metrics_and_health_static,
)
from vector.domains.cortex.retrieval.retrieval_control_plane import (
    GP07_CP01_GATE_ID_V1,
    PHASE07_RETRIEVAL_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_ADMIN_OPENAPI_PATHS_V1,
    RETRIEVAL_CONTROL_PLANE_SURFACES_V1,
    build_retrieval_control_plane_surface_checklist_v1,
    build_retrieval_control_plane_v1,
    build_retrieval_rbac_matrix_v1,
    list_retrieval_query_audit_trail_v1,
    retrieval_admin_openapi_path_v1,
    verify_gp07_cp01_retrieval_control_plane_rbac_static,
)
from vector.domains.cortex.retrieval.retrieval_operator_workflows import (
    GP07_WF01_GATE_ID_V1,
    PHASE07_RETRIEVAL_OPERATOR_WORKFLOWS_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE_V1,
    RETRIEVAL_SURFACE_SPA_ROUTES_V1,
    RetrievalOperatorWorkflowsError,
    assert_retrieval_index_rebuild_confirmation_v1,
    build_retrieval_operator_workflows_catalog_v1,
    build_retrieval_spa_route_registry_v1,
    list_remediation_links_for_omissions_v1,
    verify_gp07_wf01_spa_routes_complete_static,
)
from vector.domains.cortex.retrieval.retrieval_readiness_economics import (
    GP07_ECO01_GATE_ID_V1,
    GP07_ECO02_GATE_ID_V1,
    GP07_ECO03_GATE_ID_V1,
    RETRIEVAL_READINESS_ECONOMICS_CONTRACT_V1,
    RETRIEVAL_READINESS_ECONOMICS_SCHEMA_VERSION,
    build_retrieval_readiness_economics_receipt_v1,
    compute_retrieval_economics_receipt_hash_v1,
    verify_gp07_eco01_readiness_economics_clean_profile_static,
    verify_gp07_eco02_readiness_economics_hostile_profile_static,
    verify_gp07_eco03_admin_openapi_path_matrix_static,
)
from vector.domains.cortex.retrieval.retrieval_tenant_verification_slice import (
    GP07_TVER01_GATE_ID_V1,
    ORG_GRAPH_RETRIEVAL_VERIFICATION_SLICE_SCHEMA_VERSION,
    VECTOR_RETRIEVAL_TENANT_VERIFICATION_SLICE_ENV,
    build_org_graph_retrieval_verification_slice_v1,
    compute_retrieval_verification_slice_hash_v1,
    retrieval_tenant_verification_slice_enabled_v1,
    validate_org_graph_retrieval_verification_slice_v1,
    verify_gp07_tver01_org_graph_retrieval_slice_golden_static,
    verify_gp07_tver02_admin_openapi_path_matrix_static,
)
from vector.domains.cortex.retrieval.retrieval_bounded_caps import (
    GP07_DEG01_GATE_ID_V1,
    PHASE07_RETRIEVAL_BOUNDED_CAPS_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_POLICY_PACK_ID_DEFAULT_V1,
    build_retrieval_omission_explorer_catalog_v1,
    load_retrieval_policy_pack_v1,
    verify_gp07_deg01_rd_registry_closed_static,
)
from vector.domains.cortex.retrieval.retrieval_ranking_selection import (
    GP07_RANK01_GATE_ID_V1,
    PHASE07_RETRIEVAL_RANKING_SELECTION_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1,
    build_retrieval_ranking_selection_catalog_v1,
    verify_gp07_rank01_no_float_scores_static,
)
from vector.domains.cortex.retrieval.retrieval_temporal import (
    GP07_TEMP01_GATE_ID_V1,
    PHASE07_RETRIEVAL_TEMPORAL_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_TEMPORAL_SCOPE_FIELD_IDS_V1,
    build_retrieval_temporal_explorer_catalog_v1,
    normalize_retrieval_temporal_scope_v1,
    verify_gp07_temp01_temporal_scope_schema_static,
)
from vector.domains.cortex.retrieval.retrieval_replay_equivalence import (
    GP07_REPLAY_01_GATE_ID_V1,
    PHASE07_RETRIEVAL_REPLAY_EQUIVALENCE_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_RD_POLICY_MISMATCH_V1,
    RetrievalReplayEquivalenceError,
    compute_retrieval_query_replay_identity_v1,
    verify_gp07_replay_01_canonical_identity_stable_static,
)
from vector.domains.cortex.retrieval.retrieval_replay_equivalence_proofs import (
    PHASE07_RETRIEVAL_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_RD_REPLAY_TWIN_V1,
    build_retrieval_replay_inspector_catalog_v1,
)
from vector.domains.cortex.retrieval.retrieval_program_closure import (
    GP07_P30_PROGRAM_CLOSURE_GATE_ID_V1,
    PHASE07_FREEZE_BUNDLE_FF_P07_5_V1,
    PHASE07_RETRIEVAL_PROGRAM_CLOSURE_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_PROGRAM_CLOSURE_SPEC_REF_V1,
    build_retrieval_program_closure_snapshot_v1,
    build_retrieval_program_completion_matrix_v1,
    run_retrieval_gp07_ci_cert_pack_artifact_v1,
    verify_gp07_p30_retrieval_program_closure_static,
)
from vector.domains.cortex.retrieval.retrieval_implementation_sequencing import (
    GP07_SEQ01_GATE_ID_V1,
    GP07_SEQ05_GATE_ID_V1,
    PHASE07_RETRIEVAL_IMPLEMENTATION_SEQUENCING_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_CRITICAL_PATH_MODULE_CHAIN_V1,
    RETRIEVAL_EVIDENCE_HIT_SCHEMA_LITERAL_V1,
    RETRIEVAL_IMPLEMENTATION_SEQUENCING_SPEC_REF_V1,
    RETRIEVAL_IMPLEMENTATION_WAVE_IDS_V1,
    build_retrieval_implementation_sequencing_catalog_v1,
    build_retrieval_phase08_readiness_checklist_v1,
    build_retrieval_tracker_step_wave_map_v1,
    evaluate_all_retrieval_implementation_waves_v1,
    evaluate_retrieval_implementation_wave_v1,
    verify_gp07_seq01_implementation_sequencing_catalog_static,
    verify_gp07_seq02_tracker_wave_mapping_static,
    verify_gp07_seq03_critical_path_modules_static,
    verify_gp07_seq04_waves_zero_through_five_complete_static,
    verify_gp07_seq05_phase08_readiness_handoff_static,
)
from vector.domains.cortex.retrieval.retrieval_certification_pack import (
    PHASE07_RETRIEVAL_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1,
    RETRIEVAL_CERT_PACK_REQUIRED_ROOT_FILES_V1,
    RETRIEVAL_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1,
    build_retrieval_cert_pack_v1,
    build_retrieval_certification_pack_snapshot_v1,
    compute_retrieval_vectors_bundle_hash_v1,
    default_retrieval_cert_pack_vector_files_v1,
    verify_gp07_close01_retrieval_cert_pack_closure_static,
    verify_gp07_rcpk01_retrieval_cert_pack_admin_openapi_path_matrix_static,
    verify_retrieval_cert_pack_v1,
)
from vector.domains.cortex.retrieval.retrieval_verification_harness import (
    PHASE07_RETRIEVAL_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION,
    RETRIEVAL_GP07_DOCTRINE_GATE_IDS_V1,
    RETRIEVAL_VERIFICATION_HARNESS_SPEC_REF_V1,
    build_retrieval_verification_harness_catalog_v1,
    list_retrieval_gp07_wired_verification_runners_v1,
    run_retrieval_gp07_ci_full_wired_stages_with_meta_v1,
    run_retrieval_gp07_pr_blocking_static_stages_v1,
    run_retrieval_gp07_stage_c_replay_gates_v1,
    run_retrieval_gp07_wired_verification_stages_v1,
    verify_gp07_rvh01_harness_catalog_covers_spec_gate_table_static,
    verify_gp07_rvh02_pr_blocking_bundle_passes_static,
    verify_gp07_rvh03_full_stage_az_includes_close_static,
)
from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
    GP07_COMP01_GATE_ID_V1,
    PHASE07_RETRIEVAL_COMPLETENESS_RUNTIME_SCHEMA_VERSION,
    build_retrieval_coverage_catalog_v1,
    build_retrieval_overview_catalog_v1,
    project_retrieval_completeness_v1,
    verify_gp07_comp01_never_idle_healthy_static,
)
from vector.domains.cortex.retrieval.retrieval_degradation_taxonomy import (
    GP07_DEG02_GATE_ID_V1,
    GP07_DEG03_GATE_ID_V1,
    PHASE07_RETRIEVAL_DEGRADATION_TAXONOMY_RUNTIME_SCHEMA_VERSION,
    apply_retrieval_degradation_taxonomy_to_query_result_v1,
    build_retrieval_degradation_topology_catalog_v1,
    build_retrieval_rd_rollup_v1,
    propagate_upstream_triggers_to_rd_omissions_v1,
    verify_gp07_deg02_monotonicity_static,
    verify_gp07_deg03_propagation_table_static,
    verify_gp07_deg04_completeness_registry_static,
)
from vector.domains.cortex.retrieval.retrieval_query_engine import (
    execute_retrieval_query_v1,
    index_tcre_chain_for_retrieval_v1,
    index_walk_for_retrieval_v1,
    index_graph_ref_for_retrieval_v1,
)

__all__ = [
    "PHASE07_ANTI_GOALS_RUNTIME_SCHEMA_VERSION",
    "PHASE07_BOUNDARIES_RUNTIME_SCHEMA_VERSION",
    "PHASE07_INGRESS_RUNTIME_SCHEMA_VERSION",
    "PHASE07_QUERY_CONTRACT_RUNTIME_SCHEMA_VERSION",
    "PHASE07_QUERY_EXECUTION_RUNTIME_SCHEMA_VERSION",
    "RETRIEVAL_QUERY_EXECUTION_PHASES_V1",
    "RetrievalQueryExecutionError",
    "execute_retrieval_query_envelope_v1",
    "verify_gp07_qc02_addressing_resolution_static",
    "verify_gp07_qc03_fsm_phase_order_static",
    "PHASE07_PROGRAM_FREEZE_VERSION",
    "GP07_QC01_GATE_ID_V1",
    "RETRIEVAL_INTENT_CLASSES_V1",
    "RETRIEVAL_RD_ADDRESSING_UNRESOLVED_V1",
    "RETRIEVAL_WORKLOAD_CLASSES_V1",
    "RetrievalQueryContractError",
    "build_retrieval_query_contract_catalog_v1",
    "verify_gp07_qc01_workload_intent_registry_static",
    "RETRIEVAL_EVIDENCE_LEGALITY_CANDIDATE_ONLY_V1",
    "RETRIEVAL_RD_INDEX_STALE_V1",
    "RetrievalIngressError",
    "build_retrieval_ingress_law_catalog_v1",
    "build_retrieval_provenance_inspector_fields_v1",
    "enforce_retrieval_ingress_scope_v1",
    "verify_gp07_ingress01_observed_derived_partition_static",
    "RET_BND_RULE_IDS_V1",
    "RETRIEVAL_RD_TCRE_GAP_V1",
    "RetrievalPhaseBoundaryError",
    "build_retrieval_phase_boundary_catalog_v1",
    "enforce_retrieval_envelope_phase06_boundary_v1",
    "verify_gp07_bnd06_tcre_boundary_static",
    "verify_gp07_bnd08_synthesis_boundary_static",
    "verify_gp07_bnd_acyclic_dependency_static",
    "RETRIEVAL_FORBIDDEN_LEGALITY_CLASS_V1",
    "RetrievalAntiGoalViolationError",
    "build_phase07_normative_program_document_v1",
    "enforce_retrieval_query_envelope_anti_goals_v1",
    "verify_gp07_anti01_retrieval_package_static",
    "verify_gp07_anti02_retrieval_ingress_token_rejection_static",
    "RETRIEVAL_LEGALITY_CLASSES_V1",
    "GP07_LEG01_GATE_ID_V1",
    "PHASE07_RETRIEVAL_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION",
    "RETRIEVAL_LEGALITY_MATRIX_CONTRACT_V1",
    "aggregate_query_legality_class_v1",
    "build_retrieval_legality_matrix_catalog_v1",
    "build_retrieval_queries_by_legality_histogram_v1",
    "run_retrieval_r_leg_precheck_v1",
    "verify_gp07_leg01_retrieval_legality_matrix_static",
    "GP07_RLM01_GATE_ID_V1",
    "PHASE07_RETRIEVAL_RUNTIME_LEGALITY_MATRIX_RUNTIME_SCHEMA_VERSION",
    "RETRIEVAL_RUNTIME_LEGALITY_MATRIX_CONTRACT_V1",
    "build_retrieval_runtime_legality_matrix_catalog_v1",
    "detect_retrieval_forbidden_deployments_v1",
    "evaluate_retrieval_production_gates_v1",
    "verify_gp07_rlm01_retrieval_runtime_legality_matrix_static_bundle",
    "GP07_ADDR01_GATE_ID_V1",
    "PHASE07_RETRIEVAL_ADDRESSING_RUNTIME_SCHEMA_VERSION",
    "build_retrieval_addressing_catalog_v1",
    "resolve_retrieval_addressing_v1",
    "verify_gp07_addr01_golden_corpus_static",
    "GP07_PROV01_GATE_ID_V1",
    "PHASE07_RETRIEVAL_PROVENANCE_EVIDENCE_RUNTIME_SCHEMA_VERSION",
    "RETRIEVAL_EVIDENCE_LEGALITY_CLASSES_V1",
    "build_retrieval_provenance_inspector_catalog_v1",
    "verify_gp07_prov01_provenance_field_checklist_static",
    "GP07_TEMP01_GATE_ID_V1",
    "PHASE07_RETRIEVAL_TEMPORAL_RUNTIME_SCHEMA_VERSION",
    "RETRIEVAL_TEMPORAL_SCOPE_FIELD_IDS_V1",
    "build_retrieval_temporal_explorer_catalog_v1",
    "normalize_retrieval_temporal_scope_v1",
    "verify_gp07_temp01_temporal_scope_schema_static",
    "GP07_RANK01_GATE_ID_V1",
    "PHASE07_RETRIEVAL_RANKING_SELECTION_RUNTIME_SCHEMA_VERSION",
    "RETRIEVAL_SELECTION_POLICY_PROFILE_DEFAULT_V1",
    "build_retrieval_ranking_selection_catalog_v1",
    "verify_gp07_rank01_no_float_scores_static",
    "GP07_DEG01_GATE_ID_V1",
    "PHASE07_RETRIEVAL_BOUNDED_CAPS_RUNTIME_SCHEMA_VERSION",
    "RETRIEVAL_POLICY_PACK_ID_DEFAULT_V1",
    "build_retrieval_omission_explorer_catalog_v1",
    "load_retrieval_policy_pack_v1",
    "verify_gp07_deg01_rd_registry_closed_static",
    "GP07_REPLAY02_GATE_ID_V1",
    "PHASE07_RETRIEVAL_INDEX_MATERIALIZATION_RUNTIME_SCHEMA_VERSION",
    "build_retrieval_index_catalog_v1",
    "materialize_retrieval_index_entry_v1",
    "verify_gp07_idx01_publish_barrier_static",
    "verify_gp07_replay02_index_permutation_invariance_static",
    "GP07_TCRE01_GATE_ID_V1",
    "PHASE07_RETRIEVAL_TCRE_BINDING_RUNTIME_SCHEMA_VERSION",
    "apply_retrieval_tcre_binding_to_query_v1",
    "build_retrieval_tcre_binding_catalog_v1",
    "build_tcre_handoff_lookup_map_v1",
    "map_runtime02_ref_to_retrieval_lookup_id_v1",
    "materialize_retrieval_index_from_tcre_job_v1",
    "verify_gp07_tcre01_runtime02_lookup_map_static",
    "GP07_OCTS01_GATE_ID_V1",
    "PHASE07_RETRIEVAL_OCTS_BINDING_RUNTIME_SCHEMA_VERSION",
    "apply_retrieval_octs_binding_to_query_v1",
    "build_retrieval_traversal_binding_catalog_v1",
    "build_retrieval_walk_ref_v1",
    "materialize_retrieval_index_from_walk_v1",
    "query_walk_scope_v1",
    "verify_gp07_octs01_walk_ref_and_scope_queries_static",
    "GP07_GRAPH01_GATE_ID_V1",
    "PHASE07_RETRIEVAL_GRAPH_BINDING_RUNTIME_SCHEMA_VERSION",
    "apply_retrieval_graph_binding_to_query_v1",
    "build_retrieval_graph_binding_catalog_v1",
    "map_graph_ref_to_retrieval_lookup_id_v1",
    "materialize_retrieval_index_from_graph_ref_v1",
    "query_graph_scope_v1",
    "verify_gp07_graph01_entity_link_addressing_static",
    "GP07_LINEAGE01_GATE_ID_V1",
    "PHASE07_RETRIEVAL_ARTIFACT_LINEAGE_RUNTIME_SCHEMA_VERSION",
    "RETRIEVAL_RD_LINEAGE_GAP_V1",
    "apply_retrieval_lineage_binding_to_query_v1",
    "build_retrieval_lineage_explorer_catalog_v1",
    "build_retrieval_lineage_explorer_chain_v1",
    "load_retrieval_lineage_golden_case_v1",
    "run_retrieval_golden_lineage_explorer_case_v1",
    "verify_gp07_lineage01_golden_corpus_static",
    "verify_gp07_lineage01_terminal_to_root_cap_static",
    "GP07_OBS01_GATE_ID_V1",
    "PHASE07_RETRIEVAL_OBSERVABILITY_RUNTIME_SCHEMA_VERSION",
    "build_retrieval_health_strip_v1",
    "build_retrieval_observability_catalog_v1",
    "build_retrieval_runtime_health_v1",
    "record_retrieval_query_observability_v1",
    "snapshot_retrieval_metrics_v1",
    "verify_gp07_obs01_metrics_and_health_static",
    "GP07_CP01_GATE_ID_V1",
    "PHASE07_RETRIEVAL_CONTROL_PLANE_RUNTIME_SCHEMA_VERSION",
    "RETRIEVAL_ADMIN_OPENAPI_PATHS_V1",
    "RETRIEVAL_CONTROL_PLANE_SURFACES_V1",
    "build_retrieval_control_plane_surface_checklist_v1",
    "build_retrieval_control_plane_v1",
    "build_retrieval_rbac_matrix_v1",
    "list_retrieval_query_audit_trail_v1",
    "retrieval_admin_openapi_path_v1",
    "verify_gp07_cp01_retrieval_control_plane_rbac_static",
    "GP07_WF01_GATE_ID_V1",
    "PHASE07_RETRIEVAL_OPERATOR_WORKFLOWS_RUNTIME_SCHEMA_VERSION",
    "RETRIEVAL_INDEX_REBUILD_CONFIRM_PHRASE_V1",
    "RETRIEVAL_SURFACE_SPA_ROUTES_V1",
    "RetrievalOperatorWorkflowsError",
    "assert_retrieval_index_rebuild_confirmation_v1",
    "build_retrieval_operator_workflows_catalog_v1",
    "build_retrieval_spa_route_registry_v1",
    "list_remediation_links_for_omissions_v1",
    "verify_gp07_wf01_spa_routes_complete_static",
    "GP07_ECO01_GATE_ID_V1",
    "GP07_ECO02_GATE_ID_V1",
    "GP07_ECO03_GATE_ID_V1",
    "RETRIEVAL_READINESS_ECONOMICS_CONTRACT_V1",
    "RETRIEVAL_READINESS_ECONOMICS_SCHEMA_VERSION",
    "build_retrieval_readiness_economics_receipt_v1",
    "compute_retrieval_economics_receipt_hash_v1",
    "verify_gp07_eco01_readiness_economics_clean_profile_static",
    "verify_gp07_eco02_readiness_economics_hostile_profile_static",
    "verify_gp07_eco03_admin_openapi_path_matrix_static",
    "GP07_TVER01_GATE_ID_V1",
    "ORG_GRAPH_RETRIEVAL_VERIFICATION_SLICE_SCHEMA_VERSION",
    "VECTOR_RETRIEVAL_TENANT_VERIFICATION_SLICE_ENV",
    "build_org_graph_retrieval_verification_slice_v1",
    "compute_retrieval_verification_slice_hash_v1",
    "retrieval_tenant_verification_slice_enabled_v1",
    "validate_org_graph_retrieval_verification_slice_v1",
    "verify_gp07_tver01_org_graph_retrieval_slice_golden_static",
    "verify_gp07_tver02_admin_openapi_path_matrix_static",
    "GP07_REPLAY_01_GATE_ID_V1",
    "PHASE07_RETRIEVAL_REPLAY_EQUIVALENCE_RUNTIME_SCHEMA_VERSION",
    "RETRIEVAL_RD_POLICY_MISMATCH_V1",
    "RetrievalReplayEquivalenceError",
    "PHASE07_RETRIEVAL_REPLAY_EQUIVALENCE_PROOFS_RUNTIME_SCHEMA_VERSION",
    "RETRIEVAL_RD_REPLAY_TWIN_V1",
    "build_retrieval_replay_inspector_catalog_v1",
    "compute_retrieval_query_replay_identity_v1",
    "PHASE07_RETRIEVAL_PROGRAM_CLOSURE_RUNTIME_SCHEMA_VERSION",
    "PHASE07_FREEZE_BUNDLE_FF_P07_5_V1",
    "GP07_P30_PROGRAM_CLOSURE_GATE_ID_V1",
    "RETRIEVAL_PROGRAM_CLOSURE_SPEC_REF_V1",
    "build_retrieval_program_closure_snapshot_v1",
    "build_retrieval_program_completion_matrix_v1",
    "run_retrieval_gp07_ci_cert_pack_artifact_v1",
    "verify_gp07_p30_retrieval_program_closure_static",
    "PHASE07_RETRIEVAL_IMPLEMENTATION_SEQUENCING_RUNTIME_SCHEMA_VERSION",
    "RETRIEVAL_CRITICAL_PATH_MODULE_CHAIN_V1",
    "RETRIEVAL_EVIDENCE_HIT_SCHEMA_LITERAL_V1",
    "RETRIEVAL_IMPLEMENTATION_SEQUENCING_SPEC_REF_V1",
    "RETRIEVAL_IMPLEMENTATION_WAVE_IDS_V1",
    "GP07_SEQ01_GATE_ID_V1",
    "GP07_SEQ05_GATE_ID_V1",
    "build_retrieval_implementation_sequencing_catalog_v1",
    "build_retrieval_phase08_readiness_checklist_v1",
    "build_retrieval_tracker_step_wave_map_v1",
    "evaluate_all_retrieval_implementation_waves_v1",
    "evaluate_retrieval_implementation_wave_v1",
    "verify_gp07_seq01_implementation_sequencing_catalog_static",
    "verify_gp07_seq02_tracker_wave_mapping_static",
    "verify_gp07_seq03_critical_path_modules_static",
    "verify_gp07_seq04_waves_zero_through_five_complete_static",
    "verify_gp07_seq05_phase08_readiness_handoff_static",
    "PHASE07_RETRIEVAL_CERTIFICATION_PACK_RUNTIME_SCHEMA_VERSION",
    "RETRIEVAL_CERT_PACK_REQUIRED_ROOT_FILES_V1",
    "RETRIEVAL_CERTIFICATION_PACK_ADMIN_OPENAPI_PATHS_V1",
    "build_retrieval_cert_pack_v1",
    "build_retrieval_certification_pack_snapshot_v1",
    "compute_retrieval_vectors_bundle_hash_v1",
    "default_retrieval_cert_pack_vector_files_v1",
    "verify_gp07_rcpk01_retrieval_cert_pack_admin_openapi_path_matrix_static",
    "verify_retrieval_cert_pack_v1",
    "PHASE07_RETRIEVAL_VERIFICATION_HARNESS_RUNTIME_SCHEMA_VERSION",
    "RETRIEVAL_CERT_PACK_FORMAT_LITERAL_V1",
    "RETRIEVAL_GP07_DOCTRINE_GATE_IDS_V1",
    "RETRIEVAL_VERIFICATION_HARNESS_SPEC_REF_V1",
    "build_retrieval_verification_harness_catalog_v1",
    "list_retrieval_gp07_wired_verification_runners_v1",
    "run_retrieval_gp07_ci_full_wired_stages_with_meta_v1",
    "run_retrieval_gp07_pr_blocking_static_stages_v1",
    "run_retrieval_gp07_stage_c_replay_gates_v1",
    "run_retrieval_gp07_wired_verification_stages_v1",
    "verify_gp07_close01_retrieval_cert_pack_closure_static",
    "verify_gp07_rvh01_harness_catalog_covers_spec_gate_table_static",
    "verify_gp07_rvh02_pr_blocking_bundle_passes_static",
    "verify_gp07_rvh03_full_stage_az_includes_close_static",
    "PHASE07_RETRIEVAL_DEGRADATION_TAXONOMY_RUNTIME_SCHEMA_VERSION",
    "GP07_DEG02_GATE_ID_V1",
    "GP07_DEG03_GATE_ID_V1",
    "apply_retrieval_degradation_taxonomy_to_query_result_v1",
    "build_retrieval_degradation_topology_catalog_v1",
    "build_retrieval_rd_rollup_v1",
    "propagate_upstream_triggers_to_rd_omissions_v1",
    "verify_gp07_deg02_monotonicity_static",
    "verify_gp07_deg03_propagation_table_static",
    "verify_gp07_deg04_completeness_registry_static",
    "GP07_COMP01_GATE_ID_V1",
    "PHASE07_RETRIEVAL_COMPLETENESS_RUNTIME_SCHEMA_VERSION",
    "build_retrieval_coverage_catalog_v1",
    "build_retrieval_overview_catalog_v1",
    "project_retrieval_completeness_v1",
    "verify_gp07_comp01_never_idle_healthy_static",
    "verify_gp07_replay_01_canonical_identity_stable_static",
    "assert_retrieval_query_lawful_v1",
    "classify_retrieval_legality_v1",
    "execute_retrieval_query_v1",
    "index_tcre_chain_for_retrieval_v1",
    "index_walk_for_retrieval_v1",
    "index_graph_ref_for_retrieval_v1",
]
