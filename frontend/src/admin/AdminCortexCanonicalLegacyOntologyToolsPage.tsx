import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

type OntologyArc = { from_kind: string; edge_kind: string; to_kind: string };
type OntologyKind = {
  id: string;
  layer: string;
  taxonomy_family: string;
  structural_role: string;
  structural_examples: string[];
  description: string;
};
type TaxonomyFamily = { id: string; boundary_definition: string };
type KindTaxonomyRow = {
  object_kind_id: string;
  taxonomy_family: string;
  structural_role: string;
  structural_examples: string[];
};

type LogicalKeyKindRow = {
  canonical_object_kind: string;
  idempotency_tuple_fields: string[];
  tie_break_notes?: string | null;
};

type EvidenceGradeRow = { id: string; label: string; definition: string };
type MappingAllowedOp = { id: string; description: string };
type MappingTableCol = {
  column: string;
  value_type: string;
  required: boolean;
  description: string;
};

type CanonicalOntologyPayload = {
  ontology_schema_version: number;
  phase: string;
  implementation_step: number;
  completed_implementation_steps: number[];
  name: string;
  tenant_id?: string | null;
  layers: string[];
  object_kinds: OntologyKind[];
  structural_arcs: OntologyArc[];
  taxonomy_families: TaxonomyFamily[];
  kind_taxonomy: KindTaxonomyRow[];
  taxonomy_hard_rules: string[];
  logical_key_profile_version: number;
  logical_key_global_rules: string[];
  logical_keys_by_kind: LogicalKeyKindRow[];
  logical_key_doctrine_anchors: string[];
  mapping_contract_schema_version: number;
  evidence_grades: EvidenceGradeRow[];
  determinism_criteria: string[];
  structural_extraction_definition: string;
  semantic_inference_forbidden_definition: string;
  allowed_deterministic_operations: MappingAllowedOp[];
  forbidden_operations: string[];
  field_emission_posture_rules: string[];
  mapping_versioning_rules: string[];
  mapping_table_row_shape: MappingTableCol[];
  mapping_contract_doctrine_anchors: string[];
  mapping_registry_surface_version: number;
  mapping_registry_admin_route: string;
  mapping_registry_doctrine_anchors: string[];
  doctrine_anchors: string[];
  transform_runtime_surface_version: number;
  transform_materialize_route: string;
  transform_lineage_route: string;
  transform_lineage_includes_confidence: boolean;
  transform_supports_replay_job_link: boolean;
  transform_emits_provenance_record: boolean;
  transform_persists_temporal_ordering: boolean;
  transform_runtime_doctrine_anchors: string[];
  confidence_propagation_surface_version: number;
  confidence_propagation_schema_version: number;
  confidence_non_ranking_semantics: string;
  confidence_allowed_classes: Array<Record<string, unknown>>;
  confidence_forbidden_classes: Array<Record<string, unknown>>;
  confidence_summary_admin_route: string;
  confidence_propagation_doctrine_anchors: string[];
  ambiguity_runtime_surface_version: number;
  ambiguity_list_route: string;
  ambiguity_open_route: string;
  ambiguity_detail_route: string;
  ambiguity_lifecycle_route: string;
  ambiguity_runtime_doctrine_anchors: string[];
  identity_runtime_surface_version: number;
  identity_anchors_list_route: string;
  identity_anchor_detail_route: string;
  identity_runtime_doctrine_anchors: string[];
  replay_runtime_surface_version: number;
  replay_jobs_list_route: string;
  replay_job_detail_route: string;
  replay_job_run_route: string;
  replay_divergence_taxonomy: Array<{ class: string; meaning: string }>;
  replay_runtime_doctrine_anchors: string[];
  provenance_runtime_surface_version: number;
  provenance_by_raw_record_route: string;
  provenance_by_materialization_route: string;
  provenance_evidence_shapes_documented: string[];
  provenance_runtime_doctrine_anchors: string[];
  temporal_runtime_surface_version: number;
  temporal_supersessions_list_route: string;
  temporal_rebuild_preview_route: string;
  temporal_ordering_precedence: string[];
  temporal_runtime_doctrine_anchors: string[];
  canonical_query_surface_version: number;
  canonical_query_route: string;
  canonical_query_classes: string[];
  canonical_query_doctrine_anchors: string[];
  failure_remediation_surface_version: number;
  canonical_failures_route: string;
  canonical_remediation_validate_route: string;
  failure_degradation_taxonomy: string[];
  failure_classes_documented: string[];
  remediation_classes_documented: string[];
  failure_remediation_doctrine_anchors: string[];
  verification_engine_surface_version: number;
  canonical_verification_run_route: string;
  canonical_verification_runs_list_route: string;
  verification_engine_gate_ids: string[];
  verification_engine_doctrine_anchors: string[];
  canonical_control_plane_surface_version: number;
  canonical_control_plane_route: string;
  canonical_control_plane_doctrine_anchors: string[];
  stabilization_proof_surface_version: number;
  canonical_stabilization_proof_route: string;
  canonical_stabilization_proof_run_route: string;
  canonical_stabilization_proof_runs_route: string;
  stabilization_proof_doctrine_anchors: string[];
  certification_pack_surface_version: number;
  canonical_certification_pack_route: string;
  canonical_certification_pack_archive_route: string;
  canonical_certification_pack_archives_route: string;
  certification_pack_doctrine_anchors: string[];
};

type MappingRegistryBundleRow = {
  bundle_id: string;
  lifecycle_state: string;
  manifest_hash: string;
  owner_team: string;
  title?: string | null;
  notes?: string | null;
  predecessor_bundle_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

type MappingRegistryEdgeRow = {
  from_bundle_id: string;
  to_bundle_id: string;
  edge_kind: string;
  is_breaking: boolean;
  rationale?: string | null;
  declared_at?: string | null;
};

type MappingRegistryPinRow = {
  pin_id: string;
  tenant_id: string;
  bundle_id: string;
  scope_kind: string;
  scope_marker: string;
  effective_from?: string | null;
  policy_reference?: string | null;
  created_at?: string | null;
};

type MappingRegistryChangelogRow = {
  bundle_id: string;
  sequence_number: number;
  summary: string;
  breaking_classification: string;
  created_at?: string | null;
};

type MappingRegistryPayload = {
  registry_schema_version: number;
  mapping_registry_surface_version: number;
  phase: string;
  implementation_step: number;
  completed_implementation_steps: number[];
  name: string;
  tenant_id: string;
  bundles: MappingRegistryBundleRow[];
  compatibility_edges: MappingRegistryEdgeRow[];
  pins_for_tenant: MappingRegistryPinRow[];
  changelog_entries: MappingRegistryChangelogRow[];
  doctrine_anchors: string[];
};

type TransformFieldLineageRow = {
  field_path: string;
  rule_id: string;
  evidence_grade: string;
  confidence_class: string;
  confidence_metadata: Record<string, unknown>;
  source_paths: unknown[];
  value_snapshot?: unknown;
};

type TransformMaterializationRow = {
  id: string;
  tenant_id: string;
  bundle_id: string;
  raw_record_id: number;
  last_replay_job_id?: string | null;
  canonical_entity_id: string;
  phase04_boundary: Record<string, unknown>;
  canonical_object_kind: string;
  logical_key_json: Record<string, unknown>;
  logical_key_hash: string;
  emitted_snapshot_json: Record<string, unknown>;
  emitted_snapshot_hash: string;
  engine_build_ref: string;
  occurred_at?: string | null;
  observed_at?: string | null;
  canonical_processed_at?: string | null;
  source_revision_key?: string | null;
  temporal_ordering_key?: string | null;
  created_at?: string | null;
  confidence_rollup: { by_confidence_class: Record<string, number>; semantics: string };
  field_lineage: TransformFieldLineageRow[];
};

type TransformLineagePayload = {
  transform_runtime_schema_version: number;
  confidence_propagation_schema_version: number;
  tenant_id: string;
  materializations: TransformMaterializationRow[];
};

type ConfidenceSummaryPayload = {
  confidence_propagation_schema_version: number;
  tenant_id: string;
  field_lineage_rows_total: number;
  by_confidence_class: Record<string, number>;
  confidence_non_ranking_semantics: string;
};

type IdentityAnchorRow = {
  canonical_entity_id: string;
  bundle_id: string;
  canonical_object_kind: string;
  provider_identity_hash: string;
  logical_key_hash: string;
  raw_record_id: number;
  connector: string;
  phase04_boundary: Record<string, unknown>;
  engine_build_ref: string;
  updated_at?: string | null;
};

type IdentityAnchorsPayload = {
  identity_runtime_schema_version: number;
  tenant_id: string;
  anchors: IdentityAnchorRow[];
};

type ReplayJobRow = {
  id: string;
  tenant_id: string;
  pinned_bundle_id: string;
  job_kind: string;
  status: string;
  source_bundle_id?: string | null;
  dry_run: boolean;
  scope_raw_record_ids: number[];
  resolved_pin_json: Record<string, unknown>;
  engine_build_ref: string;
  summary_json: Record<string, unknown>;
  error_detail?: string | null;
  created_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
};

type ReplayJobsListPayload = {
  replay_runtime_schema_version: number;
  tenant_id: string;
  jobs: ReplayJobRow[];
};

type ReplayJobReceiptRow = {
  id: number;
  job_id: string;
  raw_record_id: number;
  divergence_class: string;
  detail_json: Record<string, unknown>;
  materialize_error?: string | null;
  created_at?: string | null;
};

type ReplayJobDetailPayload = {
  replay_runtime_schema_version: number;
  tenant_id: string;
  job: ReplayJobRow;
  receipts: ReplayJobReceiptRow[];
};

type ProvenanceRecordRow = {
  id: number;
  materialization_id: string;
  tenant_id: string;
  bundle_id: string;
  raw_record_id: number;
  canonical_object_kind: string;
  logical_key_hash: string;
  evidence_shape: string;
  primary_raw_record_ids: number[];
  rule_ids_involved: string[];
  derivation_json: Record<string, unknown>;
  parent_materialization_id?: string | null;
  created_at?: string | null;
};

type ProvenanceByRawPayload = {
  provenance_runtime_schema_version: number;
  tenant_id: string;
  raw_record_id: number;
  records: ProvenanceRecordRow[];
};

type TemporalSupersessionRow = {
  id: number;
  tenant_id: string;
  bundle_id: string;
  predecessor_materialization_id: string;
  predecessor_logical_key_hash: string;
  successor_materialization_id: string | null;
  causing_raw_record_id: number;
  engine_build_ref: string;
  created_at?: string | null;
};

type TemporalSupersessionsPayload = {
  temporal_runtime_schema_version: number;
  tenant_id: string;
  items: TemporalSupersessionRow[];
};

type TemporalRebuildPreviewPayload = {
  temporal_runtime_schema_version: number;
  tenant_id: string;
  ordered: Array<{
    raw_record_id: number;
    temporal_ordering_key: string;
    occurred_at: string;
    source_revision_key: string;
    replay_sequence: number;
  }>;
};

type CanonicalQueryResponsePayload = {
  canonical_query_runtime_schema_version: number;
  tenant_id: string;
  query_class: string;
  result_kind: string;
  payload: Record<string, unknown>;
  truncation: Record<string, unknown> | null;
};

type AmbiguityConnectorRollup = {
  connector: string;
  resource_type: string;
  total: number;
  open_count: number;
};

type AmbiguityRecordRow = {
  id: string;
  tenant_id: string;
  bundle_id: string;
  ambiguity_class: string;
  scope: string;
  record_handle?: string | null;
  raw_record_ids: number[];
  rule_ids_involved: string[];
  primary_connector?: string | null;
  primary_resource_type?: string | null;
  status: string;
  created_at?: string | null;
};

type AmbiguityListPayload = {
  ambiguity_runtime_schema_version: number;
  tenant_id: string;
  aggregates: {
    by_status: Record<string, number>;
    by_class: Record<string, number>;
    by_connector_resource: AmbiguityConnectorRollup[];
  };
  records: AmbiguityRecordRow[];
};

type OracleExpectedLK = {
  canonical_object_kind: string;
  tuple_field_names: string[];
  example_normalized_tuple: string[];
};

type OracleVector = {
  fixture_id: string;
  coverage_tags: string[];
  raw_snapshot_ref: string;
  mapping_bundle_id: string;
  mapping_manifest_hash: string;
  engine_build_ref: string;
  expected_logical_keys: OracleExpectedLK[];
  expected_ordering: Record<string, unknown>[];
  expected_ambiguity_records: Record<string, unknown>[];
  expected_provenance_edges: Record<string, unknown>[];
  allowed_divergence_classes: string[];
  injected_fault?: string | null;
};

type OracleManifestPayload = {
  oracle_manifest_schema_version: number;
  phase: string;
  implementation_step: number;
  completed_implementation_steps: number[];
  name: string;
  tenant_id?: string | null;
  mapping_bundle_id: string;
  mapping_manifest_hash: string;
  engine_build_ref: string;
  oracle_manifest_doctrine_anchors: string[];
  coverage_categories_documented: string[];
  vectors: OracleVector[];
};

/** Full combined ontology + operational tools page (legacy escape hatch). */
export default function AdminCortexCanonicalLegacyOntologyToolsPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const queryClient = useQueryClient();
  const [matRawId, setMatRawId] = useState("");
  const [matBundleId, setMatBundleId] = useState("bundle.phase03.step03.logical_keys.v1");
  const [ambBundleId, setAmbBundleId] = useState("bundle.phase03.step03.logical_keys.v1");
  const [ambClass, setAmbClass] = useState("competing_canonical_candidates");
  const [ambScope, setAmbScope] = useState("issue.status_transition");
  const [ambRawIds, setAmbRawIds] = useState("");
  const [ambHandle, setAmbHandle] = useState("");
  const [ambLifecycleId, setAmbLifecycleId] = useState("");
  const [ambLifecycleTarget, setAmbLifecycleTarget] = useState("void");
  const [ambLifecycleNote, setAmbLifecycleNote] = useState("");
  const [replayRawIds, setReplayRawIds] = useState("");
  const [replayBundleId, setReplayBundleId] = useState("bundle.phase03.step03.logical_keys.v1");
  const [replayJobKind, setReplayJobKind] = useState<"rebuild" | "regeneration">("rebuild");
  const [replaySourceBundle, setReplaySourceBundle] = useState("");
  const [replayDryRun, setReplayDryRun] = useState(true);
  const [provRawId, setProvRawId] = useState("");
  const [temporalPreviewIds, setTemporalPreviewIds] = useState("");
  const [cqClass, setCqClass] = useState("point_lookup_materialization");
  const [cqIntent, setCqIntent] = useState("evidence_retrieval");
  const [cqQueryText, setCqQueryText] = useState("");
  const [cqParamsJson, setCqParamsJson] = useState("{}");
  const [cqLimit, setCqLimit] = useState("30");
  const [remediationClass, setRemediationClass] = useState<"scoped_rebuild" | "ambiguity_triage_ack">(
    "scoped_rebuild",
  );
  const [remediationDryRun, setRemediationDryRun] = useState(true);
  const [remediationConfirm, setRemediationConfirm] = useState(false);
  const [remediationGapId, setRemediationGapId] = useState("");
  const [remediationPayloadJson, setRemediationPayloadJson] = useState(
    '{"pinned_bundle_id":"bundle.phase03.step03.logical_keys.v1","job_kind":"rebuild","raw_record_ids":[]}',
  );
  const [verifPersist, setVerifPersist] = useState(true);
  const [verifSampleLimit, setVerifSampleLimit] = useState("50");
  const qOnt = useQuery({
    queryKey: ["admin-cortex-canonical-ontology", tenantId],
    queryFn: () =>
      adminJson<CanonicalOntologyPayload>(`/admin/tenants/${tenantId}/cortex/canonical/ontology`),
    enabled: Boolean(tenantId),
  });
  const qOracle = useQuery({
    queryKey: ["admin-cortex-canonical-oracle-manifest", tenantId],
    queryFn: () =>
      adminJson<OracleManifestPayload>(`/admin/tenants/${tenantId}/cortex/canonical/oracle-manifest`),
    enabled: Boolean(tenantId),
  });
  const qRegistry = useQuery({
    queryKey: ["admin-cortex-canonical-mapping-registry", tenantId],
    queryFn: () =>
      adminJson<MappingRegistryPayload>(`/admin/tenants/${tenantId}/cortex/canonical/mapping-registry`),
    enabled: Boolean(tenantId),
  });
  const qLineage = useQuery({
    queryKey: ["admin-cortex-transform-lineage", tenantId],
    queryFn: () =>
      adminJson<TransformLineagePayload>(
        `/admin/tenants/${tenantId}/cortex/canonical/transform/lineage?limit=30`,
      ),
    enabled: Boolean(tenantId),
  });
  const qConfidenceSummary = useQuery({
    queryKey: ["admin-cortex-confidence-summary", tenantId],
    queryFn: () =>
      adminJson<ConfidenceSummaryPayload>(`/admin/tenants/${tenantId}/cortex/canonical/confidence/summary`),
    enabled: Boolean(tenantId),
  });
  const qIdentityAnchors = useQuery({
    queryKey: ["admin-cortex-identity-anchors", tenantId],
    queryFn: () =>
      adminJson<IdentityAnchorsPayload>(`/admin/tenants/${tenantId}/cortex/canonical/identity/anchors?limit=40`),
    enabled: Boolean(tenantId),
  });
  const qReplayJobs = useQuery({
    queryKey: ["admin-cortex-replay-jobs", tenantId],
    queryFn: () =>
      adminJson<ReplayJobsListPayload>(`/admin/tenants/${tenantId}/cortex/canonical/replay-jobs?limit=20`),
    enabled: Boolean(tenantId),
  });
  type FailuresPayload = {
    failure_remediation_runtime_schema_version: number;
    tenant_id: string;
    active_failure_count: number;
    active_failure_classes: Record<string, number>;
    cases: Array<{
      gap_id: string;
      failure_class: string;
      degradation_state: string;
      scope_kind: string;
      detail_json: Record<string, unknown>;
      source: string;
    }>;
    recent_remediation_validations: Array<{
      id: number;
      remediation_class: string;
      result_status: string;
      created_at: string | null;
    }>;
  };
  const qFailures = useQuery({
    queryKey: ["admin-cortex-canonical-failures", tenantId],
    queryFn: () => adminJson<FailuresPayload>(`/admin/tenants/${tenantId}/cortex/canonical/failures`),
    enabled: Boolean(tenantId),
  });
  type VerificationRunsPayload = {
    canonical_verification_engine_schema_version: number;
    tenant_id: string;
    runs: Array<{
      id: number;
      passed: boolean;
      engine_schema_version: number;
      created_at: string | null;
    }>;
  };
  const qVerificationRuns = useQuery({
    queryKey: ["admin-cortex-canonical-verification-runs", tenantId],
    queryFn: () =>
      adminJson<VerificationRunsPayload>(
        `/admin/tenants/${tenantId}/cortex/canonical/verification/runs?limit=10`,
      ),
    enabled: Boolean(tenantId),
  });
  const provRawIdNum = Number.parseInt(provRawId.trim(), 10);
  const qProvenanceByRaw = useQuery({
    queryKey: ["admin-cortex-provenance-by-raw", tenantId, provRawIdNum],
    queryFn: () =>
      adminJson<ProvenanceByRawPayload>(
        `/admin/tenants/${tenantId}/cortex/canonical/provenance/raw-records/${provRawIdNum}?limit=40`,
      ),
    enabled: Boolean(tenantId) && Number.isFinite(provRawIdNum) && provRawIdNum > 0,
  });
  const qTemporalSupersessions = useQuery({
    queryKey: ["admin-cortex-temporal-supersessions", tenantId],
    queryFn: () =>
      adminJson<TemporalSupersessionsPayload>(
        `/admin/tenants/${tenantId}/cortex/canonical/temporal/supersessions?limit=30`,
      ),
    enabled: Boolean(tenantId),
  });
  const qAmbiguity = useQuery({
    queryKey: ["admin-cortex-canonical-ambiguity", tenantId],
    queryFn: () =>
      adminJson<AmbiguityListPayload>(`/admin/tenants/${tenantId}/cortex/canonical/ambiguity?limit=40`),
    enabled: Boolean(tenantId),
  });
  const materializeMut = useMutation({
    mutationFn: async () => {
      const rawId = Number.parseInt(matRawId, 10);
      if (!Number.isFinite(rawId)) {
        throw new Error("raw_record_id must be a decimal integer");
      }
      return adminJson<{ materialization: TransformMaterializationRow }>(
        `/admin/tenants/${tenantId}/cortex/canonical/transform/materialize`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ raw_record_id: rawId, bundle_id: matBundleId }),
        },
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-transform-lineage", tenantId] });
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-confidence-summary", tenantId] });
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-identity-anchors", tenantId] });
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-replay-jobs", tenantId] });
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-provenance-by-raw", tenantId] });
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-temporal-supersessions", tenantId] });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-canonical-failures", tenantId] });
    },
  });
  const temporalPreviewMut = useMutation({
    mutationFn: async () => {
      const ids = temporalPreviewIds
        .split(/[\s,]+/)
        .map((s) => s.trim())
        .filter(Boolean)
        .map((s) => Number.parseInt(s, 10))
        .filter((n) => Number.isFinite(n));
      if (ids.length === 0) throw new Error("Enter at least one raw_record_id (comma or space separated)");
      return adminJson<TemporalRebuildPreviewPayload>(
        `/admin/tenants/${tenantId}/cortex/canonical/temporal/rebuild-preview`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ raw_record_ids: ids }),
        },
      );
    },
  });
  const canonicalQueryMut = useMutation({
    mutationFn: async () => {
      let params: Record<string, unknown>;
      try {
        params = JSON.parse(cqParamsJson.trim() || "{}") as Record<string, unknown>;
      } catch {
        throw new Error("params must be valid JSON object");
      }
      const lim = Number.parseInt(cqLimit, 10);
      return adminJson<CanonicalQueryResponsePayload>(
        `/admin/tenants/${tenantId}/cortex/canonical/query`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query_class: cqClass,
            intent: cqIntent,
            query_text: cqQueryText.trim() || undefined,
            params,
            limit: Number.isFinite(lim) ? lim : 30,
          }),
        },
      );
    },
  });
  const replayRunMut = useMutation({
    mutationFn: async () => {
      const ids = replayRawIds
        .split(/[\s,]+/)
        .map((s) => s.trim())
        .filter(Boolean)
        .map((s) => Number.parseInt(s, 10))
        .filter((n) => Number.isFinite(n));
      if (ids.length === 0) throw new Error("Enter at least one raw_record_id (comma or space separated)");
      const body: Record<string, unknown> = {
        pinned_bundle_id: replayBundleId.trim(),
        job_kind: replayJobKind,
        raw_record_ids: ids,
        dry_run: replayDryRun,
      };
      const src = replaySourceBundle.trim();
      if (replayJobKind === "regeneration" && src) body.source_bundle_id = src;
      return adminJson<ReplayJobDetailPayload>(
        `/admin/tenants/${tenantId}/cortex/canonical/replay-jobs/run`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-replay-jobs", tenantId] });
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-transform-lineage", tenantId] });
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-identity-anchors", tenantId] });
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-provenance-by-raw", tenantId] });
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-temporal-supersessions", tenantId] });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-canonical-failures", tenantId] });
    },
  });
  const remediationMut = useMutation({
    mutationFn: async () => {
      let payload: Record<string, unknown>;
      try {
        payload = JSON.parse(remediationPayloadJson.trim() || "{}") as Record<string, unknown>;
      } catch {
        throw new Error("payload must be valid JSON object");
      }
      return adminJson<{
        tenant_id: string;
        remediation_class: string;
        validation: Record<string, unknown>;
      }>(`/admin/tenants/${tenantId}/cortex/canonical/remediation/validate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          remediation_class: remediationClass,
          dry_run: remediationDryRun,
          confirm_execution: remediationConfirm,
          failure_case_gap_id: remediationGapId.trim() || undefined,
          payload,
        }),
      });
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-canonical-failures", tenantId] });
    },
  });
  const verificationRunMut = useMutation({
    mutationFn: async () => {
      const lim = Number.parseInt(verifSampleLimit, 10);
      return adminJson<Record<string, unknown>>(
        `/admin/tenants/${tenantId}/cortex/canonical/verification/run`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            persist: verifPersist,
            materialization_sample_limit: Number.isFinite(lim) ? lim : 50,
          }),
        },
      );
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-canonical-verification-runs", tenantId] });
    },
  });
  const openAmbiguityMut = useMutation({
    mutationFn: async () => {
      const ids = ambRawIds
        .split(/[\s,]+/)
        .map((s) => s.trim())
        .filter(Boolean)
        .map((s) => Number.parseInt(s, 10))
        .filter((n) => Number.isFinite(n));
      if (ids.length === 0) throw new Error("Enter at least one raw_record_id (comma or space separated)");
      return adminJson<{ record: AmbiguityRecordRow }>(`/admin/tenants/${tenantId}/cortex/canonical/ambiguity`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bundle_id: ambBundleId,
          ambiguity_class: ambClass,
          scope: ambScope,
          raw_record_ids: ids,
          record_handle: ambHandle.trim() || undefined,
          rule_ids_involved: [],
        }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-canonical-ambiguity", tenantId] });
    },
  });
  const ambiguityLifecycleMut = useMutation({
    mutationFn: async () => {
      const id = ambLifecycleId.trim();
      if (!id) throw new Error("ambiguity UUID required");
      return adminJson<{ record: AmbiguityRecordRow }>(
        `/admin/tenants/${tenantId}/cortex/canonical/ambiguity/${id}/lifecycle`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            target_status: ambLifecycleTarget,
            supersession_note: ambLifecycleNote.trim() || undefined,
          }),
        },
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-cortex-canonical-ambiguity", tenantId] });
    },
  });

  if (!tenantId) return <p className="text-sm text-red-700">Missing tenant.</p>;
  if (qOnt.isPending) return <p className="text-sm text-stone-600">Loading canonical ontology…</p>;
  if (qOnt.isError) return <p className="text-sm text-red-700">{(qOnt.error as Error).message}</p>;

  const d = qOnt.data;

  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-amber-200 bg-amber-50/70 p-4 shadow-sm ring-1 ring-amber-100">
        <p className="text-sm font-semibold text-amber-950">Legacy combined tools page</p>
        <p className="mt-1 text-xs text-amber-900/90">
          Prefer the operator tabs on the parent Canonical layout (Overview / Runtime / …). This page preserves the
          original single-scroll tooling surface.
        </p>
      </section>
      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Canonical ontology (Phase 03 Steps 1–18)</h2>
        <p className="mt-1 text-sm text-stone-600">
          Frozen structural kinds, taxonomy, logical keys, deterministic mapping contracts (E0/E1), mapping bundle
          registry (pins + compatibility), transform + confidence + provider-scoped identity anchors (Phase 04
          handoff hooks), replay + provenance + temporal ordering + bounded canonical query surfaces,
          failure/remediation operator paths, ambiguity persistence, oracle manifest, verification engine, operator
          control-plane + stabilization proof route metadata, and non-interpretive class graph—substrate only (no
          semantic cognition).
        </p>
        <dl className="mt-4 grid gap-2 text-sm text-stone-800 md:grid-cols-2">
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Schema version</dt>
            <dd className="font-mono">{d.ontology_schema_version}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Implementation step</dt>
            <dd className="font-mono">
              Phase {d.phase} / Step {d.implementation_step}
            </dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Completed steps</dt>
            <dd className="font-mono">{d.completed_implementation_steps.join(", ")}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Registry surface</dt>
            <dd className="font-mono text-xs">v{d.mapping_registry_surface_version}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Mapping registry route</dt>
            <dd className="break-all font-mono text-xs text-stone-700">{d.mapping_registry_admin_route}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Transform runtime surface</dt>
            <dd className="font-mono text-xs">v{d.transform_runtime_surface_version}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Transform materialize route</dt>
            <dd className="break-all font-mono text-xs text-stone-700">{d.transform_materialize_route}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Transform lineage route</dt>
            <dd className="break-all font-mono text-xs text-stone-700">{d.transform_lineage_route}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Lineage includes confidence</dt>
            <dd className="font-mono text-xs">{d.transform_lineage_includes_confidence ? "yes" : "no"}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Confidence surface</dt>
            <dd className="font-mono text-xs">v{d.confidence_propagation_surface_version}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Confidence summary route</dt>
            <dd className="break-all font-mono text-xs text-stone-700">{d.confidence_summary_admin_route}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Transform lineage doctrine</dt>
            <dd className="mt-1 space-y-1 font-mono text-xs text-stone-700">
              {d.transform_runtime_doctrine_anchors.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Ambiguity runtime surface</dt>
            <dd className="font-mono text-xs">v{d.ambiguity_runtime_surface_version}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Ambiguity list route</dt>
            <dd className="break-all font-mono text-xs text-stone-700">{d.ambiguity_list_route}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Ambiguity open / lifecycle</dt>
            <dd className="break-all font-mono text-xs text-stone-700">
              {d.ambiguity_open_route} · {d.ambiguity_lifecycle_route}
            </dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Ambiguity doctrine</dt>
            <dd className="mt-1 space-y-1 font-mono text-xs text-stone-700">
              {d.ambiguity_runtime_doctrine_anchors.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Identity runtime surface</dt>
            <dd className="font-mono text-xs">v{d.identity_runtime_surface_version}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Identity anchors routes</dt>
            <dd className="break-all font-mono text-xs text-stone-700">
              {d.identity_anchors_list_route} · {d.identity_anchor_detail_route}
            </dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Identity continuity doctrine</dt>
            <dd className="mt-1 space-y-1 font-mono text-xs text-stone-700">
              {d.identity_runtime_doctrine_anchors.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Replay runtime surface</dt>
            <dd className="font-mono text-xs">v{d.replay_runtime_surface_version}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Replay job routes</dt>
            <dd className="break-all font-mono text-xs text-stone-700">
              {d.replay_job_run_route} · {d.replay_jobs_list_route}
            </dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Replay job detail route</dt>
            <dd className="break-all font-mono text-xs text-stone-700">{d.replay_job_detail_route}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Replay versioning doctrine</dt>
            <dd className="mt-1 space-y-1 font-mono text-xs text-stone-700">
              {d.replay_runtime_doctrine_anchors.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Provenance runtime surface</dt>
            <dd className="font-mono text-xs">v{d.provenance_runtime_surface_version}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Transform emits provenance</dt>
            <dd className="font-mono text-xs">{d.transform_emits_provenance_record ? "yes" : "no"}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Provenance routes</dt>
            <dd className="break-all font-mono text-xs text-stone-700">
              {d.provenance_by_raw_record_route} · {d.provenance_by_materialization_route}
            </dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Provenance traceability doctrine</dt>
            <dd className="mt-1 space-y-1 font-mono text-xs text-stone-700">
              {d.provenance_runtime_doctrine_anchors.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Temporal runtime surface</dt>
            <dd className="font-mono text-xs">v{d.temporal_runtime_surface_version}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Transform persists temporal ordering</dt>
            <dd className="font-mono text-xs">{d.transform_persists_temporal_ordering ? "yes" : "no"}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Temporal routes</dt>
            <dd className="break-all font-mono text-xs text-stone-700">
              {d.temporal_supersessions_list_route} · {d.temporal_rebuild_preview_route}
            </dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Temporal ordering precedence</dt>
            <dd className="mt-1 space-y-1 text-xs text-stone-700">
              {d.temporal_ordering_precedence.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Temporal timeline doctrine</dt>
            <dd className="mt-1 space-y-1 font-mono text-xs text-stone-700">
              {d.temporal_runtime_doctrine_anchors.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Canonical query surface</dt>
            <dd className="font-mono text-xs">v{d.canonical_query_surface_version}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Canonical query route</dt>
            <dd className="break-all font-mono text-xs text-stone-700">{d.canonical_query_route}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Canonical query doctrine</dt>
            <dd className="mt-1 space-y-1 font-mono text-xs text-stone-700">
              {d.canonical_query_doctrine_anchors.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Failure + remediation surface</dt>
            <dd className="font-mono text-xs">v{d.failure_remediation_surface_version}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Canonical failures route</dt>
            <dd className="break-all font-mono text-xs text-stone-700">{d.canonical_failures_route}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Canonical remediation validate route</dt>
            <dd className="break-all font-mono text-xs text-stone-700">{d.canonical_remediation_validate_route}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Failure / remediation doctrine</dt>
            <dd className="mt-1 space-y-1 font-mono text-xs text-stone-700">
              {d.failure_remediation_doctrine_anchors.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Verification engine surface</dt>
            <dd className="font-mono text-xs">v{d.verification_engine_surface_version}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Verification run route</dt>
            <dd className="break-all font-mono text-xs text-stone-700">{d.canonical_verification_run_route}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Verification runs list route</dt>
            <dd className="break-all font-mono text-xs text-stone-700">{d.canonical_verification_runs_list_route}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Gates exercised (subset)</dt>
            <dd className="font-mono text-[11px] text-stone-800">{d.verification_engine_gate_ids.join(", ")}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Verification engine doctrine</dt>
            <dd className="mt-1 space-y-1 font-mono text-xs text-stone-700">
              {d.verification_engine_doctrine_anchors.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Control plane surface</dt>
            <dd className="font-mono text-xs">v{d.canonical_control_plane_surface_version}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Control plane route</dt>
            <dd className="break-all font-mono text-xs text-stone-700">{d.canonical_control_plane_route}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Control plane doctrine</dt>
            <dd className="mt-1 space-y-1 font-mono text-xs text-stone-700">
              {d.canonical_control_plane_doctrine_anchors.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Stabilization proof surface</dt>
            <dd className="font-mono text-xs">v{d.stabilization_proof_surface_version}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Stabilization proof GET</dt>
            <dd className="break-all font-mono text-xs text-stone-700">{d.canonical_stabilization_proof_route}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Stabilization proof POST</dt>
            <dd className="break-all font-mono text-xs text-stone-700">
              {d.canonical_stabilization_proof_run_route}
            </dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Stabilization proof runs list</dt>
            <dd className="break-all font-mono text-xs text-stone-700">
              {d.canonical_stabilization_proof_runs_route}
            </dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Stabilization proof doctrine</dt>
            <dd className="mt-1 space-y-1 font-mono text-xs text-stone-700">
              {d.stabilization_proof_doctrine_anchors.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-stone-500">Certification pack surface</dt>
            <dd className="font-mono text-xs">v{d.certification_pack_surface_version}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Certification pack GET</dt>
            <dd className="break-all font-mono text-xs text-stone-700">{d.canonical_certification_pack_route}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Certification pack archive POST</dt>
            <dd className="break-all font-mono text-xs text-stone-700">
              {d.canonical_certification_pack_archive_route}
            </dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Certification pack archives list</dt>
            <dd className="break-all font-mono text-xs text-stone-700">
              {d.canonical_certification_pack_archives_route}
            </dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Certification pack doctrine</dt>
            <dd className="mt-1 space-y-1 font-mono text-xs text-stone-700">
              {d.certification_pack_doctrine_anchors.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-wide text-stone-500">Doctrine anchors</dt>
            <dd className="mt-1 space-y-1 font-mono text-xs text-stone-700">
              {d.doctrine_anchors.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </dd>
          </div>
        </dl>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Layers</h3>
        <p className="mt-1 text-sm text-stone-600">Structural discriminant only—not provider-specific.</p>
        <ul className="mt-3 flex flex-wrap gap-2">
          {d.layers.map((layer) => (
            <li key={layer} className="rounded-md bg-stone-100 px-2 py-1 font-mono text-xs text-stone-800">
              {layer}
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Taxonomy families ({d.taxonomy_families.length})</h3>
        <p className="mt-1 text-sm text-stone-600">
          Entity / artifact / event / relationship / reference / snapshot boundaries (doctrine-aligned text).
        </p>
        <ul className="mt-3 space-y-3 text-sm text-stone-800">
          {d.taxonomy_families.map((fam) => (
            <li key={fam.id} className="rounded-lg border border-stone-100 bg-stone-50/80 p-3">
              <div className="font-mono text-xs font-semibold text-stone-900">{fam.id}</div>
              <p className="mt-1 text-sm leading-relaxed text-stone-700">{fam.boundary_definition}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Taxonomy hard rules</h3>
        <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-stone-700">
          {d.taxonomy_hard_rules.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">
          Logical keys (profile v{d.logical_key_profile_version})
        </h3>
        <p className="mt-1 text-sm text-stone-600">
          Ordered idempotency tuple fields per canonical object kind (`phase-03-logical-key-doctrine.md`).
        </p>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-stone-500">Global rules</h4>
            <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-stone-700">
              {d.logical_key_global_rules.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-stone-500">Logical-key doctrine</h4>
            <div className="mt-2 space-y-1 font-mono text-xs text-stone-700">
              {d.logical_key_doctrine_anchors.map((p) => (
                <div key={p}>{p}</div>
              ))}
            </div>
          </div>
        </div>
        <div className="mt-4 overflow-x-auto rounded border border-stone-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-700">
              <tr>
                <th className="px-2 py-2">canonical_object_kind</th>
                <th className="px-2 py-2">idempotency_tuple_fields</th>
                <th className="px-2 py-2">tie_break_notes</th>
              </tr>
            </thead>
            <tbody>
              {d.logical_keys_by_kind.map((row) => (
                <tr key={row.canonical_object_kind} className="border-t border-stone-100">
                  <td className="px-2 py-2 align-top font-mono text-stone-900">{row.canonical_object_kind}</td>
                  <td className="px-2 py-2 align-top font-mono text-[11px] text-stone-800">
                    {row.idempotency_tuple_fields.join(", ")}
                  </td>
                  <td className="px-2 py-2 align-top text-stone-700">{row.tie_break_notes ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">
          Deterministic mapping contracts (schema v{d.mapping_contract_schema_version})
        </h3>
        <p className="mt-1 text-sm text-stone-600">
          Evidence grades, allowed transforms, forbidden anti-goals, and frozen mapping-table row shape (
          <code className="rounded bg-stone-100 px-1">phase-03-deterministic-canonicalization-doctrine.md</code>
          ).
        </p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {d.evidence_grades.map((g) => (
            <div key={g.id} className="rounded-lg border border-indigo-100 bg-indigo-50/50 p-4">
              <div className="font-mono text-xs font-semibold text-indigo-900">{g.label}</div>
              <p className="mt-2 text-sm leading-relaxed text-stone-800">{g.definition}</p>
            </div>
          ))}
        </div>
        <div className="mt-6">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-stone-500">Determinism criteria</h4>
          <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-stone-700">
            {d.determinism_criteria.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-stone-500">Structural extraction</h4>
            <p className="mt-2 text-sm leading-relaxed text-stone-700">{d.structural_extraction_definition}</p>
          </div>
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-stone-500">
              Semantic inference (forbidden)
            </h4>
            <p className="mt-2 text-sm leading-relaxed text-stone-700">
              {d.semantic_inference_forbidden_definition}
            </p>
          </div>
        </div>
        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-stone-500">
              Allowed deterministic operations
            </h4>
            <ul className="mt-2 space-y-3 text-sm text-stone-800">
              {d.allowed_deterministic_operations.map((op) => (
                <li key={op.id}>
                  <span className="font-mono text-xs text-stone-900">{op.id}</span>
                  <p className="mt-1 text-stone-700">{op.description}</p>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-stone-500">Forbidden operations</h4>
            <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-red-900/90">
              {d.forbidden_operations.map((rule) => (
                <li key={rule}>{rule}</li>
              ))}
            </ul>
          </div>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-stone-500">Field emission posture</h4>
            <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-stone-700">
              {d.field_emission_posture_rules.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-stone-500">Mapping versioning</h4>
            <ul className="mt-2 list-disc space-y-2 pl-5 text-sm text-stone-700">
              {d.mapping_versioning_rules.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </div>
        </div>
        <div className="mt-6">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-stone-500">
            Frozen mapping-table row shape (bundle authoring)
          </h4>
          <div className="mt-3 overflow-x-auto rounded border border-stone-200">
            <table className="min-w-full text-left text-xs">
              <thead className="bg-stone-50 text-stone-700">
                <tr>
                  <th className="px-2 py-2">column</th>
                  <th className="px-2 py-2">type</th>
                  <th className="px-2 py-2">required</th>
                  <th className="px-2 py-2">description</th>
                </tr>
              </thead>
              <tbody>
                {d.mapping_table_row_shape.map((col) => (
                  <tr key={col.column} className="border-t border-stone-100">
                    <td className="px-2 py-2 font-mono text-stone-900">{col.column}</td>
                    <td className="px-2 py-2 font-mono text-stone-800">{col.value_type}</td>
                    <td className="px-2 py-2 font-mono">{col.required ? "yes" : "no"}</td>
                    <td className="px-2 py-2 text-stone-700">{col.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="mt-4 font-mono text-xs text-stone-600">
          {d.mapping_contract_doctrine_anchors.map((p) => (
            <div key={p}>{p}</div>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Mapping bundle registry (Phase 03 Step 5)</h3>
        <p className="mt-1 text-sm text-stone-600">
          Authoritative bundle inventory, compatibility edges, changelog, and tenant pins (
          <code className="rounded bg-stone-100 px-1">phase-03-mapping-bundle-registry.md</code>
          ).
        </p>
        {qRegistry.isPending ? (
          <p className="mt-3 text-sm text-stone-600">Loading mapping registry…</p>
        ) : qRegistry.isError ? (
          <p className="mt-3 text-sm text-red-700">{(qRegistry.error as Error).message}</p>
        ) : (
          <>
            <dl className="mt-4 grid gap-2 text-sm text-stone-800 md:grid-cols-3">
              <div>
                <dt className="text-xs uppercase tracking-wide text-stone-500">Runtime schema</dt>
                <dd className="font-mono">{qRegistry.data.registry_schema_version}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-stone-500">Bundles</dt>
                <dd className="font-mono">{qRegistry.data.bundles.length}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-stone-500">Pins (this tenant)</dt>
                <dd className="font-mono">{qRegistry.data.pins_for_tenant.length}</dd>
              </div>
            </dl>
            <div className="mt-4 overflow-x-auto rounded border border-stone-200">
              <table className="min-w-full text-left text-xs">
                <thead className="bg-stone-50 text-stone-700">
                  <tr>
                    <th className="px-2 py-2">bundle_id</th>
                    <th className="px-2 py-2">state</th>
                    <th className="px-2 py-2">manifest_hash</th>
                    <th className="px-2 py-2">owner_team</th>
                  </tr>
                </thead>
                <tbody>
                  {qRegistry.data.bundles.map((b) => (
                    <tr key={b.bundle_id} className="border-t border-stone-100">
                      <td className="px-2 py-2 font-mono text-stone-900">{b.bundle_id}</td>
                      <td className="px-2 py-2 font-mono text-stone-800">{b.lifecycle_state}</td>
                      <td className="px-2 py-2 font-mono text-[11px] text-stone-700">{b.manifest_hash}</td>
                      <td className="px-2 py-2 text-stone-700">{b.owner_team}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <h4 className="mt-6 text-xs font-semibold uppercase tracking-wide text-stone-500">
              Compatibility edges ({qRegistry.data.compatibility_edges.length})
            </h4>
            <div className="mt-2 overflow-x-auto rounded border border-stone-200">
              <table className="min-w-full text-left text-xs">
                <thead className="bg-stone-50 text-stone-700">
                  <tr>
                    <th className="px-2 py-2">from</th>
                    <th className="px-2 py-2">to</th>
                    <th className="px-2 py-2">edge_kind</th>
                    <th className="px-2 py-2">breaking</th>
                  </tr>
                </thead>
                <tbody>
                  {qRegistry.data.compatibility_edges.length === 0 ? (
                    <tr className="border-t border-stone-100">
                      <td className="px-2 py-2 text-stone-600 md:col-span-4" colSpan={4}>
                        No compatibility edges declared yet.
                      </td>
                    </tr>
                  ) : (
                    qRegistry.data.compatibility_edges.map((e, i) => (
                      <tr key={`${e.from_bundle_id}-${e.to_bundle_id}-${i}`} className="border-t border-stone-100">
                        <td className="px-2 py-2 font-mono">{e.from_bundle_id}</td>
                        <td className="px-2 py-2 font-mono">{e.to_bundle_id}</td>
                        <td className="px-2 py-2 font-mono">{e.edge_kind}</td>
                        <td className="px-2 py-2 font-mono">{e.is_breaking ? "yes" : "no"}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            <h4 className="mt-6 text-xs font-semibold uppercase tracking-wide text-stone-500">
              Tenant pins ({qRegistry.data.pins_for_tenant.length})
            </h4>
            <div className="mt-2 overflow-x-auto rounded border border-stone-200">
              <table className="min-w-full text-left text-xs">
                <thead className="bg-stone-50 text-stone-700">
                  <tr>
                    <th className="px-2 py-2">bundle_id</th>
                    <th className="px-2 py-2">scope_kind</th>
                    <th className="px-2 py-2">scope_marker</th>
                  </tr>
                </thead>
                <tbody>
                  {qRegistry.data.pins_for_tenant.length === 0 ? (
                    <tr className="border-t border-stone-100">
                      <td className="px-2 py-2 text-stone-600" colSpan={3}>
                        No pins for this tenant — resolve bundle via policy or create pins in later operator workflows.
                      </td>
                    </tr>
                  ) : (
                    qRegistry.data.pins_for_tenant.map((p) => (
                      <tr key={p.pin_id} className="border-t border-stone-100">
                        <td className="px-2 py-2 font-mono">{p.bundle_id}</td>
                        <td className="px-2 py-2 font-mono">{p.scope_kind}</td>
                        <td className="px-2 py-2 font-mono">{p.scope_marker || "—"}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            <h4 className="mt-6 text-xs font-semibold uppercase tracking-wide text-stone-500">Changelog</h4>
            <ul className="mt-2 space-y-3 text-sm text-stone-800">
              {qRegistry.data.changelog_entries.map((c) => (
                <li key={`${c.bundle_id}-${c.sequence_number}`} className="rounded-lg border border-stone-100 bg-stone-50/80 p-3">
                  <div className="font-mono text-xs text-stone-900">
                    {c.bundle_id} · seq {c.sequence_number}{" "}
                    <span className="text-stone-600">({c.breaking_classification})</span>
                  </div>
                  <p className="mt-1 text-sm text-stone-700">{c.summary}</p>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Transform runtime + field lineage (Phase 03 Steps 6–9)</h3>
        <p className="mt-1 text-sm text-stone-600">
          Deterministic stub routing emits logical keys, emitted snapshots, SHA-256 hashes, and per-field lineage
          receipts with Phase 03 confidence classes (structured metadata only—never ranking weights). Materialization
          requires an approved/candidate mapping bundle and a raw row whose connector + resource_type matches a stub
          rule (Slack message, GitHub/Linear issue).
        </p>
        <div className="mt-4 flex flex-wrap items-end gap-3 rounded-lg border border-stone-100 bg-stone-50/80 p-4">
          <label className="flex flex-col gap-1 text-xs text-stone-600">
            raw_record_id
            <input
              className="rounded border border-stone-200 bg-white px-2 py-1 font-mono text-sm text-stone-900"
              value={matRawId}
              onChange={(e) => setMatRawId(e.target.value)}
              placeholder="e.g. 42"
            />
          </label>
          <label className="min-w-[14rem] flex flex-col gap-1 text-xs text-stone-600">
            bundle_id
            <input
              className="rounded border border-stone-200 bg-white px-2 py-1 font-mono text-sm text-stone-900"
              value={matBundleId}
              onChange={(e) => setMatBundleId(e.target.value)}
            />
          </label>
          <button
            type="button"
            className="rounded-md bg-stone-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
            disabled={materializeMut.isPending}
            onClick={() => materializeMut.mutate()}
          >
            {materializeMut.isPending ? "Materializing…" : "POST materialize"}
          </button>
        </div>
        {materializeMut.isError ? (
          <p className="mt-2 text-sm text-red-700">{(materializeMut.error as Error).message}</p>
        ) : null}
        {materializeMut.isSuccess ? (
          <p className="mt-2 text-sm text-emerald-800">
            Materialized {materializeMut.data.materialization.canonical_object_kind} — entity{" "}
            <span className="font-mono text-xs">{materializeMut.data.materialization.canonical_entity_id.slice(0, 13)}…</span>{" "}
            · lk{" "}
            <span className="font-mono">{materializeMut.data.materialization.logical_key_hash.slice(0, 16)}…</span>
          </p>
        ) : null}

        <h4 className="mt-6 text-xs font-semibold uppercase tracking-wide text-stone-500">Confidence summary (tenant)</h4>
        {qConfidenceSummary.isPending ? (
          <p className="mt-2 text-sm text-stone-600">Loading confidence summary…</p>
        ) : qConfidenceSummary.isError ? (
          <p className="mt-2 text-sm text-red-700">{(qConfidenceSummary.error as Error).message}</p>
        ) : (
          <div className="mt-2 rounded-lg border border-stone-100 bg-stone-50/80 p-3 text-xs text-stone-800">
            <p className="font-mono">
              confidence schema v{qConfidenceSummary.data.confidence_propagation_schema_version} ·{" "}
              {qConfidenceSummary.data.field_lineage_rows_total} lineage row(s)
            </p>
            <ul className="mt-2 space-y-1 font-mono text-[11px]">
              {Object.entries(qConfidenceSummary.data.by_confidence_class).map(([k, v]) => (
                <li key={k}>
                  {k}: {v}
                </li>
              ))}
            </ul>
            <p className="mt-2 text-[11px] leading-relaxed text-stone-600">
              {qConfidenceSummary.data.confidence_non_ranking_semantics}
            </p>
          </div>
        )}
        <h4 className="mt-6 text-xs font-semibold uppercase tracking-wide text-stone-500">Recent materializations</h4>
        {qLineage.isPending ? (
          <p className="mt-2 text-sm text-stone-600">Loading lineage…</p>
        ) : qLineage.isError ? (
          <p className="mt-2 text-sm text-red-700">{(qLineage.error as Error).message}</p>
        ) : (
          <>
            <p className="mt-2 text-xs text-stone-600">
              Transform v{qLineage.data.transform_runtime_schema_version} · confidence v
              {qLineage.data.confidence_propagation_schema_version} · {qLineage.data.materializations.length} row(s)
            </p>
            <ul className="mt-3 space-y-4">
              {qLineage.data.materializations.map((m) => (
                <li key={m.id} className="rounded-lg border border-stone-100 bg-stone-50/80 p-3 text-sm text-stone-800">
                  <div className="font-mono text-xs text-stone-900">
                    {m.canonical_object_kind} · raw #{m.raw_record_id} · bundle{" "}
                    <span className="text-stone-700">{m.bundle_id}</span>
                  </div>
                  <div className="mt-1 font-mono text-[11px] text-stone-600">
                    entity {m.canonical_entity_id.slice(0, 13)}… · lk {m.logical_key_hash.slice(0, 12)}… · snap{" "}
                    {m.emitted_snapshot_hash.slice(0, 12)}… · {m.engine_build_ref}
                    {m.last_replay_job_id ? (
                      <>
                        {" "}
                        · replay <span className="text-amber-900">{m.last_replay_job_id.slice(0, 13)}…</span>
                      </>
                    ) : null}
                  </div>
                  <p className="mt-1 font-mono text-[11px] text-stone-600">
                    rollup:{" "}
                    {Object.entries(m.confidence_rollup.by_confidence_class || {})
                      .map(([k, v]) => `${k}=${v}`)
                      .join(", ") || "—"}
                  </p>
                  <ul className="mt-2 space-y-1 border-t border-stone-100 pt-2 font-mono text-[11px] text-stone-700">
                    {m.field_lineage.map((fl) => (
                      <li key={`${m.id}-${fl.field_path}`}>
                        <span className="text-stone-900">{fl.field_path}</span> ← {fl.rule_id}{" "}
                        <span className="text-stone-500">({fl.evidence_grade})</span>{" "}
                        <span className="text-amber-800">[{fl.confidence_class}]</span>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Identity continuity (Phase 03 Step 9)</h3>
        <p className="mt-1 text-sm text-stone-600">
          Replay-stable canonical_entity_id (UUIDv5) per provider identity tuple under a mapping bundle. Rows carry
          explicit Phase 04 boundary metadata (human/org linkage authority deferred). Materialize refreshes the anchor
          for the same logical identity.
        </p>
        {qIdentityAnchors.isPending ? (
          <p className="mt-3 text-sm text-stone-600">Loading identity anchors…</p>
        ) : qIdentityAnchors.isError ? (
          <p className="mt-3 text-sm text-red-700">{(qIdentityAnchors.error as Error).message}</p>
        ) : (
          <>
            <p className="mt-3 text-xs text-stone-600">
              Identity runtime v{qIdentityAnchors.data.identity_runtime_schema_version} ·{" "}
              {qIdentityAnchors.data.anchors.length} anchor(s)
            </p>
            <ul className="mt-3 space-y-2 font-mono text-[11px] text-stone-800">
              {qIdentityAnchors.data.anchors.map((a) => (
                <li key={a.canonical_entity_id} className="rounded border border-stone-100 bg-stone-50/80 px-2 py-2">
                  <span className="text-stone-900">{a.canonical_entity_id}</span> · {a.canonical_object_kind} ·{" "}
                  {a.connector} · raw #{a.raw_record_id}{" "}
                  <span className="text-stone-600">
                    · phase04 {String(a.phase04_boundary?.human_identity_resolution ?? "—")}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Replay / rebuild (Phase 03 Step 10)</h3>
        <p className="mt-1 text-sm text-stone-600">
          Pinned-bundle canonical jobs compare the transform oracle to stored materializations, emit C0–C5 receipts,
          and optionally re-materialize. Regeneration across bundles requires a declared compatibility edge in the
          mapping registry.
        </p>
        {qOnt.isSuccess ? (
          <ul className="mt-3 space-y-2 rounded-lg border border-stone-100 bg-stone-50/80 p-3 font-mono text-[11px] text-stone-800">
            {qOnt.data.replay_divergence_taxonomy.map((row) => (
              <li key={row.class}>
                <span className="font-semibold text-stone-900">{row.class}</span> — {row.meaning}
              </li>
            ))}
          </ul>
        ) : null}
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <label className="block text-xs text-stone-600">
            raw_record_ids (comma / space)
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={replayRawIds}
              onChange={(e) => setReplayRawIds(e.target.value)}
              placeholder="e.g. 101 102"
            />
          </label>
          <label className="block text-xs text-stone-600">
            pinned bundle_id
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={replayBundleId}
              onChange={(e) => setReplayBundleId(e.target.value)}
            />
          </label>
          <label className="block text-xs text-stone-600">
            job_kind
            <select
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 text-xs"
              value={replayJobKind}
              onChange={(e) => setReplayJobKind(e.target.value as "rebuild" | "regeneration")}
            >
              <option value="rebuild">rebuild</option>
              <option value="regeneration">regeneration</option>
            </select>
          </label>
          <label className="block text-xs text-stone-600">
            source_bundle_id (regeneration only, optional if same lineage family)
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={replaySourceBundle}
              onChange={(e) => setReplaySourceBundle(e.target.value)}
              placeholder="required when migrating across bundles"
            />
          </label>
          <label className="flex items-center gap-2 text-xs text-stone-600 md:col-span-2">
            <input type="checkbox" checked={replayDryRun} onChange={(e) => setReplayDryRun(e.target.checked)} />
            dry_run (receipts only; no materialize)
          </label>
        </div>
        <button
          type="button"
          className="mt-3 rounded-md bg-stone-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
          disabled={replayRunMut.isPending || !tenantId}
          onClick={() => replayRunMut.mutate()}
        >
          {replayRunMut.isPending ? "Running replay job…" : "Run replay job"}
        </button>
        {replayRunMut.isError ? (
          <p className="mt-2 text-sm text-red-700">{(replayRunMut.error as Error).message}</p>
        ) : null}
        {replayRunMut.isSuccess ? (
          <div className="mt-3 rounded-lg border border-emerald-100 bg-emerald-50/80 p-3 text-xs text-emerald-950">
            Job {replayRunMut.data.job.id.slice(0, 13)}… status <strong>{replayRunMut.data.job.status}</strong> ·
            receipts {replayRunMut.data.receipts.length} · writes{" "}
            {String((replayRunMut.data.job.summary_json as { writes_applied?: number }).writes_applied ?? "—")} applied
          </div>
        ) : null}
        <h4 className="mt-6 text-xs font-semibold uppercase tracking-wide text-stone-500">Recent replay jobs</h4>
        {qReplayJobs.isPending ? (
          <p className="mt-2 text-sm text-stone-600">Loading replay jobs…</p>
        ) : qReplayJobs.isError ? (
          <p className="mt-2 text-sm text-red-700">{(qReplayJobs.error as Error).message}</p>
        ) : (
          <ul className="mt-2 space-y-2 font-mono text-[11px] text-stone-800">
            {qReplayJobs.data.jobs.map((j) => (
              <li key={j.id} className="rounded border border-stone-100 bg-stone-50/80 px-2 py-2">
                <span className="text-stone-900">{j.id}</span> · {j.job_kind} · {j.status}
                {j.dry_run ? " · dry_run" : ""} · bundle {j.pinned_bundle_id} · raws [{j.scope_raw_record_ids.join(", ")}]
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Provenance traceability (Phase 03 Step 11)</h3>
        <p className="mt-1 text-sm text-stone-600">
          Durable forward index (raw → canonical materialization) plus derivation envelope (bundle, engine, sorted rule
          ids). Each successful materialize writes one row; replacing a projection cascades the prior envelope.
        </p>
        {qOnt.isSuccess ? (
          <p className="mt-2 text-xs text-stone-600">
            Evidence shapes documented: {qOnt.data.provenance_evidence_shapes_documented.join(", ")} (stub transform
            emits <strong>1:1</strong> only today).
          </p>
        ) : null}
        <label className="mt-4 block text-xs text-stone-600">
          raw_record_id (forward index lookup)
          <input
            className="mt-1 w-full max-w-xs rounded border border-stone-200 px-2 py-1 font-mono text-xs"
            value={provRawId}
            onChange={(e) => setProvRawId(e.target.value)}
            placeholder="e.g. 101"
          />
        </label>
        {qProvenanceByRaw.isPending ? (
          <p className="mt-3 text-sm text-stone-600">Loading provenance…</p>
        ) : qProvenanceByRaw.isError ? (
          <p className="mt-3 text-sm text-red-700">{(qProvenanceByRaw.error as Error).message}</p>
        ) : qProvenanceByRaw.isSuccess ? (
          <>
            <p className="mt-3 text-xs text-stone-600">
              Provenance runtime v{qProvenanceByRaw.data.provenance_runtime_schema_version} ·{" "}
              {qProvenanceByRaw.data.records.length} projection(s) for raw #{qProvenanceByRaw.data.raw_record_id}
            </p>
            <ul className="mt-2 space-y-2 font-mono text-[11px] text-stone-800">
              {qProvenanceByRaw.data.records.map((r) => (
                <li key={r.id} className="rounded border border-stone-100 bg-stone-50/80 px-2 py-2">
                  mat {r.materialization_id.slice(0, 13)}… · {r.canonical_object_kind} · bundle {r.bundle_id} · lk{" "}
                  {r.logical_key_hash.slice(0, 12)}… · rules {r.rule_ids_involved.length}
                </li>
              ))}
            </ul>
          </>
        ) : (
          <p className="mt-3 text-xs text-stone-500">Enter a positive raw_record_id to load provenance rows.</p>
        )}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Temporal ordering (Phase 03 Step 12)</h3>
        <p className="mt-1 text-sm text-stone-600">
          Deterministic ordering keys on materializations plus an append-only supersession ledger when the same raw
          scope is re-materialized. Rebuild preview sorts raw ids read-only using the same precedence as replay jobs.
        </p>
        <h4 className="mt-4 text-xs font-semibold uppercase tracking-wide text-stone-500">Recent supersessions</h4>
        {qTemporalSupersessions.isPending ? (
          <p className="mt-2 text-sm text-stone-600">Loading supersessions…</p>
        ) : qTemporalSupersessions.isError ? (
          <p className="mt-2 text-sm text-red-700">{(qTemporalSupersessions.error as Error).message}</p>
        ) : (
          <ul className="mt-2 max-h-48 space-y-2 overflow-y-auto font-mono text-[11px] text-stone-800">
            {qTemporalSupersessions.data.items.length === 0 ? (
              <li className="text-stone-600">No supersession rows yet</li>
            ) : (
              qTemporalSupersessions.data.items.map((s) => (
                <li key={s.id} className="rounded border border-stone-100 bg-stone-50/80 px-2 py-2">
                  #{s.id} · bundle {s.bundle_id} · pred {s.predecessor_materialization_id.slice(0, 13)}… → succ{" "}
                  {s.successor_materialization_id
                    ? `${s.successor_materialization_id.slice(0, 13)}…`
                    : "—"}{" "}
                  · raw {s.causing_raw_record_id}
                </li>
              ))
            )}
          </ul>
        )}
        <label className="mt-4 block text-xs text-stone-600">
          raw_record_ids for rebuild-order preview (comma / space)
          <input
            className="mt-1 w-full max-w-md rounded border border-stone-200 px-2 py-1 font-mono text-xs"
            value={temporalPreviewIds}
            onChange={(e) => setTemporalPreviewIds(e.target.value)}
            placeholder="e.g. 101 102"
          />
        </label>
        <button
          type="button"
          className="mt-2 rounded-md bg-stone-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
          disabled={temporalPreviewMut.isPending || !tenantId}
          onClick={() => temporalPreviewMut.mutate()}
        >
          {temporalPreviewMut.isPending ? "Computing preview…" : "Preview rebuild order"}
        </button>
        {temporalPreviewMut.isError ? (
          <p className="mt-2 text-sm text-red-700">{(temporalPreviewMut.error as Error).message}</p>
        ) : null}
        {temporalPreviewMut.isSuccess ? (
          <ul className="mt-3 space-y-1 font-mono text-[11px] text-stone-800">
            {temporalPreviewMut.data.ordered.map((row) => (
              <li key={row.raw_record_id} className="rounded border border-emerald-100 bg-emerald-50/80 px-2 py-1">
                raw {row.raw_record_id} · seq {row.replay_sequence} · {row.occurred_at}
              </li>
            ))}
          </ul>
        ) : null}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Canonical query (Phase 03 Step 13)</h3>
        <p className="mt-1 text-sm text-stone-600">
          Bounded retrieval classes only (point lookup, provenance back/forward trace, timeline slice, logical-key
          neighborhood, replay debug). Semantic search, ranking, and narrative intents are rejected server-side.
        </p>
        {qOnt.isSuccess ? (
          <p className="mt-2 text-xs text-stone-600">
            Classes: {qOnt.data.canonical_query_classes.join(", ")}
          </p>
        ) : null}
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <label className="block text-xs text-stone-600">
            query_class
            <select
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={cqClass}
              onChange={(e) => setCqClass(e.target.value)}
            >
              <option value="point_lookup_materialization">point_lookup_materialization</option>
              <option value="point_lookup_identity_anchor">point_lookup_identity_anchor</option>
              <option value="evidence_backtrace">evidence_backtrace</option>
              <option value="forward_trace">forward_trace</option>
              <option value="timeline_slice">timeline_slice</option>
              <option value="graph_neighborhood">graph_neighborhood</option>
              <option value="replay_debug_snapshot">replay_debug_snapshot</option>
            </select>
          </label>
          <label className="block text-xs text-stone-600">
            intent
            <select
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 text-xs"
              value={cqIntent}
              onChange={(e) => setCqIntent(e.target.value)}
            >
              <option value="evidence_retrieval">evidence_retrieval</option>
              <option value="point_lookup">point_lookup</option>
              <option value="evidence_backtrace">evidence_backtrace</option>
              <option value="forward_trace">forward_trace</option>
              <option value="timeline_retrieval">timeline_retrieval</option>
              <option value="neighborhood_retrieval">neighborhood_retrieval</option>
              <option value="replay_debug">replay_debug</option>
            </select>
          </label>
          <label className="block text-xs text-stone-600 md:col-span-2">
            query_text (optional; blocked if it looks like semantic / ranking / narrative search)
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={cqQueryText}
              onChange={(e) => setCqQueryText(e.target.value)}
              placeholder="leave empty for normal operator retrieval"
            />
          </label>
          <label className="block text-xs text-stone-600 md:col-span-2">
            params (JSON object — examples: materialization_id uuid, raw_record_id int, center_materialization_id)
            <textarea
              className="mt-1 w-full min-h-[4.5rem] rounded border border-stone-200 px-2 py-1 font-mono text-[11px]"
              value={cqParamsJson}
              onChange={(e) => setCqParamsJson(e.target.value)}
            />
          </label>
          <label className="block text-xs text-stone-600">
            limit
            <input
              className="mt-1 w-full max-w-[8rem] rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={cqLimit}
              onChange={(e) => setCqLimit(e.target.value)}
            />
          </label>
        </div>
        <button
          type="button"
          className="mt-3 rounded-md bg-stone-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
          disabled={canonicalQueryMut.isPending || !tenantId}
          onClick={() => canonicalQueryMut.mutate()}
        >
          {canonicalQueryMut.isPending ? "Running query…" : "Run canonical query"}
        </button>
        {canonicalQueryMut.isError ? (
          <p className="mt-2 text-sm text-red-700">{(canonicalQueryMut.error as Error).message}</p>
        ) : null}
        {canonicalQueryMut.isSuccess ? (
          <pre className="mt-3 max-h-64 overflow-auto rounded-lg border border-stone-100 bg-stone-50/80 p-3 font-mono text-[11px] text-stone-800">
            {JSON.stringify(canonicalQueryMut.data, null, 2)}
          </pre>
        ) : null}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Failure + remediation (Phase 03 Step 14)</h3>
        <p className="mt-1 text-sm text-stone-600">
          Durable failure cases (transform errors, replay forbidden divergence, failed jobs) and auditable remediation
          validations. Scoped rebuild delegates to replay jobs; non–dry-run execution requires{" "}
          <span className="font-mono">confirm_execution: true</span>. Phase 02 catastrophic trust states block
          remediation.
        </p>
        {qFailures.isPending ? (
          <p className="mt-3 text-sm text-stone-600">Loading failures…</p>
        ) : qFailures.isError ? (
          <p className="mt-3 text-sm text-red-700">{(qFailures.error as Error).message}</p>
        ) : (
          <>
            <p className="mt-3 text-xs text-stone-600">
              Runtime schema v{qFailures.data.failure_remediation_runtime_schema_version} · active{" "}
              {qFailures.data.active_failure_count} · classes{" "}
              <span className="font-mono">
                {Object.entries(qFailures.data.active_failure_classes)
                  .map(([k, v]) => `${k}:${v}`)
                  .join(", ") || "—"}
              </span>
            </p>
            <ul className="mt-3 max-h-48 space-y-2 overflow-y-auto font-mono text-[11px] text-stone-800">
              {qFailures.data.cases.length === 0 ? (
                <li className="text-stone-600">No active failure cases</li>
              ) : (
                qFailures.data.cases.map((c) => (
                  <li key={c.gap_id} className="rounded border border-stone-100 bg-stone-50/80 px-2 py-2">
                    <span className="text-stone-900">{c.failure_class}</span> · {c.degradation_state} ·{" "}
                    {c.scope_kind} · <span className="text-stone-600">{c.source}</span>
                    <div className="mt-1 break-all text-[10px] text-stone-500">{c.gap_id}</div>
                  </li>
                ))
              )}
            </ul>
            <h4 className="mt-6 text-xs font-semibold uppercase tracking-wide text-stone-500">
              Recent remediation validations
            </h4>
            <ul className="mt-2 max-h-32 space-y-1 overflow-y-auto font-mono text-[10px] text-stone-700">
              {qFailures.data.recent_remediation_validations.length === 0 ? (
                <li className="text-stone-600">None yet</li>
              ) : (
                qFailures.data.recent_remediation_validations.map((v) => (
                  <li key={v.id}>
                    #{v.id} · {v.remediation_class} · <span className="text-amber-900">{v.result_status}</span>
                    {v.created_at ? <span className="text-stone-500"> · {v.created_at}</span> : null}
                  </li>
                ))
              )}
            </ul>
          </>
        )}
        <div className="mt-4 space-y-3 rounded-lg border border-stone-100 bg-stone-50/80 p-4">
          <label className="block text-xs text-stone-600">
            remediation_class
            <select
              className="mt-1 w-full max-w-md rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={remediationClass}
              onChange={(e) => setRemediationClass(e.target.value as "scoped_rebuild" | "ambiguity_triage_ack")}
            >
              <option value="scoped_rebuild">scoped_rebuild</option>
              <option value="ambiguity_triage_ack">ambiguity_triage_ack</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-xs text-stone-600">
            <input type="checkbox" checked={remediationDryRun} onChange={(e) => setRemediationDryRun(e.target.checked)} />
            dry_run
          </label>
          <label className="flex items-center gap-2 text-xs text-stone-600">
            <input
              type="checkbox"
              checked={remediationConfirm}
              onChange={(e) => setRemediationConfirm(e.target.checked)}
            />
            confirm_execution (required when dry_run is false)
          </label>
          <label className="block text-xs text-stone-600">
            failure_case_gap_id (optional)
            <input
              className="mt-1 w-full rounded border border-stone-200 px-2 py-1 font-mono text-[11px]"
              value={remediationGapId}
              onChange={(e) => setRemediationGapId(e.target.value)}
              placeholder="hex gap id from failures list"
            />
          </label>
          <label className="block text-xs text-stone-600">
            payload (JSON) — scoped_rebuild: pinned_bundle_id, raw_record_ids, optional job_kind / source_bundle_id;
            ambiguity_triage_ack: note, optional connector
            <textarea
              className="mt-1 w-full min-h-[5rem] rounded border border-stone-200 px-2 py-1 font-mono text-[11px]"
              value={remediationPayloadJson}
              onChange={(e) => setRemediationPayloadJson(e.target.value)}
            />
          </label>
          <button
            type="button"
            className="rounded-md bg-stone-900 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
            disabled={remediationMut.isPending || !tenantId}
            onClick={() => remediationMut.mutate()}
          >
            {remediationMut.isPending ? "Validating…" : "POST remediation validate"}
          </button>
          {remediationMut.isError ? (
            <p className="text-sm text-red-700">{(remediationMut.error as Error).message}</p>
          ) : null}
          {remediationMut.isSuccess ? (
            <pre className="max-h-48 overflow-auto rounded border border-stone-200 bg-white p-2 font-mono text-[10px] text-stone-800">
              {JSON.stringify(remediationMut.data, null, 2)}
            </pre>
          ) : null}
        </div>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Canonical verification engine (Phase 03 Step 15)</h3>
        <p className="mt-1 text-sm text-stone-600">
          Deterministic invariant sweep (G-P03-01,02,03,04,06,08,09,10 subset) with PASS/FAIL gate payloads. Persisted
          runs support audit replay (G-P03-12). No semantic interpretation—structural substrate checks only.
        </p>
        <div className="mt-4 flex flex-wrap items-end gap-4 rounded-lg border border-stone-100 bg-stone-50/80 p-4">
          <label className="flex items-center gap-2 text-xs text-stone-600">
            <input type="checkbox" checked={verifPersist} onChange={(e) => setVerifPersist(e.target.checked)} />
            persist run to ledger
          </label>
          <label className="block text-xs text-stone-600">
            materialization_sample_limit (1–200)
            <input
              className="mt-1 w-24 rounded border border-stone-200 px-2 py-1 font-mono text-xs"
              value={verifSampleLimit}
              onChange={(e) => setVerifSampleLimit(e.target.value)}
            />
          </label>
          <button
            type="button"
            className="rounded-md bg-stone-900 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
            disabled={verificationRunMut.isPending || !tenantId}
            onClick={() => verificationRunMut.mutate()}
          >
            {verificationRunMut.isPending ? "Running…" : "POST verification/run"}
          </button>
        </div>
        {verificationRunMut.isError ? (
          <p className="mt-2 text-sm text-red-700">{(verificationRunMut.error as Error).message}</p>
        ) : null}
        {verificationRunMut.isSuccess ? (
          <pre className="mt-3 max-h-64 overflow-auto rounded-lg border border-stone-100 bg-stone-50/80 p-3 font-mono text-[11px] text-stone-800">
            {JSON.stringify(verificationRunMut.data, null, 2)}
          </pre>
        ) : null}
        <h4 className="mt-6 text-xs font-semibold uppercase tracking-wide text-stone-500">Recent verification runs</h4>
        {qVerificationRuns.isPending ? (
          <p className="mt-2 text-sm text-stone-600">Loading runs…</p>
        ) : qVerificationRuns.isError ? (
          <p className="mt-2 text-sm text-red-700">{(qVerificationRuns.error as Error).message}</p>
        ) : (
          <ul className="mt-2 space-y-1 font-mono text-[11px] text-stone-800">
            {qVerificationRuns.data.runs.length === 0 ? (
              <li className="text-stone-600">No persisted runs yet</li>
            ) : (
              qVerificationRuns.data.runs.map((r) => (
                <li key={r.id}>
                  #{r.id} · schema v{r.engine_schema_version} ·{" "}
                  <span className={r.passed ? "text-emerald-800" : "text-red-800"}>
                    {r.passed ? "PASS" : "FAIL"}
                  </span>
                  {r.created_at ? <span className="text-stone-500"> · {r.created_at}</span> : null}
                </li>
              ))
            )}
          </ul>
        )}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Ambiguity persistence (Phase 03 Step 7)</h3>
        <p className="mt-1 text-sm text-stone-600">
          Durable ambiguity receipts with lifecycle supersession (no silent loss). Append-only lifecycle events are
          stored for every open and transition. Aggregates support operator visibility by status, class, and connector /
          resource type.
        </p>
        {qAmbiguity.isPending ? (
          <p className="mt-3 text-sm text-stone-600">Loading ambiguity…</p>
        ) : qAmbiguity.isError ? (
          <p className="mt-3 text-sm text-red-700">{(qAmbiguity.error as Error).message}</p>
        ) : (
          <>
            <p className="mt-3 text-xs text-stone-600">
              Runtime schema v{qAmbiguity.data.ambiguity_runtime_schema_version}
            </p>
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border border-stone-100 bg-stone-50/80 p-3">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-stone-500">By status</h4>
                <ul className="mt-2 font-mono text-xs text-stone-800">
                  {Object.entries(qAmbiguity.data.aggregates.by_status).map(([k, v]) => (
                    <li key={k}>
                      {k}: {v}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-lg border border-stone-100 bg-stone-50/80 p-3">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-stone-500">By class</h4>
                <ul className="mt-2 font-mono text-xs text-stone-800">
                  {Object.entries(qAmbiguity.data.aggregates.by_class).map(([k, v]) => (
                    <li key={k}>
                      {k}: {v}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-lg border border-stone-100 bg-stone-50/80 p-3 md:col-span-1">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-stone-500">Connector / type rollup</h4>
                <ul className="mt-2 max-h-40 space-y-1 overflow-y-auto font-mono text-[11px] text-stone-800">
                  {qAmbiguity.data.aggregates.by_connector_resource.length === 0 ? (
                    <li className="text-stone-600">No rows yet</li>
                  ) : (
                    qAmbiguity.data.aggregates.by_connector_resource.map((r) => (
                      <li key={`${r.connector}:${r.resource_type}`}>
                        {r.connector}/{r.resource_type}: open {r.open_count} / total {r.total}
                      </li>
                    ))
                  )}
                </ul>
              </div>
            </div>
            <h4 className="mt-6 text-xs font-semibold uppercase tracking-wide text-stone-500">Open ambiguity</h4>
            <div className="mt-2 flex flex-wrap items-end gap-3 rounded-lg border border-stone-100 bg-stone-50/80 p-4">
              <label className="min-w-[10rem] flex flex-col gap-1 text-xs text-stone-600">
                bundle_id
                <input
                  className="rounded border border-stone-200 bg-white px-2 py-1 font-mono text-sm text-stone-900"
                  value={ambBundleId}
                  onChange={(e) => setAmbBundleId(e.target.value)}
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-stone-600">
                ambiguity_class
                <select
                  className="rounded border border-stone-200 bg-white px-2 py-1 font-mono text-sm text-stone-900"
                  value={ambClass}
                  onChange={(e) => setAmbClass(e.target.value)}
                >
                  <option value="unresolved_mapping">unresolved_mapping</option>
                  <option value="unresolved_identity">unresolved_identity</option>
                  <option value="conflicting_evidence">conflicting_evidence</option>
                  <option value="competing_canonical_candidates">competing_canonical_candidates</option>
                </select>
              </label>
              <label className="min-w-[12rem] flex flex-col gap-1 text-xs text-stone-600">
                scope
                <input
                  className="rounded border border-stone-200 bg-white px-2 py-1 font-mono text-sm text-stone-900"
                  value={ambScope}
                  onChange={(e) => setAmbScope(e.target.value)}
                />
              </label>
              <label className="min-w-[10rem] flex flex-col gap-1 text-xs text-stone-600">
                raw_record_ids
                <input
                  className="rounded border border-stone-200 bg-white px-2 py-1 font-mono text-sm text-stone-900"
                  value={ambRawIds}
                  onChange={(e) => setAmbRawIds(e.target.value)}
                  placeholder="e.g. 1, 2"
                />
              </label>
              <label className="min-w-[8rem] flex flex-col gap-1 text-xs text-stone-600">
                record_handle (opt)
                <input
                  className="rounded border border-stone-200 bg-white px-2 py-1 font-mono text-sm text-stone-900"
                  value={ambHandle}
                  onChange={(e) => setAmbHandle(e.target.value)}
                  placeholder="amb:001"
                />
              </label>
              <button
                type="button"
                className="rounded-md bg-stone-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
                disabled={openAmbiguityMut.isPending}
                onClick={() => openAmbiguityMut.mutate()}
              >
                {openAmbiguityMut.isPending ? "Opening…" : "POST ambiguity"}
              </button>
            </div>
            {openAmbiguityMut.isError ? (
              <p className="mt-2 text-sm text-red-700">{(openAmbiguityMut.error as Error).message}</p>
            ) : null}
            {openAmbiguityMut.isSuccess ? (
              <p className="mt-2 text-sm text-emerald-800">
                Opened ambiguity <span className="font-mono">{openAmbiguityMut.data.record.id}</span> (
                {openAmbiguityMut.data.record.status})
              </p>
            ) : null}
            <h4 className="mt-6 text-xs font-semibold uppercase tracking-wide text-stone-500">Lifecycle transition</h4>
            <div className="mt-2 flex flex-wrap items-end gap-3 rounded-lg border border-stone-100 bg-stone-50/80 p-4">
              <label className="min-w-[16rem] flex flex-col gap-1 text-xs text-stone-600">
                ambiguity_id
                <input
                  className="rounded border border-stone-200 bg-white px-2 py-1 font-mono text-sm text-stone-900"
                  value={ambLifecycleId}
                  onChange={(e) => setAmbLifecycleId(e.target.value)}
                  placeholder="UUID"
                />
              </label>
              <label className="flex flex-col gap-1 text-xs text-stone-600">
                target_status
                <select
                  className="rounded border border-stone-200 bg-white px-2 py-1 font-mono text-sm text-stone-900"
                  value={ambLifecycleTarget}
                  onChange={(e) => setAmbLifecycleTarget(e.target.value)}
                >
                  <option value="superseded_by_evidence">superseded_by_evidence</option>
                  <option value="superseded_by_mapping_version">superseded_by_mapping_version</option>
                  <option value="void">void</option>
                </select>
              </label>
              <label className="min-w-[14rem] flex flex-col gap-1 text-xs text-stone-600">
                note (optional)
                <input
                  className="rounded border border-stone-200 bg-white px-2 py-1 font-mono text-sm text-stone-900"
                  value={ambLifecycleNote}
                  onChange={(e) => setAmbLifecycleNote(e.target.value)}
                />
              </label>
              <button
                type="button"
                className="rounded-md bg-stone-800 px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
                disabled={ambiguityLifecycleMut.isPending}
                onClick={() => ambiguityLifecycleMut.mutate()}
              >
                {ambiguityLifecycleMut.isPending ? "Applying…" : "POST lifecycle"}
              </button>
            </div>
            {ambiguityLifecycleMut.isError ? (
              <p className="mt-2 text-sm text-red-700">{(ambiguityLifecycleMut.error as Error).message}</p>
            ) : null}
            {ambiguityLifecycleMut.isSuccess ? (
              <p className="mt-2 text-sm text-emerald-800">
                Now <span className="font-mono">{ambiguityLifecycleMut.data.record.status}</span>
              </p>
            ) : null}
            <h4 className="mt-6 text-xs font-semibold uppercase tracking-wide text-stone-500">Recent records</h4>
            <ul className="mt-2 space-y-2 font-mono text-[11px] text-stone-800">
              {qAmbiguity.data.records.map((r) => (
                <li key={r.id} className="rounded border border-stone-100 bg-white px-2 py-2">
                  <span className="text-stone-900">{r.id}</span> · {r.ambiguity_class} · {r.status} ·{" "}
                  {r.primary_connector}/{r.primary_resource_type} · raw {r.raw_record_ids.join(",")}
                </li>
              ))}
            </ul>
          </>
        )}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Object kinds ({d.object_kinds.length})</h3>
        <div className="mt-3 overflow-x-auto rounded border border-stone-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-700">
              <tr>
                <th className="px-2 py-2">id</th>
                <th className="px-2 py-2">layer</th>
                <th className="px-2 py-2">structural_role</th>
                <th className="px-2 py-2">structural_examples</th>
                <th className="px-2 py-2">description</th>
              </tr>
            </thead>
            <tbody>
              {d.object_kinds.map((row) => (
                <tr key={row.id} className="border-t border-stone-100">
                  <td className="px-2 py-2 font-mono text-stone-900">{row.id}</td>
                  <td className="px-2 py-2 font-mono text-stone-800">{row.layer}</td>
                  <td className="px-2 py-2 font-mono text-stone-800">{row.structural_role}</td>
                  <td className="px-2 py-2 font-mono text-[11px] text-stone-700">
                    {row.structural_examples.join(", ")}
                  </td>
                  <td className="px-2 py-2 text-stone-700">{row.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Kind taxonomy index ({d.kind_taxonomy.length})</h3>
        <p className="mt-1 text-sm text-stone-600">
          Same boundaries as object kinds—indexed for operator review (provider-shaped structural exemplars only).
        </p>
        <div className="mt-3 overflow-x-auto rounded border border-stone-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-700">
              <tr>
                <th className="px-2 py-2">object_kind_id</th>
                <th className="px-2 py-2">taxonomy_family</th>
                <th className="px-2 py-2">structural_role</th>
                <th className="px-2 py-2">structural_examples</th>
              </tr>
            </thead>
            <tbody>
              {d.kind_taxonomy.map((row) => (
                <tr key={row.object_kind_id} className="border-t border-stone-100">
                  <td className="px-2 py-2 font-mono text-stone-900">{row.object_kind_id}</td>
                  <td className="px-2 py-2 font-mono text-stone-800">{row.taxonomy_family}</td>
                  <td className="px-2 py-2 font-mono text-stone-800">{row.structural_role}</td>
                  <td className="px-2 py-2 font-mono text-[11px] text-stone-700">
                    {row.structural_examples.join(", ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">Oracle manifest (Phase 03 Step 3)</h3>
        <p className="mt-1 text-sm text-stone-600">
          Pre-runtime regression vectors — CI harness consumes the same JSON (`phase-03-oracle-vectors-doctrine.md`).
        </p>
        {qOracle.isPending ? (
          <p className="mt-3 text-sm text-stone-600">Loading oracle manifest…</p>
        ) : qOracle.isError ? (
          <p className="mt-3 text-sm text-red-700">{(qOracle.error as Error).message}</p>
        ) : (
          <>
            <dl className="mt-4 grid gap-2 text-sm text-stone-800 md:grid-cols-2">
              <div>
                <dt className="text-xs uppercase tracking-wide text-stone-500">Manifest schema</dt>
                <dd className="font-mono">{qOracle.data.oracle_manifest_schema_version}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-stone-500">Stub bundle</dt>
                <dd className="break-all font-mono text-xs">{qOracle.data.mapping_bundle_id}</dd>
              </div>
              <div className="md:col-span-2">
                <dt className="text-xs uppercase tracking-wide text-stone-500">Engine build ref</dt>
                <dd className="font-mono text-xs">{qOracle.data.engine_build_ref}</dd>
              </div>
            </dl>
            <div className="mt-4 overflow-x-auto rounded border border-stone-200">
              <table className="min-w-full text-left text-xs">
                <thead className="bg-stone-50 text-stone-700">
                  <tr>
                    <th className="px-2 py-2">fixture_id</th>
                    <th className="px-2 py-2">coverage_tags</th>
                    <th className="px-2 py-2">allowed_divergence</th>
                    <th className="px-2 py-2">raw_snapshot_ref</th>
                  </tr>
                </thead>
                <tbody>
                  {qOracle.data.vectors.map((v) => (
                    <tr key={v.fixture_id} className="border-t border-stone-100">
                      <td className="px-2 py-2 align-top font-mono text-stone-900">{v.fixture_id}</td>
                      <td className="px-2 py-2 align-top font-mono text-[11px] text-stone-800">
                        {v.coverage_tags.join(", ")}
                      </td>
                      <td className="px-2 py-2 align-top font-mono text-stone-800">
                        {v.allowed_divergence_classes.join(", ")}
                      </td>
                      <td className="px-2 py-2 align-top font-mono text-[11px] text-stone-700">
                        {v.raw_snapshot_ref}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>

      <section className="rounded-xl border border-stone-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-stone-900">
          Structural arcs ({d.structural_arcs.length})
        </h3>
        <p className="mt-1 text-sm text-stone-600">
          Allowed projection linkage shapes—evidenced mapping rules bind here in later steps.
        </p>
        <div className="mt-3 overflow-x-auto rounded border border-stone-200">
          <table className="min-w-full text-left text-xs">
            <thead className="bg-stone-50 text-stone-700">
              <tr>
                <th className="px-2 py-2">from_kind</th>
                <th className="px-2 py-2">edge_kind</th>
                <th className="px-2 py-2">to_kind</th>
              </tr>
            </thead>
            <tbody>
              {d.structural_arcs.map((row, i) => (
                <tr key={`${row.from_kind}-${row.edge_kind}-${row.to_kind}-${i}`} className="border-t border-stone-100">
                  <td className="px-2 py-2 font-mono">{row.from_kind}</td>
                  <td className="px-2 py-2 font-mono">{row.edge_kind}</td>
                  <td className="px-2 py-2 font-mono">{row.to_kind}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
