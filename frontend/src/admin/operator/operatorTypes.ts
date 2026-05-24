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
