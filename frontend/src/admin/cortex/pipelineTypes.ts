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

export type ExecutionInspect = {
  tenant_id: string;
  lease: {
    status: string | null;
    fsm_state: string | null;
    phase_cursor: string | null;
    block_reason_code: string | null;
    block_detail?: string | null;
  } | null;
  progression: {
    phase_status?: Record<string, string>;
    active_phase?: string | null;
    stop_reason?: string | null;
    progression_class?: string | null;
    execution_lease?: {
      last_phase_receipt_outcome?: string | null;
      last_phase_receipt_hash?: string | null;
    } | null;
  } | null;
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
