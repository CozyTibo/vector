/**
 * Cortex Graph / walk control plane mock — derives all metrics from a deterministic walk substrate.
 * @see graphWalkDerivedState.ts
 */

export type {
  BoundednessRow,
  DriftIssueRow,
  GraphControlPlaneViewModel,
  GraphForensicView,
  GraphOperation,
  GraphOverallStatus,
  GraphSubstrateSnapshot,
  ReadinessCard,
  ReadinessDecision,
  RowStatus,
  RuntimeLaneRow,
  SnapshotCard,
  SnapshotCardTier,
  TemporalLegalityRow,
  TopologyHealthRow,
  TraversalProofRow,
} from "./graphControlPlaneTypes";

export { GRAPH_FORENSIC_VIEWS } from "./graphControlPlaneTypes";

import { deriveGraphControlPlaneViewModel } from "./graphWalkDerivedState";

export { deriveGraphControlPlaneViewModel };

export function getGraphControlPlaneMock(tenantId: string) {
  return deriveGraphControlPlaneViewModel(tenantId);
}
