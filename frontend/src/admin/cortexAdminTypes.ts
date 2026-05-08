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
    status: "ok" | "warn" | "unavailable";
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
