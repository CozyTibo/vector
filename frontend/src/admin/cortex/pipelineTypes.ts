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
  state: "AUTONOMOUS" | "DEGRADED" | "OPERATOR_RECOVERY" | "STALLED" | "BROKEN";
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

export type OperatorPrimaryKpiIsland = {
  island_scope_id: string;
  entity_count: number;
  authoritative_edge_count: number;
  last_retrieval_epoch?: string | null;
  last_walk_at?: string | null;
};

export type DeferralOmissionPosture = {
  surface_kind?: string;
  schema_version?: number;
  enabled?: boolean;
  runbook_path?: string;
  omission_class?: string;
  posture?: string;
  permanent_orphan_count?: number;
  deferral_total?: number;
  deferred_retry_ready?: number;
  permanent_share_pct?: number;
  chase_zero_deferrals_forbidden?: boolean;
  is_bounded_omission_not_failure?: boolean;
  fizzer_reference_count?: number;
  headline?: string;
  summary?: string;
  operator_actions?: string[];
};

export type PromotionByRuleRow = {
  rule_id: string;
  auth_edge_rows: number;
  unique_pairs: number;
};

export type SemanticGraphTruth = {
  active_entities: number;
  entities_in_auth_graph: number;
  entities_isolated: number;
  entities_in_auth_graph_pct: number;
  auth_edge_rows: number;
  auth_edge_rows_deprecated_primary?: boolean;
  unique_auth_pairs: number;
  dup_factor: number | null;
  dup_factor_severity: "ok" | "warn" | "bad" | "unknown";
  promotion_rule_count: number;
  promotions_by_rule_id: PromotionByRuleRow[];
  primary_metric_key: string;
};

export type SemanticRetrievalProduct = {
  published_index_epoch: string | null;
  entry_count: number;
  org_link_pct: number | null;
  execution_index_pct: number | null;
  freshness_minutes: number | null;
  freshness_minutes_severity?: "ok" | "bad" | "unknown";
  freshness_green_minutes?: number;
  org_link_pct_severity?: "ok" | "bad" | "unknown";
  execution_index_pct_severity?: "ok" | "bad" | "unknown";
  index_kind_counts?: Array<{ index_kind: string; count: number }>;
};

export type SemanticSynthesisTruth = {
  artifacts_with_claims: number;
  artifacts_published: number;
  artifacts_total: number;
  published_claims_7d?: number;
  published_claims_7d_severity?: "ok" | "bad" | "unknown";
  published_claims_7d_green_min?: number;
  jobs_by_status?: Array<{ status: string; count: number }>;
};

export type SemanticIdentityContinuity = {
  anchor_boundary?: {
    anchor_count?: number;
    anchors_missing_org_entity?: number;
    anchors_missing_org_entity_pct?: number | null;
  };
  candidate_rows?: number;
  distinct_candidate_pairs?: number;
  candidate_inflation_ratio?: number | null;
  candidate_inflation_severity?: "ok" | "warn" | "bad" | "unknown";
  anchors_missing_org_entity_pct?: number | null;
  anchors_missing_severity?: "ok" | "warn" | "bad" | "unknown";
  promotable_by_rule_id?: Array<{ rule_id: string; promotable_count: number }>;
  second_link_type_policy?: string;
};

export type SemanticOperatorMetric = {
  key: string;
  label: string;
  value?: number | string | null;
  severity?: "ok" | "warn" | "bad" | "unknown";
  green_rule?: string | null;
};

export type SemanticReadiness = {
  surface_kind?: string;
  schema_version?: number;
  tenant_id: string;
  product_substrate: string;
  graph_truth: SemanticGraphTruth;
  identity_continuity?: SemanticIdentityContinuity | null;
  retrieval: SemanticRetrievalProduct;
  synthesis: SemanticSynthesisTruth;
  semantic_operator_panel?: SemanticOperatorMetric[];
  thresholds?: Record<string, number>;
};

export type OperatorPrimaryKpi = {
  surface_kind?: string;
  schema_version?: number;
  primary_metric_key: string;
  primary_metric_value: number;
  drainable_routable_estimate: number;
  untreated_routable_estimate: number;
  raw_minus_mat_admin_gap: number;
  raw_minus_mat_banner_deprecated?: boolean;
  execution_island_count?: number;
  execution_island_registry_enabled?: boolean;
  execution_islands: OperatorPrimaryKpiIsland[];
  deferral_counts?: Record<string, number>;
  deferral_omission?: DeferralOmissionPosture | null;
  semantic_primary_active?: boolean;
  hide_from_overview?: boolean;
};

export type PipelineOverview = {
  tenant_id: string;
  operator_primary_kpi?: OperatorPrimaryKpi | null;
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
