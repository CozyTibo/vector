/** Shared view-model types for the Cortex Graph / walk control plane (UI consumes only these). */

export type GraphOverallStatus =
  | "healthy"
  | "degraded"
  | "rebuilding"
  | "drift_detected"
  | "replay_divergence"
  | "unverifiable";

export type RowStatus = "healthy" | "degraded" | "rebuilding" | "blocked";

export type ReadinessDecision = "pass" | "fail" | "warn";

export type SnapshotCardTier = "primary" | "secondary" | "operational";

export interface SnapshotCard {
  id: string;
  label: string;
  value: string;
  tone: "ok" | "warn" | "bad";
  freshness: string;
  hint?: string;
  linkTo?: "verification" | "memory" | "canonical_replay" | "canonical_health" | "explorer";
  tier: SnapshotCardTier;
}

export interface GraphSubstrateSnapshot {
  overall: GraphOverallStatus;
  updatedAt: string;
  cards: SnapshotCard[];
}

export interface TopologyHealthRow {
  area: string;
  /** Reconstructed edges attributed to this substrate layer (evidence-backed count). */
  evidenceBackedEdges: number;
  unstableEdges: number;
  contradictionIncidents: number;
  continuityGaps: number;
  weakProvenanceEdges: number;
  traversalStatus: RowStatus;
}

/** Forensic explorer tabs — execution-graph debugger (deterministic text, no graph viz). */
export const GRAPH_FORENSIC_VIEWS = [
  "path",
  "edge_provenance",
  "causal_chain",
  "recon_route",
  "drift_origin",
  "contradictions",
  "replay_evidence",
  "anchor_lineage",
  "lineage",
  "edge_table",
  "continuity",
  "minimap",
] as const;

export type GraphForensicView = (typeof GRAPH_FORENSIC_VIEWS)[number];

export interface ReadinessCard {
  id: string;
  label: string;
  decision: ReadinessDecision;
  detail: string;
  doctrineRef: string;
}

export interface BoundednessRow {
  metric: string;
  value: string;
  limit: string;
  notes: string;
}

export interface TemporalLegalityRow {
  check: string;
  state: ReadinessDecision;
  detail: string;
}

export interface RuntimeLaneRow {
  lane: string;
  status: RowStatus;
  queue: number;
  frontierSize: number;
  avgLatencyMs: number;
  replayJobs: number;
  failures: number;
}

export interface GraphOperation {
  id: string;
  label: string;
  description: string;
  requiresConfirm?: boolean;
}

export interface DriftIssueRow {
  issue: string;
  severity: "info" | "warn" | "critical";
  substrateLayer: string;
  replaySafe: "yes" | "no" | "unknown";
  recoverable: "yes" | "no" | "partial";
  operatorAction: string;
}

export interface TraversalProofRow {
  artifact: string;
  value: string;
  status: ReadinessDecision;
  notes: string;
}

/** Full payload for `AdminCortexGraphPage` (walk-derived; no raw walk JSON in UI). */
export interface GraphControlPlaneViewModel {
  snapshot: GraphSubstrateSnapshot;
  topology: TopologyHealthRow[];
  readinessConstitutional: ReadinessCard[];
  readinessRuntime: ReadinessCard[];
  boundedness: BoundednessRow[];
  temporalLegality: TemporalLegalityRow[];
  runtime: RuntimeLaneRow[];
  safeOps: GraphOperation[];
  dangerousOps: GraphOperation[];
  drift: DriftIssueRow[];
  proofs: TraversalProofRow[];
  /** Operator-safe lines derived from a representative walk (forensic panel). */
  forensicLines: string[];
  /** Same layout as `forensicLines`, keyed by explorer view (substrate-derived). */
  forensicByView: Record<GraphForensicView, string[]>;
}
