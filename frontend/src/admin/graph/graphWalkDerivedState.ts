/**
 * Deterministic walk substrate + causal derivation for the Graph control plane.
 * All UI metrics derive from shared `TraversalWalk` entities and propagated signals.
 */

import type {
  BoundednessRow,
  DriftIssueRow,
  GraphControlPlaneViewModel,
  GraphForensicView,
  GraphOperation,
  GraphOverallStatus,
  GraphSubstrateSnapshot,
  ReadinessCard,
  ReadinessDecision,
  RuntimeLaneRow,
  SnapshotCard,
  TemporalLegalityRow,
  TraversalProofRow,
} from "./graphControlPlaneTypes";
import type { EdgeAggregateSignals, EdgeProvenance, EdgeValidity, ExecutionCausalChain } from "./graphEdgeTruth";
import {
  aggregateEdgeSignals,
  buildExecutionCausalChains,
  buildReconstructedEdges,
  distributeEdgesToTopologyLayers,
  formatCausalChainLines,
  formatEdgeProvenanceLines,
  pickRepresentativeEdge,
  scoreAllEdges,
} from "./graphEdgeTruth";

/** Internal walk record — drives aggregates only (not rendered as JSON). */
export interface TraversalWalk {
  walk_id: string;
  traversal_policy: string;
  root_node: string;
  hop_budget: number;
  frontier_cap: number;
  traversal_hash: string;
  replay_hash: string;
  replay_equivalent: boolean;
  legality_state: "deterministic" | "replay_safe" | "partially_replay_safe" | "unverifiable" | "drifted";
  truncation_reason: string | null;
  termination_reason: "goal" | "budget" | "empty_frontier" | "legality_halt" | "replay_abort";
  continuity_window: string;
  temporal_anchor_start: string;
  temporal_anchor_end: string;
  provenance_chain: string[];
  export_sequence_ref: number;
  replay_job_id: string | null;
  bounded: boolean;
  replay_safe: boolean;
  /** Twin-run: ordering differs on replay. */
  ordering_drift_twin: boolean;
  /** Snapshot closure violated on export interval (constitutional temporal). */
  snapshot_closure_illegal: boolean;
  /** Continuity ledger / hop receipt class mismatch. */
  continuity_corruption: boolean;
  /** export_sequence_ref inconsistent with walk anchor window. */
  export_sequence_mismatch: boolean;
  /** Truncation class differed between twin runs. */
  truncation_mismatch_twin: boolean;
  /** Walk still holding frontier budget (saturation signal). */
  frontier_active: boolean;
}

export type ReplayDriftClass =
  | "ordering_drift"
  | "temporal_drift"
  | "authority_conflict"
  | "continuity_corruption"
  | "truncation_mismatch"
  | "late_import_replay_skew"
  | "export_sequence_mismatch";

function fnv1a32(input: string): number {
  let h = 2166136261;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function mulberry32(seed: number): () => number {
  return () => {
    let t = (seed += 0x6d2b79f5);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function shortHex(seed: number, salt: string): string {
  const x = fnv1a32(`${seed}:${salt}`) >>> 0;
  return x.toString(16).padStart(8, "0").slice(0, 8);
}

function isoFromSeed(seed: number): string {
  const day = 1 + (seed % 28);
  const hour = seed % 24;
  const min = (seed >>> 3) % 60;
  return `2026-05-${String(day).padStart(2, "0")}T${String(hour).padStart(2, "0")}:${String(min).padStart(2, "0")}:00Z`;
}

const WALK_COUNT = 52;

function buildWalks(tenantId: string): TraversalWalk[] {
  const base = fnv1a32(tenantId || "default");
  const rand = mulberry32(base ^ 0x9e3779b9);
  const walks: TraversalWalk[] = [];
  const slug = tenantId.replace(/[^a-z0-9]/gi, "").slice(0, 8) || "tenant";

  for (let i = 0; i < WALK_COUNT; i++) {
    const policy = `octs-pol-v1:${100 + ((base + i * 31) % 800)}`;
    const root = `org-node:${((base + i) * 17) % 100_000}`;
    const hopBudget = 8 + ((base + i * 5) % 25);
    const frontierCap = 32 + ((base + i * 3) % 96);
    const exportRef = 10_000 + ((base + i * 13) % 50_000);

    const temporalGap = (base + i * 17) % 23 === 0;
    const continuityCorrupt = (base + i * 19) % 29 === 0;
    const orderingDrift = (base + i * 11) % 31 === 0 && !continuityCorrupt;
    const exportMismatch = temporalGap && (base + i) % 3 === 0;
    const truncMismatch = continuityCorrupt && (base + i) % 2 === 0;
    const frontierActive = rand() < 0.12;

    const walkId = `oct-wk-${slug}-${i.toString(16).padStart(3, "0")}`;
    const th = `sha256:${shortHex(base + i, walkId)}${shortHex(base + i * 7, policy)}`;
    let replayHash = th;
    let replayEquivalent = true;
    let legality: TraversalWalk["legality_state"] = "deterministic";
    let replaySafe = true;

    if (continuityCorrupt) {
      replayHash = `sha256:${shortHex(base + i + 999, walkId)}00000001`;
      replayEquivalent = false;
      legality = "drifted";
      replaySafe = false;
    } else if (temporalGap || exportMismatch) {
      replayHash = `sha256:${shortHex(base + i + 404, walkId)}ffff0002`;
      replayEquivalent = false;
      legality = orderingDrift ? "partially_replay_safe" : "partially_replay_safe";
      replaySafe = false;
    } else if (orderingDrift) {
      replayHash = `sha256:${shortHex(base + i + 303, walkId)}aaaa0003`;
      replayEquivalent = false;
      legality = "partially_replay_safe";
      replaySafe = true;
    } else if ((base + i * 41) % 37 === 0) {
      legality = "unverifiable";
      replayEquivalent = false;
      replaySafe = false;
    } else {
      legality = "replay_safe";
    }

    const truncated = rand() < 0.18;
    const truncReason = truncated ? (rand() < 0.55 ? "hop_budget" : "frontier_cap") : null;
    const term: TraversalWalk["termination_reason"] = truncated
      ? truncReason === "hop_budget"
        ? "budget"
        : "empty_frontier"
      : rand() < 0.92
        ? "goal"
        : "legality_halt";

    const snapshotIllegal = temporalGap || exportMismatch;
    const ns0 = 1_700_000_000_000_000_000n + BigInt((base + i) * 1_000_000);
    const ns1 = ns0 + 60_000_000_000n;
    const chainLen = 2 + ((base + i) % 4);
    const prov: string[] = [];
    for (let c = 0; c < chainLen; c++) {
      prov.push(`prv:${shortHex(base + i + c * 101, `${walkId}:${c}`)}`);
    }

    const replayJob =
      !replayEquivalent || legality === "unverifiable"
        ? `wrj-${shortHex(base + i * 91, walkId)}`
        : rand() < 0.08
          ? `wrj-${shortHex(base + i * 97, walkId)}`
          : null;

    walks.push({
      walk_id: walkId,
      traversal_policy: policy,
      root_node: root,
      hop_budget: hopBudget,
      frontier_cap: frontierCap,
      traversal_hash: th,
      replay_hash: replayHash,
      replay_equivalent: replayEquivalent,
      legality_state: legality,
      truncation_reason: truncated ? truncReason : null,
      termination_reason: term,
      continuity_window: `[${ns0.toString()},${ns1.toString()})`,
      temporal_anchor_start: ns0.toString(),
      temporal_anchor_end: ns1.toString(),
      provenance_chain: prov,
      export_sequence_ref: exportRef,
      replay_job_id: replayJob,
      bounded: true,
      replay_safe: replaySafe,
      ordering_drift_twin: orderingDrift,
      snapshot_closure_illegal: snapshotIllegal,
      continuity_corruption: continuityCorrupt,
      export_sequence_mismatch: exportMismatch,
      truncation_mismatch_twin: truncMismatch,
      frontier_active: frontierActive,
    });
  }
  return walks;
}

interface WalkSubstrateSignals {
  walkCount: number;
  temporal_anchor_gap_count: number;
  snapshot_closure_illegal_count: number;
  continuity_corruption_count: number;
  replay_divergence_count: number;
  ordering_drift_count: number;
  export_sequence_mismatch_count: number;
  truncation_mismatch_count: number;
  replay_queue_backlog: number;
  unverifiable_count: number;
  replay_equivalent_count: number;
  frontier_active_count: number;
  truncation_events: number;
  hop_budget_exhaustions: number;
  bounded_legality_halts: number;
  replayDriftHistogram: Partial<Record<ReplayDriftClass, number>>;
  /** Aggregate replay-equivalence confidence (constitutional). */
  replayEquivalenceConfidence: TraversalWalk["legality_state"] | "mixed";
}

type SubstrateSignals = WalkSubstrateSignals & EdgeAggregateSignals;

function computeWalkSignals(walks: TraversalWalk[]): WalkSubstrateSignals {
  const snapshot_closure_illegal_count = walks.filter((w) => w.snapshot_closure_illegal).length;
  const temporal_anchor_gap_count = snapshot_closure_illegal_count;
  const continuity_corruption_count = walks.filter((w) => w.continuity_corruption).length;
  const replay_divergence_count = walks.filter((w) => !w.replay_equivalent && w.replay_hash !== w.traversal_hash).length;
  const ordering_drift_count = walks.filter((w) => w.ordering_drift_twin).length;
  const export_sequence_mismatch_count = walks.filter((w) => w.export_sequence_mismatch).length;
  const truncation_mismatch_count = walks.filter((w) => w.truncation_mismatch_twin).length;
  const replay_queue_backlog = walks.filter((w) => w.replay_job_id !== null).length;
  const unverifiable_count = walks.filter((w) => w.legality_state === "unverifiable").length;
  const replay_equivalent_count = walks.filter((w) => w.replay_equivalent).length;
  const frontier_active_count = walks.filter((w) => w.frontier_active).length;
  const truncation_events = walks.filter((w) => w.truncation_reason !== null).length;
  const hop_budget_exhaustions = walks.filter((w) => w.termination_reason === "budget").length;
  const bounded_legality_halts = walks.filter((w) => w.termination_reason === "legality_halt").length;

  const h: Partial<Record<ReplayDriftClass, number>> = {};
  for (const w of walks) {
    if (w.ordering_drift_twin) h.ordering_drift = (h.ordering_drift ?? 0) + 1;
    if (w.snapshot_closure_illegal && !w.export_sequence_mismatch) h.temporal_drift = (h.temporal_drift ?? 0) + 1;
    if (w.export_sequence_mismatch) h.export_sequence_mismatch = (h.export_sequence_mismatch ?? 0) + 1;
    if (w.continuity_corruption) h.continuity_corruption = (h.continuity_corruption ?? 0) + 1;
    if (w.truncation_mismatch_twin) h.truncation_mismatch = (h.truncation_mismatch ?? 0) + 1;
    if (w.snapshot_closure_illegal && w.export_sequence_mismatch) h.late_import_replay_skew = (h.late_import_replay_skew ?? 0) + 1;
  }

  let replayEquivalenceConfidence: WalkSubstrateSignals["replayEquivalenceConfidence"] = "deterministic";
  if (unverifiable_count > 0) replayEquivalenceConfidence = "unverifiable";
  else if (continuity_corruption_count > 0) replayEquivalenceConfidence = "drifted";
  else if (replay_divergence_count > walks.length * 0.12) replayEquivalenceConfidence = "partially_replay_safe";
  else if (replay_divergence_count > 0) replayEquivalenceConfidence = "partially_replay_safe";
  else replayEquivalenceConfidence = "replay_safe";

  return {
    walkCount: walks.length,
    temporal_anchor_gap_count,
    snapshot_closure_illegal_count,
    continuity_corruption_count,
    replay_divergence_count,
    ordering_drift_count,
    export_sequence_mismatch_count,
    truncation_mismatch_count,
    replay_queue_backlog,
    unverifiable_count,
    replay_equivalent_count,
    frontier_active_count,
    truncation_events,
    hop_budget_exhaustions,
    bounded_legality_halts,
    replayDriftHistogram: h,
    replayEquivalenceConfidence,
  };
}

function deriveOverall(s: SubstrateSignals): GraphOverallStatus {
  if (s.continuity_corruption_count > 0 && s.replay_divergence_count > s.walkCount * 0.08) return "replay_divergence";
  if (s.unverifiable_count > 1) return "unverifiable";
  if (s.temporal_anchor_gap_count > 0) return "drift_detected";
  if (s.replay_queue_backlog > Math.max(14, s.walkCount * 0.28)) return "degraded";
  if (s.replay_queue_backlog > 8 || s.continuity_corruption_count > 0) return "degraded";
  if (s.replay_divergence_count > 0 && s.temporal_anchor_gap_count === 0) return "degraded";
  return "healthy";
}

function pct(part: number, whole: number): string {
  if (whole === 0) return "0%";
  return `${((1000 * part) / whole / 10).toFixed(1)}%`;
}

function decisionFrom(cond: boolean, warnIf: boolean): ReadinessDecision {
  if (cond) return "fail";
  if (warnIf) return "warn";
  return "pass";
}

function buildSnapshot(s: SubstrateSignals, walks: TraversalWalk[], seed: number): GraphSubstrateSnapshot {
  const bounded24 = walks.length;
  const replayPct = pct(s.replay_equivalent_count, s.walkCount);
  const continuityEdgePct = pct(
    s.walkCount - s.continuity_corruption_count - Math.min(s.ordering_drift_count, s.walkCount),
    s.walkCount,
  );

  const orderingHealthy =
    s.ordering_drift_count === 0 && s.truncation_mismatch_count === 0 ? "pass" : s.ordering_drift_count < 3 ? "degraded" : "fail";
  const orderingTone: "ok" | "warn" | "bad" =
    orderingHealthy === "pass" ? "ok" : orderingHealthy === "degraded" ? "warn" : "bad";

  const traversalLegalityVal =
    s.unverifiable_count > 0 ? "blocked" : s.continuity_corruption_count > 0 ? "partial" : s.replay_divergence_count > 4 ? "partial" : "nominal";
  const travTone: "ok" | "warn" | "bad" =
    traversalLegalityVal === "blocked" ? "bad" : traversalLegalityVal === "partial" ? "warn" : "ok";

  const temporalVal = s.temporal_anchor_gap_count > 2 ? "fail" : s.temporal_anchor_gap_count > 0 ? "warn" : "pass";
  const temporalTone: "ok" | "warn" | "bad" =
    temporalVal === "fail" ? "bad" : temporalVal === "warn" ? "warn" : "ok";

  const driftWindow = `${s.replay_divergence_count} / ${bounded24}`;
  const edgeValidityLine = `${s.edge_validity_stable} stable · ${s.edge_validity_degraded} degraded · ${s.edge_validity_replay_risky} replay_risky · ${s.edge_validity_unverifiable} unverifiable`;

  const cards: SnapshotCard[] = [
    {
      id: "bounded_walks",
      label: "Bounded walks (24h)",
      value: bounded24.toLocaleString(),
      tone: s.bounded_legality_halts > s.walkCount * 0.15 ? "warn" : "ok",
      freshness: "walk ledger",
      hint: "Walk entities completed in window — primitive is the bounded walk, not the projection.",
      tier: "primary",
      linkTo: "explorer",
    },
    {
      id: "replay_equiv_pct",
      label: "Replay-equivalent walks (twin-run)",
      value: replayPct,
      tone: s.replay_equivalent_count < s.walkCount * 0.85 ? "warn" : "ok",
      freshness: `confidence: ${s.replayEquivalenceConfidence}`,
      hint: "Same walk_id replayed twice: traversal_hash, replay_hash, receipts, termination parity.",
      tier: "primary",
      linkTo: "verification",
    },
    {
      id: "continuity_edges_pct",
      label: "Continuity-valid edges (ledger)",
      value: continuityEdgePct,
      tone: s.continuity_corruption_count > 0 ? "warn" : "ok",
      freshness: "replay-derived",
      hint: "Continuity ledger edges consistent with hop receipts after causal propagation from walk substrate.",
      tier: "primary",
    },
    {
      id: "deterministic_ordering",
      label: "Deterministic ordering health",
      value: orderingHealthy === "pass" ? "pass" : orderingHealthy,
      tone: orderingTone,
      freshness: "twin ordering",
      hint: "Propagates ordering_drift + truncation_mismatch signals from twin-run replay validation.",
      tier: "primary",
    },
    {
      id: "traversal_legality",
      label: "Traversal legality",
      value: traversalLegalityVal,
      tone: travTone,
      freshness: "walk law",
      hint: "Cascades continuity corruption + unverifiable walks into legality posture.",
      tier: "primary",
      linkTo: "verification",
    },
    {
      id: "temporal_continuity_snap",
      label: "Temporal ordering continuity",
      value: temporalVal,
      tone: temporalTone,
      freshness: `${s.temporal_anchor_gap_count} anchor gaps`,
      hint: "Chains from snapshot_closure_illegal walks → replay chronology risk → bounded-walk degradation.",
      tier: "primary",
    },
    {
      id: "edge_validity_profile",
      label: "Reconstructed edge validity (substrate)",
      value: edgeValidityLine,
      tone:
        s.edge_validity_replay_risky + s.edge_validity_unverifiable > s.edge_total * 0.25
          ? "warn"
          : s.edge_validity_unverifiable > 0
            ? "warn"
            : "ok",
      freshness: "deterministic derivation",
      hint: "edge_validity from provenance + twin-run replay + continuity — not ML scores.",
      tier: "secondary",
      linkTo: "explorer",
    },
    {
      id: "unstable_recon_edges",
      label: "Unstable reconstructed edges",
      value: String(s.unstable_edge_count),
      tone: s.unstable_edge_count > s.edge_total * 0.35 ? "warn" : "ok",
      freshness: "≠ stable",
      hint: "Count of edges whose validity is not stable (degraded, replay_risky, or unverifiable).",
      tier: "secondary",
    },
    {
      id: "edges_with_contradictions",
      label: "Edges with contradiction flags",
      value: String(s.edges_with_contradictions),
      tone: s.edges_with_contradictions > 0 ? "warn" : "ok",
      freshness: "substrate",
      hint: "Ownership, chronology, replay_hash, or temporal_anchor contradictions propagated from walks.",
      tier: "secondary",
    },
    {
      id: "causal_chain_breakpoints",
      label: "Causal chain breakpoints (aggregate)",
      value: String(s.causal_chain_breakpoints),
      tone: s.causal_chain_breakpoints > 4 ? "warn" : "ok",
      freshness: "execution chains",
      hint: "Synthetic execution-causal chains: inferred breakpoints from replay + continuity stress.",
      tier: "secondary",
    },
    {
      id: "tenant_slices",
      label: "Continuity-certified tenant slices",
      value: s.unverifiable_count > 0 ? "0" : "1",
      tone: s.unverifiable_count > 0 ? "bad" : "ok",
      freshness: "org_graph_traversal",
      hint: "Collapses when unverifiable walks block slice certification.",
      tier: "operational",
      linkTo: "verification",
    },
    {
      id: "walk_frontier",
      label: "Walk frontier queue",
      value: String(s.frontier_active_count + Math.min(180, s.replay_queue_backlog * 4)),
      tone: s.frontier_active_count + s.replay_queue_backlog > 18 ? "warn" : "ok",
      freshness: "frontier congestion",
      hint: "Rises with replay backlog (replay starvation pressure on bounded-walk runtime).",
      tier: "operational",
    },
    {
      id: "replay_drift",
      label: "Walk replay drift (24h)",
      value: driftWindow,
      tone: s.replay_divergence_count > 0 ? "warn" : "ok",
      freshness: "drift classes",
      hint: "Counts walks failing twin-run parity (ordering, temporal, continuity, truncation, export skew).",
      tier: "operational",
      linkTo: "canonical_replay",
    },
    {
      id: "rebuild",
      label: "Last traversal projection rebuild",
      value:
        s.temporal_anchor_gap_count + s.continuity_corruption_count > 4
          ? "queued"
          : s.temporal_anchor_gap_count > 0
            ? "2h ago"
            : "8h ago",
      tone: s.temporal_anchor_gap_count + s.continuity_corruption_count > 2 ? "warn" : "ok",
      freshness: "projection pressure",
      hint: "Rebuild pressure propagates from temporal_anchor_gap + continuity_corruption (causal chain).",
      tier: "operational",
      linkTo: "canonical_health",
    },
    {
      id: "readiness",
      label: "Static walk verification bundle",
      value: s.replay_queue_backlog > 12 || s.unverifiable_count > 0 ? "stale" : s.replay_divergence_count > 2 ? "partial" : "fresh",
      tone: s.replay_queue_backlog > 12 || s.unverifiable_count > 0 ? "warn" : "ok",
      freshness: "G-P05 + slice",
      hint: "Replay queue backlog degrades certification freshness (runtime coupling).",
      tier: "operational",
      linkTo: "verification",
    },
  ];

  return {
    overall: deriveOverall(s),
    updatedAt: isoFromSeed(seed),
    cards,
  };
}

function buildReadinessConstitutional(s: SubstrateSignals): ReadinessCard[] {
  const replayDetail = `Twin-run replay validation: ${s.replay_equivalent_count}/${s.walkCount} walks replay-equivalent; aggregate confidence ${s.replayEquivalenceConfidence}.`;
  const replayDecision: ReadinessDecision =
    s.replayEquivalenceConfidence === "drifted" || s.replayEquivalenceConfidence === "unverifiable"
      ? "fail"
      : s.replayEquivalenceConfidence === "partially_replay_safe"
        ? "warn"
        : "pass";

  return [
    {
      id: "walk_contract",
      label: "walk_contract_law",
      decision: decisionFrom(s.unverifiable_count > 2, s.unverifiable_count > 0),
      detail:
        s.unverifiable_count > 0
          ? `${s.unverifiable_count} walks marked unverifiable — twin-run receipts incomplete.`
          : "Schema-first walk contracts; hop receipts under OCTS-CANON-1.",
      doctrineRef: "phase-05-walk-api-contracts.md",
    },
    {
      id: "replay_equiv",
      label: "replay_equivalence_law",
      decision: replayDecision,
      detail: replayDetail,
      doctrineRef: "phase-05-traversal-equivalence-doctrine.md",
    },
    {
      id: "path_legality",
      label: "path_legality_law",
      decision: decisionFrom(s.continuity_corruption_count > 3, s.continuity_corruption_count > 0),
      detail:
        s.continuity_corruption_count > 0
          ? `Continuity corruption on ${s.continuity_corruption_count} walks → path multiset legality partially degraded (causal).`
          : "Closed multigraph algebra holds on golden walk vectors.",
      doctrineRef: "phase-05-multigraph-model-doctrine.md",
    },
    {
      id: "deterministic_ordering",
      label: "deterministic_ordering_law",
      decision: decisionFrom(false, s.ordering_drift_count > 0 || s.truncation_mismatch_count > 0),
      detail:
        s.ordering_drift_count > 0
          ? `${s.ordering_drift_count} walks with ordering_drift_twin — frontier tie-break replay skew.`
          : "Frontier ordering deterministic across bounded expansions.",
      doctrineRef: "phase-05-walk-policy-doctrine.md",
    },
    {
      id: "bounded_compliance",
      label: "bounded_traversal_compliance",
      decision: decisionFrom(false, s.temporal_anchor_gap_count > 0 || s.bounded_legality_halts > s.walkCount * 0.12),
      detail:
        s.temporal_anchor_gap_count > 0
          ? `Temporal anchor gaps (${s.temporal_anchor_gap_count}) increase bounded-walk legality risk until replay closure.`
          : "Depth caps + hop budgets enforced; truncations within DIAG law.",
      doctrineRef: "phase-05-walk-policy-doctrine.md",
    },
    {
      id: "export_monotonicity",
      label: "export_monotonicity_law",
      decision: decisionFrom(s.export_sequence_mismatch_count > 2, s.export_sequence_mismatch_count > 0 || s.temporal_anchor_gap_count > 0),
      detail:
        s.export_sequence_mismatch_count > 0
          ? `${s.export_sequence_mismatch_count} walks with export_sequence_ref mismatch vs anchor window (constitutional export chronology).`
          : s.temporal_anchor_gap_count > 0
            ? `Snapshot closure legality stressed: ${s.temporal_anchor_gap_count} walks with illegal snapshot/export interval pairing.`
            : "export_sequence strictly monotonic on pinned connector slice.",
      doctrineRef: "phase-05-temporal-walk-doctrine.md",
    },
  ];
}

function buildReadinessRuntime(s: SubstrateSignals): ReadinessCard[] {
  return [
    {
      id: "temporal_runtime",
      label: "temporal_anchor_runtime",
      decision: decisionFrom(s.temporal_anchor_gap_count > 6, s.temporal_anchor_gap_count > 0),
      detail:
        s.temporal_anchor_gap_count > 0
          ? `${s.temporal_anchor_gap_count} walks violate snapshot closure / anchor continuity — cascades to replay chronology risk.`
          : "Temporal anchor runtime aligned with export chronology proofs.",
      doctrineRef: "phase-05-temporal-walk-doctrine.md",
    },
    {
      id: "replay_queue",
      label: "walk_replay_queue_pressure",
      decision: decisionFrom(s.replay_queue_backlog > 28, s.replay_queue_backlog > 8),
      detail:
        s.replay_queue_backlog > 8
          ? `Replay lane backlog ${s.replay_queue_backlog} (walk jobs) — replay starvation + certification freshness coupling.`
          : "Walk replay lanes within bounded queue SLO.",
      doctrineRef: "phase-05-walk-replay-doctrine.md",
    },
    {
      id: "corruption_scan",
      label: "corruption_scan_freshness",
      decision: decisionFrom(false, s.continuity_corruption_count > 0 || s.replay_queue_backlog > 14),
      detail:
        s.replay_queue_backlog > 14
          ? "Scan ledger fresh but replay pressure delays closure verification on drifted walks."
          : "OCTS corruption bundles vs catalog within SLO.",
      doctrineRef: "phase-05-verification-gates-doctrine.md",
    },
    {
      id: "api_readiness",
      label: "traversal_admin_api_runtime",
      decision: "pass",
      detail: "Admin walk + replay-verify routes hot; bounded request caps enforced.",
      doctrineRef: "phase-05-runtime-legality-matrix.md",
    },
    {
      id: "projection_jobs",
      label: "traversal_projection_job_state",
      decision: decisionFrom(false, s.temporal_anchor_gap_count + s.continuity_corruption_count > 2),
      detail:
        s.temporal_anchor_gap_count + s.continuity_corruption_count > 2
          ? "Projection rebuild pressure from walk-substrate causal chain (deterministic fallback may engage)."
          : "Traversal projection jobs nominal.",
      doctrineRef: "phase-05-derived-index-contract-doctrine.md",
    },
  ];
}

function buildBoundedness(s: SubstrateSignals, walks: TraversalWalk[]): BoundednessRow[] {
  const maxDepth = Math.max(...walks.map((w) => w.provenance_chain.length), 1);
  const cap = walks[0]?.hop_budget ?? 32;
  const frontierUtil = Math.min(
    99,
    Math.round(
      (100 * (s.frontier_active_count + s.replay_queue_backlog * 0.35)) / Math.max(1, walks.length * 0.45),
    ),
  );
  const compliance =
    s.bounded_legality_halts === 0 && s.continuity_corruption_count === 0
      ? "100%"
      : `${(100 - (100 * s.bounded_legality_halts) / walks.length).toFixed(1)}%`;

  return [
    {
      metric: "Max traversal depth (policy cap)",
      value: String(Math.min(cap, maxDepth + 4)),
      limit: String(cap),
      notes: "Derived from walk hop_budget + provenance_chain depth envelope.",
    },
    {
      metric: "Frontier cap utilization",
      value: `${frontierUtil}%`,
      limit: "100%",
      notes: s.replay_queue_backlog > 10 ? "Elevated: replay starvation + frontier congestion (coupled)." : "Walk frontier vs policy cap.",
    },
    {
      metric: "Walk truncation events (24h)",
      value: String(s.truncation_events),
      limit: "—",
      notes: "Budget / frontier truncations — expected under bounded-walk exhaustion pressure.",
    },
    {
      metric: "Hop-budget exhaustion",
      value: String(s.hop_budget_exhaustions),
      limit: "—",
      notes: "Walks terminated at hop receipt cap (deterministic DIAG semantics).",
    },
    {
      metric: "Bounded-walk compliance",
      value: compliance,
      limit: "100%",
      notes:
        s.temporal_anchor_gap_count > 0
          ? "Degraded while temporal_anchor_gap walks remain open (causal)."
          : "No policy-violating completions in window.",
    },
    {
      metric: "Walk termination causes (top)",
      value:
        s.bounded_legality_halts > 0
          ? `goal | budget | legality_halt(${s.bounded_legality_halts})`
          : "goal | budget | empty_frontier",
      limit: "—",
      notes: "Histogram from walk termination_reason field.",
    },
  ];
}

function buildTemporalLegality(s: SubstrateSignals): TemporalLegalityRow[] {
  return [
    {
      check: "Snapshot interval legality",
      state: decisionFrom(s.temporal_anchor_gap_count > 5, s.temporal_anchor_gap_count > 0),
      detail:
        s.temporal_anchor_gap_count > 0
          ? `${s.temporal_anchor_gap_count} walks: snapshot closure legality violated on export interval (half-open law).`
          : "All walked intervals admit snapshot closure under export_sequence.",
    },
    {
      check: "Export chronology legality",
      state: decisionFrom(s.export_sequence_mismatch_count > 2, s.export_sequence_mismatch_count > 0),
      detail:
        s.export_sequence_mismatch_count > 0
          ? `${s.export_sequence_mismatch_count} walks: export_sequence_ref inconsistent with temporal_anchor window.`
          : "Connector export chronology monotone vs walk anchors.",
    },
    {
      check: "Temporal anchor continuity",
      state: decisionFrom(false, s.temporal_anchor_gap_count > 0),
      detail:
        s.temporal_anchor_gap_count > 0
          ? `Anchor chain gaps propagate to replay chronology + walk replay divergence risk.`
          : "Anchor total order continuous on active slice.",
    },
    {
      check: "Replay interval certification",
      state: decisionFrom(s.replay_divergence_count > s.walkCount * 0.2, s.replay_divergence_count > 0),
      detail: `${s.replay_divergence_count} walks failed twin-run closure — replay window not certified.`,
    },
    {
      check: "Cross-source chronology conflict",
      state: decisionFrom(false, s.ordering_drift_count > 0),
      detail:
        s.ordering_drift_count > 0
          ? `${s.ordering_drift_count} walks: ordering drift between walk telemetry and replay lane.`
          : "No cross-source ordering inversion detected.",
    },
    {
      check: "Late arrival legality",
      state: decisionFrom(false, (s.replayDriftHistogram.late_import_replay_skew ?? 0) > 0),
      detail:
        (s.replayDriftHistogram.late_import_replay_skew ?? 0) > 0
          ? "Late-import replay skew class present on walk substrate."
          : "Late connector arrivals within replay-safe acceptance envelope.",
    },
    {
      check: "Snapshot closure legality",
      state: decisionFrom(s.snapshot_closure_illegal_count > 4, s.snapshot_closure_illegal_count > 0),
      detail:
        s.snapshot_closure_illegal_count > 0
          ? `${s.snapshot_closure_illegal_count} walks: snapshot closure legality violated on export interval (pinned snapshot vs walk window).`
          : "Snapshot closure holds for all bounded walks in window.",
    },
    {
      check: "Export monotonicity proof",
      state: s.export_sequence_mismatch_count > 0 ? "warn" : "pass",
      detail: s.export_sequence_mismatch_count > 0 ? "Skew detected — see export chronology legality row." : "Formal monotone proof on active cursor.",
    },
    {
      check: "Replay window closure",
      state: s.replay_queue_backlog > 16 ? "warn" : "pass",
      detail:
        s.replay_queue_backlog > 16
          ? "Replay backlog delays twin-run closure — traversal quarantine lanes may engage."
          : "Replay windows closing within bounded SLA.",
    },
  ];
}

const SAFE_OPS: GraphOperation[] = [
  {
    id: "regen_projections",
    label: "Regenerate traversal projections",
    description: "Replay-derive traversal projections from canonical continuity (bounded reconstruction job).",
  },
  {
    id: "recompute_continuity",
    label: "Recompute continuity edges",
    description: "Re-derive continuity ledger from authoritative identity resolution (replay-generated, not edited).",
  },
  {
    id: "rematerialize_indexes",
    label: "Re-materialize traversal indexes",
    description: "Replay-safe derived index regeneration with publish barrier for bounded walks.",
  },
  {
    id: "run_walk_verification",
    label: "Run walk verification bundle",
    description: "Execute static G-P05 gates + tenant org_graph_traversal slice over walk ledger.",
  },
  {
    id: "corruption_scan",
    label: "Run corruption scan",
    description: "OCTS corruption vectors vs wired gate catalog.",
  },
  {
    id: "path_indexes",
    label: "Recompute walk path indexes",
    description: "Deterministic path multiset indexes from walk_policy hash.",
  },
  {
    id: "temporal_order",
    label: "Rebuild temporal ordering",
    description: "Re-anchor replay-safe chronology from export receipts (constitutional).",
  },
  {
    id: "replay_receipts",
    label: "Replay walk receipts",
    description: "Re-close bounded walk receipts against pinned policy_hash (twin-run discipline).",
  },
];

const DANGEROUS_OPS: GraphOperation[] = [
  {
    id: "wipe_artifacts",
    label: "Purge derived traversal artifacts",
    description: "Destructive purge of replay-generated projections (operator phrase + window).",
    requiresConfirm: true,
  },
  {
    id: "wipe_indexes",
    label: "Purge derived traversal indexes",
    description: "Destructive: replay indexes dropped until regeneration completes.",
    requiresConfirm: true,
  },
  {
    id: "purge_orphans",
    label: "Purge orphan projection vertices",
    description: "Destructive reconstruction step after audit export — not mutable graph edit.",
    requiresConfirm: true,
  },
  {
    id: "reset_lineage",
    label: "Reset walk replay lineage",
    description: "Destructive: clears WRJ lineage pointers; incident protocol only.",
    requiresConfirm: true,
  },
  {
    id: "full_reconstruct",
    label: "Cold-reconstruct traversal substrate",
    description: "Full replay regeneration from authoritative sources; long-running.",
    requiresConfirm: true,
  },
];

function buildDrift(s: SubstrateSignals): DriftIssueRow[] {
  const rows: DriftIssueRow[] = [];
  if (s.continuity_corruption_count > 0) {
    rows.push({
      issue: "continuity corruption (constitutional)",
      severity: s.continuity_corruption_count > 2 ? "critical" : "warn",
      substrateLayer: "identity continuity graph",
      replaySafe: "no",
      recoverable: s.continuity_corruption_count > 2 ? "partial" : "yes",
      operatorAction: "Freeze affected bounded walks + cold-reconstruct continuity ledger from replay authority.",
    });
  }
  if (s.temporal_anchor_gap_count > 0) {
    rows.push({
      issue: "temporal legality drift (snapshot closure)",
      severity: s.temporal_anchor_gap_count > 4 ? "critical" : "warn",
      substrateLayer: "temporal ordering graph",
      replaySafe: "unknown",
      recoverable: "yes",
      operatorAction: "Rebuild temporal ordering + certify replay interval closure before walk replay expansion.",
    });
  }
  if (s.replay_divergence_count > 0) {
    rows.push({
      issue: "walk replay divergence (twin-run)",
      severity: "warn",
      substrateLayer: "replay lineage graph",
      replaySafe: "no",
      recoverable: "partial",
      operatorAction: "Inspect replay receipts + walk_result_hash / traversal_hash pair; classify drift bucket.",
    });
  }
  if (s.ordering_drift_count > 0) {
    rows.push({
      issue: "ordering drift (twin-run)",
      severity: "warn",
      substrateLayer: "traversal projection graph",
      replaySafe: "no",
      recoverable: "yes",
      operatorAction: "Replay topology derivation with deterministic fallback mode; quarantine hot shard if needed.",
    });
  }
  if (s.export_sequence_mismatch_count > 0) {
    rows.push({
      issue: "export sequence mismatch (chronology)",
      severity: "warn",
      substrateLayer: "export projection graph",
      replaySafe: "no",
      recoverable: "yes",
      operatorAction: "Reconcile export_sequence_ref against walk anchor window; block late-import skew.",
    });
  }
  if (s.truncation_mismatch_count > 0) {
    rows.push({
      issue: "truncation mismatch (twin-run)",
      severity: "warn",
      substrateLayer: "provenance graph",
      replaySafe: "no",
      recoverable: "partial",
      operatorAction: "Compare hop receipt truncation DIAG across twin runs; align walk_policy hash.",
    });
  }
  if (rows.length === 0) {
    rows.push({
      issue: "no active drift classes on walk ledger",
      severity: "info",
      substrateLayer: "—",
      replaySafe: "yes",
      recoverable: "yes",
      operatorAction: "Maintain scheduled twin-run replay validation.",
    });
  }
  return rows;
}

function buildProofs(s: SubstrateSignals): TraversalProofRow[] {
  const eqStatus: ReadinessDecision =
    s.replayEquivalenceConfidence === "replay_safe" || s.replayEquivalenceConfidence === "deterministic"
      ? "pass"
      : s.replayEquivalenceConfidence === "unverifiable"
        ? "fail"
        : "warn";
  return [
    {
      artifact: "OCTS-CANON-1",
      value: "walk hash bodies (canonical JSON)",
      status: "pass",
      notes: "Serialization law for traversal_hash / replay_hash inputs.",
    },
    {
      artifact: "walk_result_hash",
      value: "pinned bounded-walk receipt digest",
      status: s.replay_divergence_count > 0 ? "warn" : "pass",
      notes:
        s.replay_divergence_count > 0
          ? `${s.replay_divergence_count} walks diverged on twin-run — receipt proof lagging until replay closure.`
          : "Walk outcome digest stable on twin-run slice.",
    },
    {
      artifact: "replay proof receipts",
      value: "WRJ twin-run closure",
      status: s.replay_queue_backlog > 12 ? "warn" : "pass",
      notes: "Replay job ledger coupling: backlog delays receipt closure (operational, not semantic).",
    },
    {
      artifact: "traversal equivalence proof",
      value: `aggregate: ${s.replayEquivalenceConfidence}`,
      status: eqStatus,
      notes: "L-EQ-class parity: deterministic | replay_safe | partially_replay_safe | unverifiable | drifted.",
    },
    {
      artifact: "export legality proof",
      value: "export_sequence monotonic",
      status: s.export_sequence_mismatch_count > 0 ? "warn" : "pass",
      notes: "Constitutional chronology for walk-validity intervals.",
    },
    {
      artifact: "OCTS-CERT-PACK-1 integrity",
      value: "closure pack digest",
      status: s.unverifiable_count > 0 ? "warn" : "pass",
      notes: s.unverifiable_count > 0 ? "Certification freshness degraded by unverifiable walks on ledger." : "Static closure artifact integrity.",
    },
    {
      artifact: "corruption vectors (catalog)",
      value: "OCTS_CORRUPTION_GATE_BUNDLES_V1",
      status: "pass",
      notes: "Forbidden cognition classes mapped to doctrine gate IDs only.",
    },
    {
      artifact: "graph legality matrix",
      value: "phase-05-runtime-legality-matrix.md",
      status: "warn",
      notes: "Materialization paths remain constitutionally gated.",
    },
  ];
}

function pickForensicWalk(walks: TraversalWalk[]): TraversalWalk {
  const scored = walks.map((w) => ({
    w,
    score:
      (w.continuity_corruption ? 8 : 0) +
      (w.snapshot_closure_illegal ? 5 : 0) +
      (!w.replay_equivalent ? 4 : 0) +
      (w.legality_state === "unverifiable" ? 6 : 0),
  }));
  scored.sort((a, b) => b.score - a.score);
  return scored[0]?.w ?? walks[0]!;
}

function buildForensicLines(w: TraversalWalk): string[] {
  return [
    `walk_id: ${w.walk_id}`,
    `traversal_policy: ${w.traversal_policy}`,
    `traversal_hash: ${w.traversal_hash.slice(0, 22)}…`,
    `replay_hash: ${w.replay_hash.slice(0, 22)}…`,
    `replay_equivalent: ${String(w.replay_equivalent)} (${w.legality_state})`,
    `bounded: ${String(w.bounded)}  replay_safe: ${String(w.replay_safe)}`,
    `termination: ${w.termination_reason}  truncation: ${w.truncation_reason ?? "—"}`,
    `continuity_window: ${w.continuity_window}`,
    `export_sequence_ref: ${w.export_sequence_ref}  replay_job: ${w.replay_job_id ?? "—"}`,
    `provenance_chain_depth: ${w.provenance_chain.length}`,
    `twin flags: ordering_drift=${w.ordering_drift_twin} closure_illegal=${w.snapshot_closure_illegal} continuity_corruption=${w.continuity_corruption}`,
  ];
}

function buildRuntimeLanes(s: SubstrateSignals): RuntimeLaneRow[] {
  const projectionQueue = 2 + s.temporal_anchor_gap_count + s.continuity_corruption_count * 2;
  const walkQ = s.frontier_active_count + Math.floor(s.replay_queue_backlog * 0.6);
  const replayFailures = s.replay_divergence_count > 0 ? 1 : 0;

  return [
    {
      lane: "traversal projection build",
      status: projectionQueue > 8 ? "rebuilding" : projectionQueue > 4 ? "degraded" : "healthy",
      queue: projectionQueue,
      frontierSize: 0,
      avgLatencyMs: projectionQueue > 6 ? 1200 : 0,
      replayJobs: s.continuity_corruption_count,
      failures: s.continuity_corruption_count > 2 ? 1 : 0,
    },
    {
      lane: "bounded walk runtime",
      status: s.frontier_active_count > s.walkCount * 0.35 ? "degraded" : "healthy",
      queue: walkQ,
      frontierSize: walkQ,
      avgLatencyMs: 40 + s.replay_queue_backlog * 3,
      replayJobs: 0,
      failures: s.bounded_legality_halts > 2 ? 1 : 0,
    },
    {
      lane: "walk replay runtime",
      status: s.replay_queue_backlog > 14 ? "degraded" : s.replay_queue_backlog > 6 ? "degraded" : "healthy",
      queue: s.replay_queue_backlog,
      frontierSize: 0,
      avgLatencyMs: 400 + s.replay_queue_backlog * 40,
      replayJobs: s.replay_queue_backlog,
      failures: replayFailures,
    },
    {
      lane: "export projection runtime",
      status: s.export_sequence_mismatch_count > 0 ? "degraded" : "healthy",
      queue: s.export_sequence_mismatch_count * 2,
      frontierSize: 0,
      avgLatencyMs: 120 + s.export_sequence_mismatch_count * 50,
      replayJobs: 0,
      failures: 0,
    },
    {
      lane: "walk verification runtime",
      status: s.unverifiable_count > 0 ? "degraded" : "healthy",
      queue: 1 + (s.replay_divergence_count % 4),
      frontierSize: 0,
      avgLatencyMs: 2000 + s.replay_queue_backlog * 30,
      replayJobs: 0,
      failures: 0,
    },
  ];
}

function buildForensicByView(
  forensicWalk: TraversalWalk,
  edges: EdgeProvenance[],
  validity: Map<string, EdgeValidity>,
  chains: ExecutionCausalChain[],
  driftRows: DriftIssueRow[],
  contradictionHistogram: EdgeAggregateSignals["contradiction_histogram"],
): Record<GraphForensicView, string[]> {
  const rep = pickRepresentativeEdge(forensicWalk.walk_id, edges);
  const vv = validity.get(rep.edge_id)!;
  const sortedEdges = [...edges].sort((a, b) => a.edge_id.localeCompare(b.edge_id));

  const chainPrimary = chains[0] ? formatCausalChainLines(chains[0]) : ["(no execution causal chains)"];
  const chainSecondary =
    chains.length > 1 ? ["", "--- second template chain ---", "", ...formatCausalChainLines(chains[1]!)] : [];

  const driftOriginLines = [
    "drift_origin (walk substrate + drift table coupling)",
    ...driftRows.map(
      (d) => `${d.severity} | ${d.substrateLayer} | ${d.issue} | replay_safe=${d.replaySafe} | recoverable=${d.recoverable}`,
    ),
  ];

  const contraLines: string[] = ["contradiction_sources (deterministic counts on reconstructed edges)"];
  const histEntries = Object.entries(contradictionHistogram).sort(([a], [b]) => a.localeCompare(b)) as [
    string,
    number | undefined,
  ][];
  let histCount = 0;
  for (const [flag, count] of histEntries) {
    if (count) {
      contraLines.push(`${flag}: ${count}`);
      histCount += count;
    }
  }
  if (histCount === 0) contraLines.push("— no contradiction flags on edges in window —");
  contraLines.push("", `representative_edge ${rep.edge_id}: ${rep.contradiction_flags.join(", ") || "—"}`);

  const replayLines = [
    "replay_evidence (walk + representative edge)",
    `walk replay_equivalent: ${String(forensicWalk.replay_equivalent)} legality: ${forensicWalk.legality_state}`,
    `walk replay_job: ${forensicWalk.replay_job_id ?? "—"}`,
    `edge replay_stability: ${rep.replay_stability}`,
    `edge twin_run_equivalent: ${String(rep.twin_run_equivalent)}`,
    `ordering_drift_twin: ${String(forensicWalk.ordering_drift_twin)} truncation_mismatch_twin: ${String(forensicWalk.truncation_mismatch_twin)}`,
  ];

  const anchorLines = [
    "temporal_anchor_lineage (walk interval + edge temporal_basis)",
    `walk temporal_anchor_start: ${forensicWalk.temporal_anchor_start}`,
    `walk temporal_anchor_end: ${forensicWalk.temporal_anchor_end}`,
    `walk continuity_window: ${forensicWalk.continuity_window}`,
    `edge temporal_basis: ${rep.temporal_basis}`,
    `export_sequence_ref: ${String(forensicWalk.export_sequence_ref)}`,
  ];

  const lineageLines = [
    "walk provenance_chain (substrate lineage)",
    ...forensicWalk.provenance_chain.map((p, i) => `  [${i}] ${p}`),
  ];

  const tableLines = [
    "reconstructed_edges (sample; tab-separated)",
    "src\tdst\tvalidity\tpolicy\tconnector\treplay_stability",
    ...sortedEdges.slice(0, 8).map((e) => {
      const v = validity.get(e.edge_id)!;
      return `${e.source_node}\t${e.target_node}\t${v}\t${e.derivation_policy}\t${e.originating_connector}\t${e.replay_stability}`;
    }),
  ];

  const continuityLines = [
    "continuity_inspection (walk flags + representative edge)",
    `walk continuity_corruption: ${String(forensicWalk.continuity_corruption)}`,
    `walk snapshot_closure_illegal: ${String(forensicWalk.snapshot_closure_illegal)}`,
    `walk export_sequence_mismatch: ${String(forensicWalk.export_sequence_mismatch)}`,
    `edge continuity_status: ${rep.continuity_status}`,
    chains[0]
      ? `template_chain ${chains[0].chain_id} continuity=${chains[0].continuity_status} replay_validity=${chains[0].replay_validity}`
      : "",
  ].filter(Boolean);

  const mini = sortedEdges.slice(0, 48).map((e) => {
    const v = validity.get(e.edge_id)!;
    return v === "stable" ? "S" : v === "degraded" ? "D" : v === "replay_risky" ? "R" : "U";
  });
  const minimapLines = [
    "edge_validity_sketch_row-major (S stable D degraded R replay_risky U unverifiable)",
    mini.join(""),
    `slice_edges=${String(mini.length)} of ${String(edges.length)}`,
  ];

  const reconRoute = [
    "reconstruction_route (walk → edge hop receipts)",
    `walk_id: ${forensicWalk.walk_id}`,
    `traversal_policy: ${forensicWalk.traversal_policy}`,
    ...forensicWalk.provenance_chain.map((p, i) => `  provenance_hop_${String(i)}: ${p}`),
    `reconstructed_edge: ${rep.edge_id}`,
    `derivation_policy: ${rep.derivation_policy}  reconstruction_depth: ${String(rep.reconstruction_depth)}`,
    `artifacts: ${rep.originating_artifacts.join(", ")}`,
  ];

  return {
    path: buildForensicLines(forensicWalk),
    edge_provenance: formatEdgeProvenanceLines(rep, vv),
    causal_chain: [...chainPrimary, ...chainSecondary],
    recon_route: reconRoute,
    drift_origin: driftOriginLines,
    contradictions: contraLines,
    replay_evidence: replayLines,
    anchor_lineage: anchorLines,
    lineage: lineageLines,
    edge_table: tableLines,
    continuity: continuityLines,
    minimap: minimapLines,
  };
}

export function deriveGraphControlPlaneViewModel(tenantId: string): GraphControlPlaneViewModel {
  const seed = fnv1a32(tenantId || "default");
  const walks = buildWalks(tenantId);
  const walkSigs = computeWalkSignals(walks);
  const edges = buildReconstructedEdges(walks, tenantId);
  const validity = scoreAllEdges(edges);
  const edgeSigs = aggregateEdgeSignals(edges, validity);
  const s: SubstrateSignals = { ...walkSigs, ...edgeSigs };
  const forensicWalk = pickForensicWalk(walks);
  const chains = buildExecutionCausalChains(edges, walks, tenantId);
  const driftRows = buildDrift(s);

  return {
    snapshot: buildSnapshot(s, walks, seed),
    topology: distributeEdgesToTopologyLayers(edges, validity),
    readinessConstitutional: buildReadinessConstitutional(s),
    readinessRuntime: buildReadinessRuntime(s),
    boundedness: buildBoundedness(s, walks),
    temporalLegality: buildTemporalLegality(s),
    runtime: buildRuntimeLanes(s),
    safeOps: SAFE_OPS,
    dangerousOps: DANGEROUS_OPS,
    drift: driftRows,
    proofs: buildProofs(s),
    forensicLines: buildForensicLines(forensicWalk),
    forensicByView: buildForensicByView(forensicWalk, edges, validity, chains, driftRows, s.contradiction_histogram),
  };
}
