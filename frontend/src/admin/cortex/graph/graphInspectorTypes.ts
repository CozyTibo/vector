import type {
  SemanticGraphTruth,
  SemanticIdentityContinuity,
  SemanticReadiness,
  SemanticRetrievalProduct,
} from "../pipelineTypes";

export type GraphInspectorId =
  | "graph-truth"
  | "identity"
  | "execution-thread"
  | "island"
  | "retrieval";

export type GraphTruthEdgeTypeRow = {
  link_type: string;
  auth_edge_rows: number;
  unique_pairs: number;
  dup_factor: number | null;
  rule_count: number;
  pct_of_auth_rows: number;
  pct_of_unique_pairs: number;
  is_topology_mirror: boolean;
};

export type GraphTruthInspectorPayload = SemanticReadiness & {
  surface_kind: "graph_truth_inspector";
  inspector_schema_version?: number;
  audit_schema_version?: number;
  captured_at_utc?: string | null;
  candidates?: { total?: number; distinct_pairs?: number };
  unpromoted_candidates?: number;
  edge_type_distribution?: GraphTruthEdgeTypeRow[];
  inflation_signals?: {
    topology_mirror_link_type?: string;
    topology_mirror_row_pct?: number;
    topology_mirror_unique_pair_pct?: number;
    topology_mirror_dominates?: boolean;
    dup_factor?: number | null;
    dup_factor_severity?: string;
    unpromoted_candidates?: number;
    candidate_total?: number;
  };
  continuity_signals?: {
    cross_system_unique_pair_pct?: number;
    execution_link_type_count?: number;
    entities_in_auth_graph_pct?: number;
    entities_isolated?: number;
    promotion_rule_count?: number;
  };
  product_laws?: {
    retrieval_org_link_pct_max?: number;
    retrieval_execution_index_pct_min?: number;
    dup_factor_green_max?: number;
  };
  graph_truth: SemanticGraphTruth & {
    connected_components?: {
      component_count?: number;
      largest_component_size?: number;
      component_sizes_top_10?: number[];
      components_size_ge_2?: number;
      error?: string;
    };
  };
  identity_continuity?: SemanticIdentityContinuity | null;
  retrieval: SemanticRetrievalProduct;
};

export const GRAPH_INSPECTORS: Array<{
  id: GraphInspectorId;
  label: string;
  phase: string;
  description: string;
}> = [
  {
    id: "identity",
    label: "Identity continuity",
    phase: "G2",
    description: "Who Cortex thinks a person/entity is, with evidence and rejections.",
  },
  {
    id: "execution-thread",
    label: "Execution thread",
    phase: "G5",
    description: "How Cortex reconstructed a real execution situation over time.",
  },
  {
    id: "island",
    label: "Islands",
    phase: "G4",
    description: "Connected execution islands, scope, and recurrence.",
  },
  {
    id: "retrieval",
    label: "Retrieval reality",
    phase: "G3",
    description: "What entered retrieval and why — composition truth, not mirror spam.",
  },
  {
    id: "graph-truth",
    label: "Graph truth",
    phase: "G1",
    description: "Unique pairs, dup factor, edge-type distribution, promotion lineage.",
  },
];

export function defaultGraphInspector(): GraphInspectorId {
  return "graph-truth";
}
