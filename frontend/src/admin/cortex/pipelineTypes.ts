/** Operator pipeline dialect (admin revamp Wave 0–1). */

export type OperatorPhase =
  | "ingestion"
  | "canonical"
  | "identity"
  | "graph"
  | "reconstruction"
  | "retrieval"
  | "synthesis";

export type PhaseStatus = "healthy" | "running" | "waiting" | "blocked" | "degraded";

export type PhaseOverview = {
  phase: OperatorPhase;
  label: string;
  status: PhaseStatus;
  statusLabel: string;
  objectCountLabel: string | null;
  route: string;
};

export type ContinuitySignal = {
  key: string;
  label: string;
  value: string;
  severity?: "ok" | "warn" | "bad" | null;
};

export type ContinuityStatus = {
  state: "AUTONOMOUS" | "DEGRADED" | "WEDGE_DEPENDENT" | "STALLED" | "BROKEN";
  state_label?: string;
  execution_lane: "HEALTHY" | "DEGRADED" | "BLOCKED" | "WAITING" | "UNKNOWN";
  canonical_lane: "HEALTHY" | "DEGRADED" | "BLOCKED" | "WAITING" | "UNKNOWN";
  last_full_chain_at?: string | null;
  last_full_chain_ago?: string | null;
  last_retrieval_epoch?: string | null;
  last_retrieval_epoch_at?: string | null;
  last_retrieval_epoch_ago?: string | null;
  last_synthesis_at?: string | null;
  last_synthesis_ago?: string | null;
  topology_wait?: boolean;
  aa_continuity_soak?: {
    active?: boolean;
    hours_elapsed?: number | null;
    hours_required?: number;
    detail?: string | null;
  };
  progression_class?: string | null;
};

export type AttentionItem = {
  priority: "P0" | "P1" | "P2";
  title: string;
  impact: string;
  action: string;
  phase?: string | null;
};

export type PipelineOverviewPhase = {
  phase: OperatorPhase;
  status: PhaseStatus;
  status_label: string;
  headline?: string;
  continuity_advancing?: boolean;
  signals?: ContinuitySignal[];
  processed_count: number | null;
  object_count_label: string | null;
  backlog_count: number | null;
  last_success_at: string | null;
  blockers: string[];
  issues: string[];
};

export type IngestionRunTriggerKind = "scheduled" | "manual" | "replay";

export type PipelineRecentIngestionRun = {
  run_id: string;
  connector: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  raw_rows_written: number | null;
  trigger_kind: IngestionRunTriggerKind;
};

export type NextScheduledIngestionStatus =
  | "disabled"
  | "paused"
  | "no_connectors"
  | "running"
  | "eligible_now"
  | "waiting_cooldown";

export type PipelineNextScheduledIngestion = {
  status: NextScheduledIngestionStatus;
  next_at: string | null;
  summary: string;
  beat_interval_seconds: number;
  min_gap_seconds: number;
  next_connector?: string | null;
  connectors_eligible_now?: string[];
};

export type PipelineOverview = {
  tenant_id: string;
  execution: {
    fsm_state: string | null;
    phase_cursor: string | null;
    lease_status: string | null;
    block_reason_code: string | null;
  };
  continuity_status?: ContinuityStatus | null;
  phases: PipelineOverviewPhase[];
  attention: string[];
  attention_items?: AttentionItem[];
  scheduler?: {
    env_scheduler_enabled: boolean;
    paused_via_redis: boolean;
    beat_interval_seconds: number;
    min_gap_seconds: number;
    operator_mode_label?: string;
  };
  runnable_connectors: string[];
  recent_ingestion_runs: PipelineRecentIngestionRun[];
  next_scheduled_ingestion?: PipelineNextScheduledIngestion | null;
};

export const OPERATOR_PHASES: Array<{ phase: OperatorPhase; label: string; route: string }> = [
  { phase: "ingestion", label: "Ingestion", route: "ingestion" },
  { phase: "canonical", label: "Canonical", route: "canonical" },
  { phase: "identity", label: "Identity", route: "identity" },
  { phase: "graph", label: "Graph", route: "graph" },
  { phase: "reconstruction", label: "Traversal", route: "reconstruction" },
  { phase: "retrieval", label: "Retrieval", route: "retrieval" },
  { phase: "synthesis", label: "Synthesis", route: "synthesis" },
];

export const START_PHASE_OPTIONS: Array<{ value: string; label: string; apiPhase: string }> = [
  { value: "canonical", label: "Canonical", apiPhase: "CANONICAL" },
  { value: "identity", label: "Identity", apiPhase: "IDENTITY" },
  { value: "graph", label: "Graph", apiPhase: "GRAPH" },
  { value: "reconstruction", label: "Reconstruction", apiPhase: "TCRE" },
  { value: "retrieval", label: "Retrieval", apiPhase: "RETRIEVAL" },
  { value: "synthesis", label: "Synthesis", apiPhase: "SYNTHESIS" },
];
