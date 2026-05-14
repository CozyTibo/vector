/**
 * Deterministic reconstructed-edge provenance + execution causal chains.
 * Drives graph-truth validation (not ML): evidence, replay twin-run, contradictions.
 */

import type { RowStatus, TopologyHealthRow } from "./graphControlPlaneTypes";

/** Narrow walk shape for edge reconstruction — avoids importing `graphWalkDerivedState` (cycle). */
export interface WalkSubstrateLite {
  walk_id: string;
  traversal_policy: string;
  root_node: string;
  replay_equivalent: boolean;
  legality_state: "deterministic" | "replay_safe" | "partially_replay_safe" | "unverifiable" | "drifted";
  ordering_drift_twin: boolean;
  snapshot_closure_illegal: boolean;
  continuity_corruption: boolean;
  export_sequence_mismatch: boolean;
  truncation_mismatch_twin: boolean;
  provenance_chain: string[];
  temporal_anchor_start: string;
  temporal_anchor_end: string;
  continuity_window: string;
}

export type OriginatingConnector = "slack" | "github" | "linear" | "call_transcript" | "notion";

export type DerivationPolicy =
  | "temporal_cooccurrence"
  | "ownership_resolution"
  | "execution_reference"
  | "dependency_inference"
  | "replay_projection"
  | "continuity_reconstruction";

export type ReplayStabilityLabel = "stable" | "partially_stable" | "divergent" | "unverifiable";

export type ContinuityEdgeStatus = "continuity_preserved" | "continuity_gap" | "replay_conflict";

export type EvidenceQualityClass = "direct" | "multi_source" | "inferred" | "weak";

export type ContradictionFlag =
  | "ownership_conflict"
  | "chronology_conflict"
  | "replay_hash_mismatch"
  | "temporal_anchor_gap";

export type EdgeValidity = "stable" | "degraded" | "replay_risky" | "unverifiable";

export interface EdgeProvenance {
  edge_id: string;
  edge_type: "continuity_ledger" | "execution_reference" | "temporal_cooccurrence" | "replay_projection" | "dependency_bridge";
  source_node: string;
  target_node: string;
  originating_connector: OriginatingConnector;
  originating_artifacts: string[];
  derivation_policy: DerivationPolicy;
  evidence_summary: string;
  temporal_basis: string;
  replay_stability: ReplayStabilityLabel;
  continuity_status: ContinuityEdgeStatus;
  confidence_class: EvidenceQualityClass;
  reconstruction_depth: number;
  twin_run_equivalent: boolean;
  contradiction_flags: ContradictionFlag[];
  /** Walk ledger row this edge was reconstructed from (substrate coupling). */
  source_walk_id: string;
}

export interface ExecutionChainStep {
  artifact: string;
  timestamp_iso: string;
  connector: OriginatingConnector;
  action_type: string;
  causality_basis: string;
  replay_safe: boolean;
  continuity_preserved: boolean;
}

export interface ExecutionCausalChain {
  chain_id: string;
  root_event: string;
  chain_steps: ExecutionChainStep[];
  continuity_status: ContinuityEdgeStatus;
  replay_validity: EdgeValidity;
  export_validity: "ok" | "degraded" | "fail";
  chronology_validity: "ok" | "degraded" | "fail";
  /** Deterministic evidence density for the chain (not ML). */
  reconstruction_confidence: EvidenceQualityClass;
  broken_links: string[];
  drift_sources: string[];
}

function fnv1a32(input: string): number {
  let h = 2166136261;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

const CONNECTORS: OriginatingConnector[] = ["slack", "github", "linear", "call_transcript", "notion"];
const POLICIES: DerivationPolicy[] = [
  "temporal_cooccurrence",
  "ownership_resolution",
  "execution_reference",
  "dependency_inference",
  "replay_projection",
  "continuity_reconstruction",
];

const EDGE_TYPES: EdgeProvenance["edge_type"][] = [
  "continuity_ledger",
  "execution_reference",
  "temporal_cooccurrence",
  "replay_projection",
  "dependency_bridge",
];

export function deriveEdgeValidity(e: EdgeProvenance): EdgeValidity {
  const hasContra = e.contradiction_flags.length > 0;
  const hard = e.contradiction_flags.some((c) => c === "replay_hash_mismatch" || c === "temporal_anchor_gap");
  if (e.confidence_class === "weak" && (hasContra || e.replay_stability === "unverifiable")) return "unverifiable";
  if (e.replay_stability === "divergent" || hard) return "replay_risky";
  if (e.continuity_status !== "continuity_preserved" || e.replay_stability === "partially_stable" || hasContra)
    return "degraded";
  if (
    e.confidence_class === "direct" &&
    e.replay_stability === "stable" &&
    e.continuity_status === "continuity_preserved" &&
    e.twin_run_equivalent
  )
    return "stable";
  if (e.confidence_class === "inferred" && e.replay_stability === "stable") return "degraded";
  return "degraded";
}

function buildArtifacts(connector: OriginatingConnector, i: number, seed: number): string[] {
  const h = shortId(seed, i);
  switch (connector) {
    case "slack":
      return [`slack_message:${h}`, `slack_thread:${h.slice(0, 6)}`];
    case "github":
      return [`github_pr:${1000 + (i % 9000)}`, `github_commit:${h}`];
    case "linear":
      return [`linear_issue:LIN-${(i % 9999).toString().padStart(4, "0")}`];
    case "call_transcript":
      return [`call_segment:${h}`, `transcript_anchor:${i}`];
    default:
      return [`notion_page:${h}`, `notion_task_ref:${i}`];
  }
}

function shortId(seed: number, i: number): string {
  return (fnv1a32(`${seed}|edge|${i}`) >>> 0).toString(16).slice(0, 10);
}

export function buildReconstructedEdges(walks: WalkSubstrateLite[], tenantId: string): EdgeProvenance[] {
  const seed = fnv1a32(tenantId || "default");
  const slug = tenantId.replace(/[^a-z0-9]/gi, "").slice(0, 8) || "tenant";
  const n = Math.min(72, walks.length * 2);
  const edges: EdgeProvenance[] = [];

  for (let i = 0; i < n; i++) {
    const w = walks[i % walks.length]!;
    const connector = CONNECTORS[(seed + i * 7) % CONNECTORS.length]!;
    const policy = POLICIES[(seed + i * 5) % POLICIES.length]!;
    const edgeType = EDGE_TYPES[(seed + i * 3) % EDGE_TYPES.length]!;
    const tgt = `org-node:${((seed + i * 11) % 99_991) + 1}`;
    const depth = 1 + ((seed + i) % 4);
    const artifacts = buildArtifacts(connector, i, seed);

    const contradiction_flags: ContradictionFlag[] = [];
    if (w.continuity_corruption) contradiction_flags.push("ownership_conflict");
    if (w.snapshot_closure_illegal) contradiction_flags.push("temporal_anchor_gap");
    if (!w.replay_equivalent) contradiction_flags.push("replay_hash_mismatch");
    if (w.export_sequence_mismatch) contradiction_flags.push("chronology_conflict");

    let replay_stability: ReplayStabilityLabel = "stable";
    if (w.legality_state === "unverifiable") replay_stability = "unverifiable";
    else if (!w.replay_equivalent) replay_stability = "divergent";
    else if (w.ordering_drift_twin || w.truncation_mismatch_twin) replay_stability = "partially_stable";

    let continuity_status: ContinuityEdgeStatus = "continuity_preserved";
    if (w.continuity_corruption) continuity_status = "replay_conflict";
    else if (w.snapshot_closure_illegal) continuity_status = "continuity_gap";

    let confidence: EvidenceQualityClass = "direct";
    if (artifacts.length >= 2 && (seed + i) % 4 === 0) confidence = "multi_source";
    else if (policy === "dependency_inference" || policy === "temporal_cooccurrence") confidence = "inferred";
    if (contradiction_flags.length > 0 && confidence === "direct") confidence = "weak";

    const twin = w.replay_equivalent && contradiction_flags.length === 0 && replay_stability === "stable";

    const evidence_summary =
      policy === "replay_projection"
        ? `Edge replay-projected from ${w.walk_id} under ${w.traversal_policy}.`
        : `${policy} link: ${connector} artifacts bind ${w.root_node}→${tgt}.`;

    const temporal_basis =
      w.snapshot_closure_illegal
        ? "export continuity chain broken vs walk anchor window"
        : w.export_sequence_mismatch
          ? "bounded walk overlap with export_sequence skew"
          : "active execution window within half-open anchor interval";

    edges.push({
      edge_id: `edg-${slug}-${i.toString(16).padStart(3, "0")}`,
      edge_type: edgeType,
      source_node: w.root_node,
      target_node: tgt,
      originating_connector: connector,
      originating_artifacts: artifacts,
      derivation_policy: policy,
      evidence_summary,
      temporal_basis,
      replay_stability,
      continuity_status,
      confidence_class: confidence,
      reconstruction_depth: depth,
      twin_run_equivalent: twin,
      contradiction_flags,
      source_walk_id: w.walk_id,
    });
  }
  return edges;
}

export function scoreAllEdges(edges: EdgeProvenance[]): Map<string, EdgeValidity> {
  const m = new Map<string, EdgeValidity>();
  for (const e of edges) m.set(e.edge_id, deriveEdgeValidity(e));
  return m;
}

export interface EdgeAggregateSignals {
  edge_total: number;
  edge_validity_stable: number;
  edge_validity_degraded: number;
  edge_validity_replay_risky: number;
  edge_validity_unverifiable: number;
  edges_with_contradictions: number;
  unstable_edge_count: number;
  causal_chain_breakpoints: number;
  /** Per contradiction class */
  contradiction_histogram: Partial<Record<ContradictionFlag, number>>;
  /** Edges by derivation_policy — weak reconstruction policies. */
  policy_weak_edges: number;
}

export function aggregateEdgeSignals(edges: EdgeProvenance[], validity: Map<string, EdgeValidity>): EdgeAggregateSignals {
  let stable = 0,
    degraded = 0,
    replay_risky = 0,
    unverifiable = 0;
  let withContra = 0;
  const hist: Partial<Record<ContradictionFlag, number>> = {};
  let policyWeak = 0;

  for (const e of edges) {
    const v = validity.get(e.edge_id)!;
    if (v === "stable") stable++;
    else if (v === "degraded") degraded++;
    else if (v === "replay_risky") replay_risky++;
    else unverifiable++;
    if (e.contradiction_flags.length) withContra++;
    for (const c of e.contradiction_flags) hist[c] = (hist[c] ?? 0) + 1;
    if (e.derivation_policy === "dependency_inference" || e.derivation_policy === "temporal_cooccurrence")
      policyWeak++;
  }

  const unstable = edges.length - stable;

  return {
    edge_total: edges.length,
    edge_validity_stable: stable,
    edge_validity_degraded: degraded,
    edge_validity_replay_risky: replay_risky,
    edge_validity_unverifiable: unverifiable,
    edges_with_contradictions: withContra,
    unstable_edge_count: unstable,
    causal_chain_breakpoints: Math.floor(withContra / 2) + replay_risky,
    contradiction_histogram: hist,
    policy_weak_edges: policyWeak,
  };
}

export function buildExecutionCausalChains(
  edges: EdgeProvenance[],
  walks: WalkSubstrateLite[],
  tenantId: string,
): ExecutionCausalChain[] {
  const seed = fnv1a32(`${tenantId}|chains`);
  const slug = tenantId.replace(/[^a-z0-9]/gi, "").slice(0, 6) || "tn";

  const templates: Array<{ root: string; actions: string[] }> = [
    {
      root: "customer_escalation",
      actions: ["slack_escalation_thread", "ownership_reassignment", "pr_creation", "deployment_block", "release_delay"],
    },
    {
      root: "incident_opened",
      actions: ["investigation_thread", "rollback_pr", "hotfix_deploy", "postmortem_task"],
    },
    {
      root: "scope_change_request",
      actions: ["linear_issue_link", "github_pr_dependency", "notion_spec_anchor", "release_gate"],
    },
  ];

  const driftedWalks = walks.filter((w) => !w.replay_equivalent || w.continuity_corruption);
  const driftSource =
    driftedWalks.length > 0
      ? `walk_substrate:${driftedWalks[0]!.walk_id}`
      : "no_walk_drift_in_window";

  return templates.map((tpl, ci) => {
    const steps: ExecutionChainStep[] = tpl.actions.map((act, si) => {
      const connector = CONNECTORS[(seed + ci * 17 + si) % CONNECTORS.length]!;
      const w = walks[(seed + ci + si) % walks.length]!;
      return {
        artifact: `${act}:${slug}-${ci}-${si}`,
        timestamp_iso: isoOffset(seed, ci * 10 + si),
        connector,
        action_type: act,
        causality_basis:
          si === 0
            ? "root_event_export_anchor"
            : `${tpl.actions[si - 1]!}→${act}:execution_reference_under_replay_projection`,
        replay_safe: w.replay_equivalent && !w.continuity_corruption,
        continuity_preserved: !w.continuity_corruption && !w.snapshot_closure_illegal,
      };
    });

    const broken: string[] = [];
    const drift_sources: string[] = [];
    if (edges.some((e) => e.contradiction_flags.includes("replay_hash_mismatch"))) {
      broken.push("step:pr_creation→deployment_block (twin-run replay_hash divergence)");
      drift_sources.push("replay_lane:walk_replay_runtime");
    }
    if (edges.some((e) => e.contradiction_flags.includes("temporal_anchor_gap"))) {
      broken.push("export_interval_closure_vs_walk_window");
      drift_sources.push(driftSource);
    }

    let continuity: ContinuityEdgeStatus = "continuity_preserved";
    if (broken.length > 1) continuity = "replay_conflict";
    else if (broken.length === 1) continuity = "continuity_gap";

    let replay_validity: EdgeValidity = "stable";
    if (drift_sources.length > 1) replay_validity = "replay_risky";
    else if (broken.length > 0) replay_validity = "degraded";

    let export_validity: ExecutionCausalChain["export_validity"] = "ok";
    if (edges.some((e) => e.contradiction_flags.includes("chronology_conflict"))) export_validity = "degraded";

    let chronology_validity: ExecutionCausalChain["chronology_validity"] = "ok";
    if (edges.some((e) => e.contradiction_flags.includes("temporal_anchor_gap"))) chronology_validity = "degraded";

    let reconstruction_confidence: EvidenceQualityClass = "multi_source";
    if (broken.length > 0) reconstruction_confidence = "inferred";
    if (replay_validity === "replay_risky") reconstruction_confidence = "weak";

    return {
      chain_id: `xchain-${slug}-${ci}`,
      root_event: tpl.root,
      chain_steps: steps,
      continuity_status: continuity,
      replay_validity,
      export_validity,
      chronology_validity,
      reconstruction_confidence,
      broken_links: broken,
      drift_sources,
    };
  });
}

function isoOffset(seed: number, step: number): string {
  const day = 1 + ((seed + step) % 27);
  const h = 8 + ((seed >> 2) + step) % 12;
  const m = (seed + step * 3) % 60;
  return `2026-05-${String(day).padStart(2, "0")}T${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:00Z`;
}

export function formatEdgeProvenanceLines(e: EdgeProvenance, validity: EdgeValidity): string[] {
  return [
    `edge_id: ${e.edge_id}`,
    `edge_type: ${e.edge_type}`,
    `source→target: ${e.source_node} → ${e.target_node}`,
    `connector: ${e.originating_connector}  policy: ${e.derivation_policy}`,
    `artifacts: ${e.originating_artifacts.join(", ")}`,
    `evidence: ${e.evidence_summary}`,
    `temporal_basis: ${e.temporal_basis}`,
    `replay_stability: ${e.replay_stability}  continuity: ${e.continuity_status}`,
    `evidence_class: ${e.confidence_class}  recon_depth: ${e.reconstruction_depth}`,
    `twin_run_equivalent: ${String(e.twin_run_equivalent)}`,
    `edge_validity: ${validity}`,
    `contradictions: ${e.contradiction_flags.length ? e.contradiction_flags.join(", ") : "—"}`,
    `source_walk: ${e.source_walk_id}`,
  ];
}

export function formatCausalChainLines(c: ExecutionCausalChain): string[] {
  const lines = [
    `chain_id: ${c.chain_id}`,
    `root_event: ${c.root_event}`,
    `continuity: ${c.continuity_status}  replay_validity: ${c.replay_validity}`,
    `export_validity: ${c.export_validity}  chronology_validity: ${c.chronology_validity}`,
    `reconstruction_confidence: ${c.reconstruction_confidence}`,
    `broken_links: ${c.broken_links.length ? c.broken_links.join(" | ") : "—"}`,
    `drift_sources: ${c.drift_sources.length ? c.drift_sources.join(" | ") : "—"}`,
    "steps:",
  ];
  for (let i = 0; i < c.chain_steps.length; i++) {
    const s = c.chain_steps[i]!;
    lines.push(
      `  ${i + 1}. [${s.connector}] ${s.action_type} @ ${s.timestamp_iso}  replay_safe=${s.replay_safe} continuity=${s.continuity_preserved}`,
    );
    lines.push(`      artifact=${s.artifact}  basis=${s.causality_basis}`);
  }
  return lines;
}

export function pickRepresentativeEdge(walkId: string, edges: EdgeProvenance[]): EdgeProvenance {
  const byWalk = edges.filter((e) => e.source_walk_id === walkId);
  if (byWalk.length) return byWalk[fnv1a32(walkId) % byWalk.length]!;
  const flagged = edges.filter((e) => e.contradiction_flags.length > 0);
  if (flagged.length) return flagged[fnv1a32(`${walkId}|flag`) % flagged.length]!;
  return edges[0]!;
}

export function distributeEdgesToTopologyLayers(
  edges: EdgeProvenance[],
  validity: Map<string, EdgeValidity>,
): TopologyHealthRow[] {
  const layerNames = [
    "canonical continuity graph",
    "identity continuity graph",
    "provenance graph",
    "replay lineage graph",
    "traversal projection graph",
    "temporal ordering graph",
    "export projection graph",
  ];
  const layerIndex = (e: EdgeProvenance): number => {
    if (e.edge_type === "continuity_ledger") return 0;
    if (e.edge_type === "execution_reference") return 1;
    // Export / closure chain (policy), excluding ledger rows already classified above.
    if (e.derivation_policy === "continuity_reconstruction") return 6;
    if (e.edge_type === "dependency_bridge") return 4;
    if (e.edge_type === "replay_projection") return 3;
    if (e.edge_type === "temporal_cooccurrence") return 5;
    return 2;
  };

  const buckets = layerNames.map(() => ({
    backed: 0,
    unstable: 0,
    contra: 0,
    gaps: 0,
    weak: 0,
  }));

  for (const e of edges) {
    const li = layerIndex(e);
    const b = buckets[li]!;
    b.backed++;
    const v = validity.get(e.edge_id)!;
    if (v !== "stable") b.unstable++;
    if (e.contradiction_flags.length) b.contra++;
    if (e.continuity_status !== "continuity_preserved") b.gaps++;
    if (e.confidence_class === "weak" || e.confidence_class === "inferred") b.weak++;
  }

  return layerNames.map((area, idx) => {
    const b = buckets[idx]!;
    let status: RowStatus = "healthy";
    if (b.unstable > b.backed * 0.35) status = "degraded";
    if (b.contra > b.backed * 0.2) status = "degraded";
    if (area.includes("replay") && b.unstable > 8) status = "rebuilding";
    if (b.contra > b.backed * 0.45) status = "blocked";
    return {
      area,
      evidenceBackedEdges: b.backed,
      unstableEdges: b.unstable,
      contradictionIncidents: b.contra,
      continuityGaps: b.gaps,
      weakProvenanceEdges: b.weak,
      traversalStatus: status,
    };
  });
}
