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
  detail: string | null;
  route: string;
};

export type PipelineOverviewPhase = {
  phase: OperatorPhase;
  status: PhaseStatus;
  processed_count: number | null;
  backlog_count: number | null;
  last_success_at: string | null;
  blockers: string[];
};

export type PipelineOverview = {
  tenant_id: string;
  execution: {
    fsm_state: string | null;
    phase_cursor: string | null;
    lease_status: string | null;
    block_reason_code: string | null;
  };
  phases: PipelineOverviewPhase[];
  attention: string[];
  scheduler?: {
    env_scheduler_enabled: boolean;
    paused_via_redis: boolean;
    beat_interval_seconds: number;
    min_gap_seconds: number;
  };
  runnable_connectors: string[];
};

export const OPERATOR_PHASES: Array<{ phase: OperatorPhase; label: string; route: string }> = [
  { phase: "ingestion", label: "Ingestion", route: "ingestion" },
  { phase: "canonical", label: "Canonical", route: "canonical" },
  { phase: "identity", label: "Identity", route: "identity" },
  { phase: "graph", label: "Graph", route: "graph" },
  { phase: "reconstruction", label: "Reconstruction", route: "reconstruction" },
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
