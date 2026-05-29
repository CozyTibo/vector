/** Cortex admin types — ingestion + canon surfaces. */

export type CortexLaneSchedulerStatus = {
  runtime_model?: "orchestrator";
  enabled: boolean;
  interval_seconds: number;
  orchestrator_interval_seconds?: number;
  tenant_needs_work?: boolean;
  lane_stale?: boolean;
  last_tick?: {
    tick_id: string;
    started_at: string;
    completed_at: string | null;
    outcome: string;
  } | null;
  last_orchestrator_run?: {
    id: string;
    started_at: string;
    completed_at: string | null;
    outcome: string;
    passes_planned?: number;
    passes_processed?: number;
    error_summary?: string | null;
  } | null;
};

export type CanonReadiness = {
  tenant_id: string;
  company_name: string;
  mapper_version: number;
  raw_inventory: {
    resource_type_counts: Record<string, number>;
    total_live_rows: number;
    max_live_raw_id: number;
    lineage_identity_count: number;
  };
  materialization_lag: {
    scope_key: string;
    last_raw_id: number;
    max_live_raw_id: number;
    pending_raw_rows_estimate: number;
    mapper_version: number;
    expected_mapper_version: number;
    mapper_version_current: boolean;
  };
  resource_type_classification: {
    mapped: string[];
    skipped: string[];
    deferred: string[];
    unknown: string[];
  };
  dirty_queue_depth: number;
  latest_pass_run: Record<string, unknown> | null;
  scheduler: CortexLaneSchedulerStatus;
};

export type CanonPassRunItem = {
  id: string;
  status: string;
  source_trigger: string;
  started_at: string;
  finished_at: string | null;
  error_summary: string | null;
  stats: Record<string, unknown> | null;
};

export type CanonEntityItem = {
  id: string;
  entity_type: string;
  entity_key: string;
  display_label: string;
  connector: string;
  connection_id: string;
  materialized_at: string;
  mapper_version: number;
  author_entity_id: string | null;
  conversation_entity_id: string | null;
  parent_message_entity_id: string | null;
  repository_entity_id: string | null;
  assignee_entity_id: string | null;
  parent_document_entity_id: string | null;
  work_item_entity_id: string | null;
};

export type CanonCoverageResourceType = {
  resource_type: string;
  disposition: string;
  entity_type: string | null;
  raw_row_count: number;
  canon_entity_count: number;
  gap: string | null;
};

export type CanonCoverageConnector = {
  connector: string;
  raw_row_count: number;
  canon_entity_count: number;
  unmaterialized_raw_rows: number;
  unknown_type_raw_rows: number;
  resource_types: CanonCoverageResourceType[];
};

export type CanonCoverage = {
  tenant_id: string;
  registry_row_count: number;
  connectors: CanonCoverageConnector[];
};

export type CanonEntityStatRow = {
  connector: string;
  entity_type: string;
  row_count: number;
  newest_materialized_at: string | null;
  oldest_materialized_at: string | null;
};

export type CanonEntityStats = {
  tenant_id: string;
  resources: CanonEntityStatRow[];
};

export type CanonEntityList = {
  items: CanonEntityItem[];
  total_count: number;
  offset: number;
  limit: number;
};

export type CanonEntityDetail = CanonEntityItem & {
  attrs_json: Record<string, unknown>;
  sources: Array<{
    raw_id: number;
    connector: string;
    resource_type: string;
    external_id: string;
    source_identity_key: string;
    source_revision_key: string;
    observed_at: string;
    is_latest: boolean;
    payload_preview?: Record<string, unknown>;
  }>;
};

export type IdentityLatestPassRun = {
  id: string;
  status: string;
  source_trigger: string;
  started_at: string;
  finished_at: string | null;
  error_summary: string | null;
  stats: Record<string, unknown> | null;
};

export type IdentityReadiness = {
  tenant_id: string;
  actor_count: number;
  identity_count: number;
  inactive_human_count?: number;
  linked_account_count: number;
  unresolved_actor_count: number;
  dirty_queue_depth: number;
  latest_pass_run: IdentityLatestPassRun | null;
  scheduler: CortexLaneSchedulerStatus;
};

export type IdentityPassRunItem = {
  id: string;
  status: string;
  source_trigger: string;
  started_at: string;
  finished_at: string | null;
  error_summary: string | null;
  stats: Record<string, unknown> | null;
};

export type IdentityListItem = {
  id: string;
  kind: string;
  display_name: string;
  primary_email: string | null;
  resolver_version: number;
  resolved_at: string;
  account_count: number;
  connectors: string[];
  avatar_url?: string | null;
};

export type IdentityList = {
  items: IdentityListItem[];
  total_count: number;
  offset: number;
  limit: number;
};

export type IdentityDetail = {
  id: string;
  kind: string;
  display_name: string;
  primary_email: string | null;
  resolver_version: number;
  resolved_at: string;
  accounts: Array<{
    identity_account_id: string;
    canon_entity_id: string;
    connector: string;
    connection_id: string;
    display_label: string;
    entity_key: string;
    link_tier: string;
    link_rule: string;
    confidence: string;
    evidence_json: Record<string, unknown>;
    linked_at: string;
  }>;
};

export type IdentityUnresolvedActors = {
  items: Array<{
    canon_entity_id: string;
    connector: string;
    display_label: string;
    entity_key: string;
    materialized_at: string;
  }>;
  total_count: number;
  offset: number;
  limit: number;
};

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

export type CortexCheckpointStreamSummary = {
  stream_key: string;
  cursor_owner?: string | null;
  next_cursor?: string | null;
  backfill_complete?: boolean;
  introduced_at?: string | null;
  last_ok_at?: string | null;
  pages_fetched_last_run?: number | null;
  rows_seen_last_run?: number | null;
  connector_exhaust_depth?: string | null;
};

export type CortexConnectorRawResourceStat = {
  resource_type: string;
  row_count: number;
  oldest_fetched_at: string | null;
  newest_fetched_at: string | null;
};

export type CortexIngestionConnectorRow = {
  connector: string;
  connection_id: string | null;
  connection_status: string | null;
  cortex_routed: boolean;
  checkpoint_last_incremental_at: string | null;
  checkpoint_exhaust_depth?: string | null;
  checkpoint_streams?: CortexCheckpointStreamSummary[];
  raw_resource_stats?: CortexConnectorRawResourceStat[];
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

export type CortexSchedulerBeatConnector = {
  connector: string;
  enqueued: boolean;
  run_id: string | null;
  status: string;
  records_written: number | null;
  resource_breakdown: Array<{ resource_type: string; count: number }>;
  error_summary: string | null;
  started_at: string | null;
  finished_at: string | null;
};

export type CortexSchedulerBeatItem = {
  tick_id: string;
  started_at: string;
  completed_at: string | null;
  outcome: string;
  beat_interval_seconds: number;
  skip_reason: string | null;
  global_enqueued_count: number;
  global_candidate_count: number;
  tenant_enqueued_count: number;
  connectors: CortexSchedulerBeatConnector[];
};

export type CortexSchedulerBeats = {
  tenant_id: string;
  items: CortexSchedulerBeatItem[];
  limit: number;
};

export type CortexRawIngestionRecord = {
  id: number;
  run_id: string;
  resource_type: string;
  external_id: string;
  api_endpoint: string;
  query_params: Record<string, unknown>;
  payload_body: Record<string, unknown>;
  http_status: number;
  fetched_at: string;
  idempotency_key: string | null;
  source_identity_key: string | null;
  source_revision_key: string | null;
  replay_job_id: string | null;
  replay_version: number | null;
};

export type CortexRawIngestionRecords = {
  tenant_id: string;
  connector: CortexConnectorId;
  items: CortexRawIngestionRecord[];
  total_count: number;
  offset: number;
  limit: number;
  truncated: boolean;
};

export type CortexRawIngestionStats = {
  tenant_id: string;
  resources: Array<{
    connector: string;
    resource_type: string;
    row_count: number;
    oldest_fetched_at: string | null;
    newest_fetched_at: string | null;
  }>;
  connector_rollups?: Array<{
    connector: string;
    row_count: number;
    resource_types: Array<{ resource_type: string; row_count: number }>;
  }>;
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

export type GraphLaneScheduler = {
  runtime_model?: string;
  enabled?: boolean;
  interval_seconds?: number;
  orchestrator_interval_seconds?: number;
  tenant_needs_work?: boolean;
  lane_stale?: boolean;
  scheduled_skip?: boolean;
  last_tick?: Record<string, unknown> | null;
  last_orchestrator_run?: Record<string, unknown> | null;
};

export type GraphReadiness = {
  tenant_id: string;
  extractor_version: number;
  extractor_version_code: number;
  dirty_queue_pending: number;
  dirty_queue_extract_pending: number;
  dirty_queue_enrich_pending: number;
  dirty_queue_by_reason: Record<string, number>;
  active_relationship_count: number;
  unresolved_reference_count: number;
  scoped_entity_count: number;
  unlinked_scoped_entity_count: number;
  canon_backlog: boolean;
  graph_caught_up: boolean;
  latest_pass_run: {
    id: string;
    status: string;
    source_trigger: string;
    started_at: string;
    finished_at: string | null;
    stats: Record<string, number>;
    error_summary: string | null;
  } | null;
  scheduler: GraphLaneScheduler;
};

export type GraphRelationshipListItem = {
  id: string;
  relationship_kind: string;
  relationship_kind_label: string;
  confidence: string;
  extractor_rule: string;
  observed_at: string;
  from: { entity_id: string; display_label?: string; entity_type?: string; connector?: string };
  to: { entity_id: string; display_label?: string; entity_type?: string; connector?: string };
  from_identity: { identity_id: string; display_name: string } | null;
  to_identity: { identity_id: string; display_name: string } | null;
  evidence_snapshot: Record<string, unknown>;
  source_raw_id: number | null;
};

export type GraphRelationshipList = {
  items: GraphRelationshipListItem[];
  total_count: number;
  offset: number;
  limit: number;
};

export type GraphStats = {
  tenant_id: string;
  by_kind: Array<{ relationship_kind: string; relationship_kind_label: string; count: number }>;
};

export type GraphPassRunItem = {
  id: string;
  source_trigger: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  stats: Record<string, number>;
  error_summary: string | null;
};

export type GraphPassRuns = {
  items: GraphPassRunItem[];
  total_count: number;
  offset: number;
  limit: number;
};

export type GraphUnresolvedItem = {
  id: string;
  reference_kind: string;
  reference_text: string;
  extractor_rule: string;
  created_at: string;
  source_entity: { entity_id: string; display_label: string } | null;
  evidence_snapshot: Record<string, unknown>;
};

export type GraphUnresolvedList = {
  items: GraphUnresolvedItem[];
  total_count: number;
  offset: number;
  limit: number;
};

export type GraphEntityLinks = {
  outbound: GraphRelationshipListItem[];
  inbound: GraphRelationshipListItem[];
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
