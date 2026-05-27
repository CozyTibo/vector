/** Cortex admin types — ingestion-only surface. */

export type CortexConnectorId = "calls" | "github" | "linear" | "notion" | "slack";

export type CortexIngestionRunSummary = {
  run_id: string;
  status: string;
  replay_mode: boolean;
  sync_mode: string | null;
  source_trigger: string;
  started_at: string;
  finished_at: string | null;
  error_summary: string | null;
  raw_rows_written: number | null;
};

export type CortexIngestionConnectorRow = {
  connector: string;
  connection_id: string | null;
  connection_status: string | null;
  cortex_routed: boolean;
  checkpoint_last_incremental_at: string | null;
  ingested_row_count: number;
  latest_run: CortexIngestionRunSummary | null;
};

export type CortexIngestionOverview = {
  tenant_id: string;
  company_name: string;
  global_scheduler: {
    env_scheduler_enabled: boolean;
    beat_interval_seconds: number;
    min_gap_seconds: number;
    verify_after_sync: boolean;
    paused_via_redis: boolean;
    operator_mode_label: string;
  };
  worker_telemetry: Record<string, unknown>;
  duplicate_prevention: Record<string, unknown>;
  digest: {
    bottleneck: string;
    routed_any: boolean;
    has_active_connection: boolean;
  };
  connectors: CortexIngestionConnectorRow[];
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
  total_count: number;
  offset: number;
  limit: number;
};

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
