export type OperatorStatusBanner = {
  lease_status: string | null;
  fsm_state: string | null;
  phase_cursor: string | null;
  block_reason_code: string | null;
  block_detail: string | null;
  obligation_epoch: number | null;
  target_epoch: number | null;
  pipeline_run_id: string | null;
  last_transition_at: string | null;
  last_transition_trigger: string | null;
  last_transition_from_state: string | null;
  last_transition_to_state: string | null;
};

export type OperatorContinuityFact = {
  key: "ingestion" | "execution" | "graph" | "retrieval" | "synthesis";
  text: string;
  inspect_lens: string | null;
};

export type OperatorRecentEvent = {
  kind: "ingestion_run" | "execution_transition";
  at: string;
  summary: string;
  detail: Record<string, unknown> | null;
};

export type OperatorConnectorRow = {
  connector: string;
  connection_id: string | null;
  connection_status: string | null;
  cortex_routed: boolean;
  checkpoint_last_incremental_at: string | null;
  latest_run: Record<string, unknown> | null;
};

export type OperatorSchedulerState = {
  env_scheduler_enabled: boolean;
  paused_via_redis: boolean;
  operator_mode_label: string | null;
  beat_interval_seconds: number;
  min_gap_seconds: number;
};

export type OperatorOverview = {
  surface_kind: "operator_overview_v1";
  tenant_id: string;
  generated_at_utc: string;
  status_banner: OperatorStatusBanner;
  continuity_facts: OperatorContinuityFact[];
  recent_events: OperatorRecentEvent[];
  connectors: OperatorConnectorRow[];
  phase_receipts: Record<string, unknown>;
  queue_counts: {
    deferral_retry_ready: number;
    synthesis_failed: number;
    tcre_queued: number;
  };
  continuity_snapshot: {
    available: boolean;
    captured_at_utc: string | null;
  };
  scheduler: OperatorSchedulerState;
  runnable_connectors: string[];
  query_groups_used: number;
};

export type OperatorRuntimeLease = {
  status: string | null;
  fsm_state: string | null;
  phase_cursor: string | null;
  obligation_epoch: number | null;
  target_epoch: number | null;
  pipeline_run_id: string | null;
  block_reason_code: string | null;
  block_detail: unknown;
  last_error: string | null;
  canonical_lane_status: string | null;
  execution_lane_status: string | null;
};

export type OperatorRuntimeTransition = {
  from_state: string;
  to_state: string;
  trigger: string;
  gate_result: string | null;
  receipt_hash: string | null;
  pipeline_run_id: string | null;
  created_at: string;
  detail_json: Record<string, unknown>;
};

export type OperatorDualLane = {
  dual_lane_enabled?: boolean;
  canonical_lane?: Record<string, unknown> | null;
  execution_lane?: Record<string, unknown> | null;
};

export type OperatorRuntime = {
  surface_kind: "operator_runtime_v1";
  tenant_id: string;
  generated_at_utc: string;
  lease: OperatorRuntimeLease | null;
  dual_lane: OperatorDualLane;
  progression: Record<string, unknown>;
  transitions: OperatorRuntimeTransition[];
  transition_total: number;
  transition_limit: number;
  transition_offset: number;
  queue_counts: {
    deferral_retry_ready: number;
    synthesis_failed: number;
    tcre_queued: number;
  };
};

export type OperatorActionKind =
  | "run_from_ingestion"
  | "run_from_phase"
  | "restart_execution"
  | "clear_derived"
  | "flush_derived"
  | "flush_all"
  | "rebuild_retrieval_index"
  | "p0_recover";

export type OperatorActionRequest = {
  action: OperatorActionKind;
  start_phase?: string;
  from_phase?: string;
  confirmation?: string;
  force?: boolean;
  break_glass?: boolean;
  scope?: string;
  pipeline_run_id?: string;
  p0_strategy?: "new_run" | "recover_in_place";
};

export type OperatorActionResponse = {
  surface_kind: "operator_action_v1";
  action: OperatorActionKind;
  tenant_id: string;
  result: Record<string, unknown>;
};

export type OperatorGraphSnapshot = {
  surface_kind: "operator_graph_snapshot_v1";
  tenant_id: string;
  available: boolean;
  captured_at_utc: string | null;
  stale: boolean;
  stale_after_minutes: number;
  graph_summary: Record<string, unknown> | null;
  identity_summary: Record<string, unknown> | null;
  component_snapshot: OperatorGraphComponentSnapshot;
  prose_summary: string;
};

export type OperatorGraphComponentSnapshot = {
  available: boolean;
  captured_at_utc: string | null;
  component_count: number | null;
  component_sizes_top_20: number[];
  largest_component_size: number | null;
  job_status: "idle" | "pending" | "running" | "complete" | "failed";
  error_detail: string | null;
};

export type OperatorGraphComponentRefresh = {
  surface_kind: "operator_graph_component_refresh_v1";
  tenant_id: string;
  enqueued: boolean;
  job_status: string;
  hint?: string | null;
};

export type OperatorQueueTab =
  | "synthesis_failed"
  | "tcre_queued"
  | "deferrals"
  | "ingestion_failed";

export type OperatorQueueItem = Record<string, unknown>;

export type OperatorQueues = {
  surface_kind: "operator_queues_v1";
  tenant_id: string;
  tab: OperatorQueueTab;
  items: OperatorQueueItem[];
  total: number;
  limit: number;
  offset: number;
  counts: {
    synthesis_failed: number;
    tcre_queued: number;
    deferrals: number;
    ingestion_failed: number;
  };
  generated_at_utc: string;
};

export type OperatorEdgeProvenance = {
  surface_kind: "operator_edge_provenance_v1";
  tenant_id: string;
  query: Record<string, unknown>;
  edges: Record<string, unknown>[];
  total: number;
};

export type OperatorIslandsList = {
  surface_kind: "operator_islands_list_v1";
  tenant_id: string;
  island_count: number;
  islands: Record<string, unknown>[];
};

export type OperatorRetrievalEpochs = {
  surface_kind: "operator_retrieval_epochs_v1";
  tenant_id: string;
  epochs: Record<string, unknown>[];
  limit: number;
  generated_at_utc: string;
};

export type OperatorRetrievalEntries = {
  surface_kind: "operator_retrieval_entries_v1";
  tenant_id: string;
  query: Record<string, unknown>;
  items: Record<string, unknown>[];
  total: number;
  limit: number;
  offset: number;
  generated_at_utc: string;
};

export type OperatorRetrievalLineage = {
  surface_kind: "operator_retrieval_lineage_v1";
  tenant_id: string;
  artifact_kind: string;
  artifact_ref: string;
  chain: Record<string, unknown>;
  generated_at_utc: string;
};

export type OperatorSynthesisJobs = {
  surface_kind: "operator_synthesis_jobs_v1";
  tenant_id: string;
  query: Record<string, unknown>;
  jobs: Record<string, unknown>[];
  total: number;
  limit: number;
  offset: number;
  recent_artifacts: Record<string, unknown>[];
  generated_at_utc: string;
};

export type OperatorExecutionThread = {
  surface_kind: "operator_execution_thread_v1";
  tenant_id: string;
  query: Record<string, unknown>;
  walk_lineage: Record<string, unknown>[];
  tcre_jobs: Record<string, unknown>[];
  index_entries: Record<string, unknown>[];
  generated_at_utc: string;
};
