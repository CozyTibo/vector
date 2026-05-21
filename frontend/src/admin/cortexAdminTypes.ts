export type CortexConnectorId = "calls" | "github" | "linear" | "notion" | "slack";

export type CortexOverview = {
  tenant_id: string;
  company_name: string;
  global_scheduler: {
    env_scheduler_enabled: boolean;
    beat_interval_seconds: number;
    min_gap_seconds: number;
    verify_after_sync: boolean;
    redis_url_configured: boolean;
    paused_via_redis: boolean;
    operator_mode_label: string;
  };
  worker_telemetry: {
    status: "ok" | "no_workers" | "unavailable" | "error";
    worker_count: number;
    live_queue_workers: number;
    replay_queue_workers: number;
    worker_names: string[];
    detail: string | null;
  };
  duplicate_prevention: {
    status: "ok" | "warn" | "unavailable" | "deferred";
    ratio_percent: number | null;
    live_rows_examined: number;
    duplicate_groups: number;
    duplicate_rows_excess: number;
    detail: string | null;
  };
  digest: {
    objective: string;
    bottleneck_hint: string;
    confidence_note: string;
    recommended_actions: string[];
  };
  connectors: Array<{
    connector: CortexConnectorId;
    connection_id: string | null;
    connection_status: string | null;
    cortex_routed: boolean;
    queue_lane_live: string;
    queue_lane_replay: string;
    checkpoint_last_incremental_at: string | null;
    ingested_row_count: number;
    latest_run: null | {
      run_id: string;
      status: string;
      replay_mode: boolean;
      sync_mode: string;
      source_trigger: string;
      started_at: string;
      finished_at: string | null;
      error_summary: string | null;
      raw_rows_written: number | null;
    };
  }>;
};

export type CortexVerification = {
  tenant_id: string;
  passed: boolean;
  runs_examined: number;
  run_reports: Array<{ run_id?: string; passed: boolean; checks?: unknown[] }>;
  checkpoint_report: { passed: boolean; checks?: unknown[] };
  raw_memory_critical_integrity?: { passed?: boolean; state?: string; checks?: unknown[] };
  raw_memory_operational_trust_proof?: { passed?: boolean; state?: string; checks?: unknown[] };
  raw_memory_control_plane?: { passed?: boolean; state?: string; checks?: unknown[] };
  raw_memory_phase_closure?: {
    passed?: boolean;
    phase_status?: string;
    checks?: unknown[];
    gate_results?: Record<string, unknown>;
    summary?: Record<string, unknown>;
  };
  exhaust_depth?: {
    warnings?: Array<{ code: string; severity: string; detail: string }>;
    ping_like_ratio?: number;
    resource_type_counts?: Record<string, number>;
    gate_passed?: boolean;
    gate_checks?: Array<{ id: string; passed: boolean; detail?: unknown }>;
    reconstruction_drill?: {
      passed?: boolean;
      checklist?: Array<{ id: string; passed: boolean; detail?: unknown }>;
    };
    live_idempotency_status?: {
      live_rows_examined?: number;
      source_identity_key_present?: boolean;
      source_revision_key_present?: boolean;
      run_scoped_live_identity_forbidden?: boolean;
    };
  };
};

export type CortexMemoryPhaseClosure = {
  tenant_id: string;
  passed: boolean;
  phase_status: "open" | "closed" | string;
  checks: Array<{ id: string; passed: boolean; detail?: unknown }>;
  gate_results: Record<
    string,
    { decision: "pass" | "warn_only" | "soft_fail" | "hard_fail" | string; reason: string; passed: boolean }
  >;
  summary: {
    hard_fail_count: number;
    soft_fail_count: number;
    warn_only_count: number;
    hard_fails: string[];
    required_scope_soft_fails: string[];
    warn_only: string[];
    warnings_ack_required: string[];
    blocking_flags_active: string[];
  };
};

export type CortexRecentRuns = {
  items: Array<{
    run_id: string;
    connector: CortexConnectorId;
    status: string;
    source_trigger: string;
    replay_mode: boolean;
    started_at: string;
    finished_at: string | null;
    error_summary: string | null;
    raw_rows_written: number | null;
    connection_id: string | null;
    sync_mode: string | null;
    replay_job_id: string | null;
    replay_version: number | null;
  }>;
};

export type CortexExhaustCoverage = {
  tenant_id: string;
  connector_exhaust_matrix_doc: string;
  ingestion_depth_model_doc: string;
  organizational_exhaust_definition_doc: string;
  real_ingestion_definition_doc: string;
  connector_expansion_roadmap_doc: string;
  connectors: Array<{
    connector: CortexConnectorId;
    maturity_level: number;
    maturity_level_title: string;
    historical_backfill_summary: string;
    replay_compatibility_summary: string;
    canonicalization_summary: string;
    missing_resource_types: string[];
    resources: Array<{
      resource_type: string;
      coverage: string;
      historical: string;
      replay: string;
      canonicalization: string;
      status: string;
      notes?: string | null;
    }>;
  }>;
};

export type CortexRawStats = {
  tenant_id: string;
  resources: Array<{
    connector: string;
    resource_type: string;
    row_count: number;
    oldest_fetched_at: string | null;
    newest_fetched_at: string | null;
  }>;
  connector_rollups: Array<{
    connector: string;
    row_count: number;
    oldest_fetched_at: string | null;
    newest_fetched_at: string | null;
    resource_types: Array<{ resource_type: string; row_count: number }>;
  }>;
};

export type CortexRawRecords = {
  tenant_id: string;
  connector: string;
  items: Array<{
    id: number;
    run_id: string;
    resource_type: string;
    external_id: string;
    api_endpoint: string;
    query_params: Record<string, unknown>;
    payload_body: Record<string, unknown>;
    http_status: number;
    fetched_at: string;
    idempotency_key?: string | null;
    source_identity_key?: string | null;
    source_revision_key?: string | null;
    replay_job_id?: string | null;
    replay_version?: number | null;
  }>;
  total_count: number;
  offset: number;
  limit: number;
  truncated: boolean;
};

export type CortexMemoryControlPlane = {
  tenant_id: string;
  health_overview: {
    trust_state: string;
    severity: string;
    replay_state: string | null;
    reconstruction_state: string | null;
    provenance_state: string | null;
    continuity_gap_count: number;
    active_failure_count: number;
    active_failure_classes: Record<string, number>;
    latest_recovery_validation: null | {
      status: string;
      created_at: string;
      apply_repairs: boolean;
    };
    blocking: Record<string, boolean>;
    state_reason_codes: string[];
    /** Phase 02 Step 14 — canonical proof-quality primary from verification truth */
    proof_quality_primary?: string | null;
    /** fresh | stale — operator-visible verification snapshot freshness */
    verification_freshness?: string | null;
    /** Phase 02 Step 15 — lineage/revision pointer integrity sweep */
    critical_integrity_passed?: boolean | null;
    critical_integrity_state?: string | null;
    /** Phase 02 Step 16 — composite operational trust proof scenarios */
    operational_trust_passed?: boolean | null;
    operational_trust_state?: string | null;
  };
  inspectors: {
    replay_inspector: {
      jobs_count: number;
      active_jobs: number;
      failed_jobs: number;
      latest_jobs: Array<{
        run_id: string;
        connector: string;
        status: string;
        replay_job_id: string | null;
        replay_version: number | null;
        started_at: string | null;
        finished_at: string | null;
      }>;
    };
    provenance_explorer: { lineage_rows: number; active_failure_classes: Record<string, number> };
    temporal_reconstruction_inspector: { revision_rows: number; continuity_gaps: Array<Record<string, unknown>> };
    corruption_continuity_inspector: {
      active_failure_count: number;
      active_failures: Array<{
        gap_id: string;
        failure_class: string;
        gap_type: string;
        trust_state_impact: string;
        recoverability_class: string;
        recovery_status: string;
      }>;
    };
    archive_storage_inspector: { tier_counts: Record<string, number> };
  };
  verification_checklist: {
    passed: boolean;
    items: Array<{ id: string; passed: boolean; detail?: unknown }>;
  };
  /** Phase 02 Step 12 — canonical verification snapshot (when present from verification payload). */
  verification_truth?: Record<string, unknown> | null;
  phase_closure?: CortexMemoryPhaseClosure;
  actions: Array<{
    id: string;
    method: string;
    path: string;
    safe: boolean;
    scope: string;
    expected_impact: string;
  }>;
  warnings: {
    must_not_assume: string[];
    active_failure_sync: Record<string, unknown>;
  };
};

export type CortexStabilizationProofReport = {
  tenant_id: string;
  stabilization_proof_schema_version: number;
  overall_passed: boolean;
  hard_fail_passed: boolean;
  warn_only_all_passed: boolean;
  proof_checklist: Array<{ id: string; passed: boolean; severity?: string; detail?: unknown }>;
  substrate_scale: Record<string, unknown>;
  replay_economics: Record<string, unknown>;
  verification_continuity: Record<string, unknown>;
  ambiguity_pressure: Record<string, unknown>;
  mapping_governance: Record<string, unknown>;
  reconstruction_slice: Record<string, unknown>;
  doctrine_anchors: string[];
  warnings: { must_not_assume: string[] };
  persisted_run_id: number | null;
};

export type CortexStabilizationProofRunsList = {
  stabilization_proof_schema_version: number;
  tenant_id: string;
  runs: Array<{
    id: number;
    tenant_id: string;
    proof_schema_version: number;
    passed: boolean;
    probes_json: Record<string, unknown>;
    created_at: string;
  }>;
};

export type CortexCanonicalCertificationClosureGate = {
  id: string;
  name: string;
  passed: boolean;
  severity: string;
  detail?: Record<string, unknown>;
};

export type CortexCanonicalCertificationPack = {
  certification_pack_schema_version: number;
  tenant_id: string;
  built_at_clock: string;
  verification_matrix_excerpt: Record<string, unknown>;
  stabilization_proof_excerpt: Record<string, unknown>;
  control_plane_excerpt: Record<string, unknown>;
  replay_jobs_excerpt: Record<string, unknown>;
  ambiguity_excerpt: Record<string, unknown>;
  mapping_registry_excerpt: Record<string, unknown>;
  lineage_operator_sample_excerpt: Record<string, unknown>;
  doctrine_notes: Record<string, unknown>;
  closure_gate_matrix: CortexCanonicalCertificationClosureGate[];
  certification_pack_contract: { passed: boolean; errors?: string[] };
};

export type CortexCanonicalCertificationArchiveResult = {
  persisted: boolean;
  passed: boolean;
  archive_id: number | null;
  certification_pack_schema_version: number;
  tenant_id: string;
  pack: Record<string, unknown>;
};

export type CortexCanonicalCertificationArchivesList = {
  certification_pack_schema_version: number;
  tenant_id: string;
  archives: Array<{
    id: number;
    tenant_id: string;
    certification_pack_schema_version: number;
    passed: boolean;
    created_at: string;
  }>;
};

export type CortexOrgIdentityCertificationClosureGate = {
  id: string;
  name: string;
  passed: boolean;
  severity: string;
  detail?: Record<string, unknown>;
};

export type CortexOrgIdentityCertificationPack = {
  org_certification_pack_schema_version: number;
  tenant_id: string;
  built_at_clock: string;
  canonical_verification_excerpt: Record<string, unknown>;
  phase04_gate_excerpt: Record<string, unknown>;
  identity_control_plane_excerpt: Record<string, unknown>;
  readiness_economics_excerpt: Record<string, unknown>;
  org_verification_last_excerpt: Record<string, unknown>;
  doctrine_notes: Record<string, unknown>;
  closure_gate_matrix: CortexOrgIdentityCertificationClosureGate[];
  org_identity_certification_pack_contract: { passed: boolean; errors?: string[] };
};

export type CortexOrgIdentityCertificationArchiveResult = {
  persisted: boolean;
  passed: boolean;
  archive_id: number | null;
  org_certification_pack_schema_version: number;
  tenant_id: string;
  pack: Record<string, unknown>;
};

export type CortexOrgIdentityCertificationArchivesList = {
  org_certification_pack_schema_version: number;
  tenant_id: string;
  archives: Array<{
    id: number;
    tenant_id: string;
    org_certification_pack_schema_version: number;
    passed: boolean;
    created_at: string;
  }>;
};

/** ``GET …/cortex/identity/handles`` — org_handle_list_row_v1 rows. */
export type CortexIdentityHandleListRow = {
  handle_id: string;
  kind: string;
  created_from: string;
  persona_count: number;
  active_links: number;
  temporal_state: string;
  merge_state: string;
  last_replay: string;
  confidence_posture: string;
  candidate_persona_touch_count?: number;
  candidate_any_touch_count?: number;
  open_ambiguity_touch_count?: number;
  entity_kind_rule?: string | null;
};

export type CortexIdentityHandlesExplorerResponse = {
  identity_operator_console_schema_version: number;
  tenant_id: string;
  list_contract: string;
  rows: CortexIdentityHandleListRow[];
};

/** ``GET …/cortex/identity/handles/{id}`` — same shape as org entity. */
export type CortexOrgEntityItem = {
  org_entity_runtime_schema_version: number;
  id: string;
  tenant_id: string;
  entity_kind: string;
  lifecycle_state: string;
  superseded_by_id: string | null;
  identity_key_fingerprint: string;
  metadata_json: Record<string, unknown>;
  engine_build_ref: string;
  tombstoned_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

/** Subset of backend `health_overview` used by the control-plane admin UI. */
export type CortexCanonicalControlPlaneHealthOverview = {
  materialization_row_count: number;
  field_lineage_row_count: number;
  provenance_record_row_count?: number;
  temporal_supersession_row_count?: number;
  active_canonical_failure_count: number;
  active_canonical_failure_classes?: Record<string, number>;
  replay_jobs_in_window: number;
  replay_job_status_counts?: Record<string, number>;
  replay_divergence_class_totals_recent_completed?: Record<string, number>;
  replay_dependency_edge_count?: number;
  replay_dependency_cycle_detected?: boolean;
  orphan_dependency_ref_count?: number;
  mapping_bundle_inventory_count: number;
  mapping_pin_row_count: number;
  ambiguity_by_status?: Record<string, unknown>;
  ambiguity_open_count: number;
  ambiguity_explosion_warn?: boolean;
  verification_freshness_label: string;
  last_verification_passed?: boolean | null;
  latest_remediation_validation?: Record<string, unknown> | null;
};

/** Canonical verification ledger row (GET …/verification/runs). */
export type CortexCanonicalVerificationGateResult = {
  id: string;
  name: string;
  passed: boolean;
  severity: string;
  detail: Record<string, unknown>;
};

export type CortexCanonicalVerificationRunRow = {
  id: number;
  tenant_id: string;
  engine_schema_version: number;
  passed: boolean;
  gates: CortexCanonicalVerificationGateResult[];
  evidence: Record<string, unknown>;
  created_at: string | null;
};

export type CortexCanonicalVerificationRunsList = {
  canonical_verification_engine_schema_version: number;
  tenant_id: string;
  runs: CortexCanonicalVerificationRunRow[];
};

export type CortexCanonicalControlPlane = {
  tenant_id: string;
  canonical_control_plane_schema_version: number;
  health_overview: CortexCanonicalControlPlaneHealthOverview;
  inspectors: Record<string, unknown>;
  verification_checklist: {
    passed: boolean;
    items: Array<{ id: string; passed: boolean; detail?: unknown }>;
  };
  verification_truth: Record<string, unknown> | null;
  logical_information_architecture: Record<
    string,
    { doctrine_surface?: string; summary?: string; admin_route_hints?: string[] }
  >;
  actions: Array<{
    id: string;
    method: string;
    path: string;
    safe: boolean;
    scope: string;
    expected_impact: string;
  }>;
  warnings: { must_not_assume: string[]; canonical_failure_sync: Record<string, unknown> };
};

/** POST …/transform/materialize-backlog-async */
export type CortexCanonicalMaterializeBacklogAsyncResponse = {
  enqueued: boolean;
  celery_task_id: string;
  tenant_id: string;
  bundle_id_used: string;
  scope_connector?: string | null;
  scope_resource_type?: string | null;
  batch_limit?: number | null;
};

export function titleConnector(connector: string): string {
  if (connector === "github") return "GitHub";
  if (connector === "calls") return "Calls";
  return connector.charAt(0).toUpperCase() + connector.slice(1);
}

export function formatRelativeAge(isoTs: string | null | undefined): string {
  if (!isoTs) return "n/a";
  const ms = Date.now() - new Date(isoTs).getTime();
  if (!Number.isFinite(ms) || ms < 0) return "just now";
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  return `${day}d ago`;
}
