import { Fragment, useState } from "react";
import type { ReactNode } from "react";
import { flushSync } from "react-dom";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { adminJson } from "../lib/adminFetch";

/**
 * §6 micro-steps in `DOCS/v0/manager_insights_master_implementation_plan.md`.
 * Bump `stepsDone` when coordination checklist items ship.
 */
const COORDINATION_SECTION6 = { stepsDone: 42, stepsTotal: 46 } as const;

/** Orchestrator / fetch-debug internal stages (not §6 step numbers — those are the coordination checklist). */
const PIPELINE = {
  p05: "P0.5",
  p1: "P1",
  p2: "P2",
  p3: "P3",
  p4: "P4",
  p5: "P5",
  p55: "P5.5",
  p56: "P5.6",
  p6: "P6",
  p7: "P7",
  p8: "P8",
} as const;

/**
 * §6 Step 4 — Type parity with `vector.contracts.manager_insights_activity` for `fetch-debug` JSON.
 * Keep literal unions aligned when Python `Literal` enums change.
 */
type ManagerInsightConnector = "slack" | "github" | "linear" | "notion" | "calls";

type WorkItemType = "issue" | "pull_request" | "document" | "call" | "message_thread";

type GapType =
  | "expected_not_executed"
  | "discussed_not_linked_to_work"
  | "blocker_not_tracked"
  | "doc_not_connected_to_execution";

type CoordinationDecisionType =
  | "LINK_OR_CLOSE_COMMITMENT"
  | "THREAD_TO_TRACKING_LINK"
  | "BLOCKER_ESCALATION"
  | "DOC_EXECUTION_BRIDGE"
  | "HOLD_START"
  | "CLARIFY_SPEC"
  | "RECENTER"
  | "PAUSE_INVESTMENT";

type DecisionLifecycleStatus = "proposed" | "accepted" | "dismissed" | "completed" | "failed";

type OutcomeType =
  | "applied_success"
  | "applied_partial"
  | "apply_failed"
  | "dismissed"
  | "ignored"
  | "superseded";

type ReliabilityTier = "high" | "medium" | "low";

type ConnectorReliabilityDetail = {
  tier: ReliabilityTier;
  reasons: string[];
  metrics?: Record<string, number>;
};

type DataReliabilityReport = {
  slack: ConnectorReliabilityDetail;
  github: ConnectorReliabilityDetail;
  linear: ConnectorReliabilityDetail;
  notion: ConnectorReliabilityDetail;
  calls: ConnectorReliabilityDetail;
  overall_confidence: ReliabilityTier;
};

type ConnectorFetchResult = {
  connector: ManagerInsightConnector;
  status: string;
  fetched_at: string | null;
  window_start: string;
  window_end: string;
  caps_applied: string[];
  errors: string[];
  coverage?: Record<string, number>;
  completeness?: Record<string, number>;
  payload: Record<string, unknown>;
};

type FetchActivityBundle = {
  run_id: string;
  tenant_id: string;
  window_days: number;
  connectors: Record<string, ConnectorFetchResult>;
};

type CoordinationDecisionItemExample = {
  id: string;
  gap_id: string;
  gap_type: GapType;
  decision_type: CoordinationDecisionType;
  title: string;
  rationale: string;
  default_action: {
    kind: string;
    connector: ManagerInsightConnector | null;
    payload_template: Record<string, unknown>;
  };
  required_inputs: Record<string, unknown>;
  evidence_refs: string[];
  signal_refs: string[];
  created_at: string;
  run_id: string;
  status?: DecisionLifecycleStatus | null;
};

type DecisionEmissionTraceDebugExample = {
  evaluated: boolean;
  inputs_complete: boolean;
  ambiguity_signal_high: boolean;
  cluster_hops_used: number;
  seed_work_item_ids: string[];
  cluster_work_item_ids: string[];
  open_execution_work_item_ids: string[];
  open_execution_count: number;
  affected_wi_threshold: number;
  decision_evidence_ids_in_cluster: string[];
  guard_ambiguity_ok: boolean;
  guard_no_decision_evidence_in_cluster_ok: boolean;
  guard_open_execution_count_ok: boolean;
  hold_start_emitted: boolean;
  reason: string;
};

type CoordinationDecisionBundleExample = {
  run_id: string;
  tenant_id: string;
  window_days: number;
  items: Array<{
    decision: CoordinationDecisionItemExample;
    decision_debug: {
      gap_id: string;
      matched_rule: string;
      conditions_met: Record<string, boolean>;
    } | null;
    decision_emission_debug: DecisionEmissionTraceDebugExample | null;
  }>;
};

type CoordinationOutcomeItemExample = {
  id: string;
  decision_id: string;
  tenant_id: string;
  observed_at: string;
  outcome_type: OutcomeType;
  user_attribution: string | null;
  receipt: Record<string, unknown> | null;
  false_positive: boolean | null;
  ground_truth: Record<string, unknown>;
};

/** §6 Step 6 — echoed env flags; mirrors `ManagerInsightsCoordinationSettingsDebug`. */
type ManagerInsightsCoordinationSettingsDebug = {
  perception_llm: boolean;
  include_execution_graph: boolean;
  skip_narrative_steps: boolean;
  /** §6 Step 18 — merge execution graph into gap adjacency. */
  gaps_use_graph: boolean;
  /** §6 Step 26 — emit HOLD_START only if open execution count in cluster &gt; this value. */
  hold_start_affected_wi_threshold: number;
  /** §6 Step 28 — default cap for `decisions_prioritized` before optional `?max_decisions=`. */
  max_decisions_surfaced: number;
};

/** §6 Step 11 — mirrors `ManagerInsightPerceptionQaDebug` on fetch-debug. */
type PerceptionEvidencePath = "regex_evidence_only" | "llm_perception_plus_regex_evidence";

type ManagerInsightPerceptionQaDebug = {
  evidence_path: PerceptionEvidencePath;
  query_perception_regex: boolean;
  query_include_execution_graph: boolean;
  /** True when fetch used ?master_plan_debug=1 (request-scoped coordination LLM + graph + gaps merge). */
  query_master_plan_debug: boolean;
  /** §6 Step 28 — set when the request included `?max_decisions=`; else null. */
  query_max_decisions: number | null;
  /** §6 Step 28 — applied cap after Step 27 sort. */
  max_decisions_cap_applied: number;
  /** §6 Step 28 — full prioritized length before truncation. */
  decisions_prioritized_full_count: number;
  /** §6 Step 32 — true when fetch used `?persist_decisions=1`. */
  query_persist_decisions: boolean;
  /** §6 Step 35 — true when fetch used `?skip_interpretations=1` (P7 bundle empty, generator not run). */
  query_skip_interpretations: boolean;
  /** §6 Step 35 — true when fetch used `?skip_insights=1` (P8 bundle empty, generator not run). */
  query_skip_insights: boolean;
  /** §6 Step 42 — per gap_type demotion totals applied in prioritize_decisions (empty when none). */
  step42_gap_demotion_by_gap_type: Record<string, number>;
};

/** §6 Step 15 — JSON shape when Step 16 attaches `execution_graph` (mirrors `ExecutionGraph`). */
type ExecutionGraphPayload = {
  run_id?: string;
  tenant_id?: string;
  window_days?: number;
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
  unresolved_dependency_refs: string[];
};

function isRecord(v: unknown): v is Record<string, unknown> {
  return v !== null && typeof v === "object" && !Array.isArray(v);
}

/** §6 Step 33 — one row from `GET .../manager-insight/decisions`. */
type ManagerInsightPersistedDecisionApiItem = {
  id: string;
  tenant_id: string;
  run_id: string;
  gap_id: string;
  gap_type: string;
  decision_type: string;
  title: string;
  rationale: string;
  default_action: Record<string, unknown>;
  required_inputs: Record<string, unknown>;
  evidence_refs: string[];
  signal_refs: string[];
  status: string;
  rank: number | null;
  slack_channel_id: string | null;
  slack_message_ts: string | null;
  idempotency_key: string | null;
  receipt: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};

/** §6 Step 33 — paginated list from PostgreSQL. */
type ManagerInsightPersistedDecisionsListResponse = {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  items: ManagerInsightPersistedDecisionApiItem[];
};

/** §6 Step 39 — one row from `GET .../manager-insight/outcomes`. */
type ManagerInsightPersistedOutcomeApiItem = {
  id: string;
  decision_id: string;
  tenant_id: string;
  observed_at: string;
  outcome_type: string;
  false_positive: boolean | null;
  ground_truth: Record<string, unknown>;
  user_attribution: string | null;
};

/** §6 Step 39 — paginated list from PostgreSQL. */
type ManagerInsightPersistedOutcomesListResponse = {
  tenant_id: string;
  total: number;
  limit: number;
  offset: number;
  items: ManagerInsightPersistedOutcomeApiItem[];
};

/** §6 Step 37 — `POST .../manager-insight/decisions/{id}/apply` with `{ dry_run: true }`. */
type ManagerInsightApplyDryRunResponse = {
  dry_run: true;
  tenant_id: string;
  decision_id: string;
  run_id: string;
  gap_id: string;
  decision_type: string;
  title: string;
  decision_status: string;
  default_action: Record<string, unknown>;
  planned_payload: Record<string, unknown>;
  note: string;
};

/** §6 Step 38 — same POST with `{ dry_run: false }` when API flag allows live apply. */
type ManagerInsightApplyLiveResponse = {
  dry_run: false;
  tenant_id: string;
  decision_id: string;
  run_id: string;
  gap_id: string;
  decision_type: string;
  title: string;
  decision_status: string;
  default_action: Record<string, unknown>;
  planned_payload: Record<string, unknown>;
  receipt: Record<string, unknown>;
  note: string;
};

/** §6 Step 40 — `POST .../manager-insight/decisions/{id}/dismiss`. */
type ManagerInsightDismissDecisionResponse = {
  tenant_id: string;
  decision_id: string;
  decision_status: string;
  idempotent: boolean;
  outcome: ManagerInsightPersistedOutcomeApiItem;
};

/** §6 Step 41 — `POST .../manager-insight/evaluate-outcomes`. */
type ManagerInsightEvaluateOutcomeItemResult = {
  outcome_id: string;
  decision_id: string;
  rules_applied: string[];
  ground_truth_before: Record<string, unknown>;
  ground_truth_after: Record<string, unknown>;
};

type ManagerInsightEvaluateOutcomesResponse = {
  tenant_id: string;
  processed: number;
  skipped: number;
  scanned: number;
  items: ManagerInsightEvaluateOutcomeItemResult[];
};

/** §6 Step 17 — normalize fetch-debug `execution_graph` for tables (tolerates partial/legacy shapes). */
function parseExecutionGraphPayload(raw: Record<string, unknown> | null): ExecutionGraphPayload | null {
  if (raw === null) {
    return null;
  }
  const nodes = Array.isArray(raw.nodes) ? raw.nodes.filter(isRecord) : [];
  const edges = Array.isArray(raw.edges) ? raw.edges.filter(isRecord) : [];
  const ur = raw.unresolved_dependency_refs;
  const unresolved = Array.isArray(ur)
    ? ur.filter((x): x is string => typeof x === "string")
    : [];
  return {
    run_id: typeof raw.run_id === "string" ? raw.run_id : undefined,
    tenant_id: typeof raw.tenant_id === "string" ? raw.tenant_id : undefined,
    window_days: typeof raw.window_days === "number" ? raw.window_days : undefined,
    nodes,
    edges,
    unresolved_dependency_refs: unresolved,
  };
}

function displayCell(v: unknown): string {
  if (v === null || v === undefined) {
    return "—";
  }
  if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") {
    return String(v);
  }
  return JSON.stringify(v);
}

/** §6 Steps 33–34 — parse list query inputs for pagination math. */
function parsePersistedListLimit(raw: string): number {
  const n = Number.parseInt(raw.trim(), 10);
  return Number.isNaN(n) ? 50 : Math.min(200, Math.max(1, n));
}

function parsePersistedListOffset(raw: string): number {
  const n = Number.parseInt(raw.trim(), 10);
  return Number.isNaN(n) ? 0 : Math.max(0, n);
}

function copyTextToClipboard(text: string): void {
  void navigator.clipboard?.writeText(text);
}

function CopyJsonButton(props: { label: string; value: unknown; "data-testid"?: string }) {
  const { label, value, "data-testid": testId } = props;
  const text = JSON.stringify(value, null, 2);
  return (
    <button
      type="button"
      className="rounded border border-stone-300 bg-white px-2 py-1 text-[11px] font-medium text-stone-800 shadow-sm hover:bg-stone-50"
      data-testid={testId}
      onClick={() => {
        copyTextToClipboard(text);
      }}
    >
      {label}
    </button>
  );
}

/** Last `offset` for pagination (aligned with server limit). */
function lastPageOffset(total: number, lim: number): number {
  if (total <= 0) {
    return 0;
  }
  return Math.max(0, Math.floor((total - 1) / lim) * lim);
}

/** §6 Step 7 — execution-state perception row; mirrors `PerceptionRow` (separate from regex `EvidenceItem`). */
type ExecutionStatePerception = "not_started" | "in_progress" | "blocked" | "waiting" | "done";

type PerceptionRowKind = "action_item" | "blocker" | "decision" | "risk" | "ambiguity" | "ownership_hint";

type PerceptionStateTransition = {
  from_state?: ExecutionStatePerception | null;
  to_state: ExecutionStatePerception;
  quote: string;
};

type PerceptionOwnershipInferred = {
  text_span: string;
  role_guess?: string | null;
};

type CoordinationPerceptionRowExample = {
  id: string;
  work_item_id: string;
  kind: PerceptionRowKind;
  statement: string;
  quote: string;
  execution_state?: ExecutionStatePerception | null;
  state_transition?: PerceptionStateTransition | null;
  waits_on?: string[];
  blocked_by?: string[];
  commitment_strength?: "weak" | "medium" | "strong" | null;
  ambiguity_class?: "unclear_scope" | "discussion_loop" | "contradiction" | null;
  ambiguity_quote?: string | null;
  contradiction_pair_id?: string | null;
  ownership_inferred?: PerceptionOwnershipInferred | null;
};

/** §6 Step 8 — mirrors `PerceptionValidationDemoDebug` (validate_perception_rows demo output). */
type PerceptionValidationDemoDebug = {
  demo_work_item_id: string;
  input_row_count: number;
  accepted: CoordinationPerceptionRowExample[];
  rejected: Array<{ index: number; reason: string; raw: Record<string, unknown> }>;
};

/** §6 Step 9 — mirrors `PerceptionExecutionStateLlmDebug` (LLM JSON parse, pre–Step 8 validation). */
type PerceptionExecutionStateLlmDebug = {
  rows: Record<string, unknown>[];
  raw_assistant_text?: string | null;
  raw_assistant_truncated?: boolean;
  parse_error?: string | null;
  response_level_error?: string | null;
  model?: string | null;
  latency_ms?: number | null;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
  skipped_reason?: string | null;
};

type ManagerInsightFetchDebugResponse = {
  fetch: FetchActivityBundle;
  coordination_contracts: {
    decision_item_example: CoordinationDecisionItemExample;
    decision_bundle_example: CoordinationDecisionBundleExample;
    outcome_item_example: CoordinationOutcomeItemExample;
    perception_row_example: CoordinationPerceptionRowExample;
    perception_validation_demo: PerceptionValidationDemoDebug;
    perception_execution_state_demo: PerceptionExecutionStateLlmDebug;
  };
  data_reliability: DataReliabilityReport;
  work_items: {
    run_id: string;
    tenant_id: string;
    window_days: number;
    items: Array<{
      id: string;
      source: ManagerInsightConnector;
      type: WorkItemType;
      title: string;
      summary: string | null;
      status: string | null;
      url: string | null;
      project: string | null;
      owner: string | null;
      participants: string[];
      created_at: string | null;
      updated_at: string | null;
      closed_at: string | null;
      source_ref: Record<string, string>;
    }>;
  };
  evidence: {
    run_id: string;
    tenant_id: string;
    window_days: number;
    discarded_without_evidence: number;
    action_items: Array<{
      id: string;
      kind: "action_item" | "blocker" | "decision";
      statement: string;
      evidence: string;
      source_work_item_id: string;
      source_connector: ManagerInsightConnector;
      source_type: WorkItemType;
      source_ref: Record<string, string>;
      linked_work_items: string[];
    }>;
    blockers: Array<{
      id: string;
      kind: "action_item" | "blocker" | "decision";
      statement: string;
      evidence: string;
      source_work_item_id: string;
      source_connector: ManagerInsightConnector;
      source_type: WorkItemType;
      source_ref: Record<string, string>;
      linked_work_items: string[];
    }>;
    decisions: Array<{
      id: string;
      kind: "action_item" | "blocker" | "decision";
      statement: string;
      evidence: string;
      source_work_item_id: string;
      source_connector: ManagerInsightConnector;
      source_type: WorkItemType;
      source_ref: Record<string, string>;
      linked_work_items: string[];
    }>;
  };
  links: {
    run_id: string;
    tenant_id: string;
    window_days: number;
    work_items_capped: number;
    /** §6 Step 12 — validated perception rows merged into link scoring when perception_llm is on. */
    perception_rows_used_for_linking: number;
    links: Array<{
      id: string;
      from_work_item_id: string;
      to_work_item_id: string;
      link_type: "semantic_match" | "shared_reference";
      confidence: ReliabilityTier;
      similarity: number;
      method: string;
      evidence: string;
    }>;
  };
  gaps: {
    run_id: string;
    tenant_id: string;
    window_days: number;
    /** §6 Step 18 — present when `VECTOR_MANAGER_INSIGHTS_GAPS_USE_GRAPH` merged graph edges into gap neighborhood. */
    gaps_debug?: string | null;
    gaps: Array<{
      id: string;
      type: GapType;
      description: string;
      evidence_pointers: Record<string, string[]>;
    }>;
  };
  key_achievements: {
    run_id: string;
    tenant_id: string;
    window_days: number;
    items: Array<{
      id: string;
      title: string;
      linked_items: string[];
      evidence: string[];
      sort_at: string | null;
    }>;
  };
  raw_highlights: {
    run_id: string;
    tenant_id: string;
    window_days: number;
    items: Array<{
      id: string;
      text: string;
      sources: string[];
    }>;
  };
  signals: {
    delivery_strength: "low" | "moderate" | "high";
    urgent_pressure: "low" | "moderate" | "high";
    expectation_coverage: "high" | "partial" | "low";
    follow_through: "strong" | "partial" | "weak";
    blocker_visibility: "visible" | "partial" | "not_visible";
    repeated_discussion_present: boolean;
    execution_momentum: "accelerating" | "steady" | "slowing";
    documentation_linkage: "linked" | "partially_linked" | "not_linked";
    focus: "focused" | "moderate" | "fragmented";
    collaboration_intensity: "low" | "moderate" | "high";
    support_pattern: "gives_help" | "asks_for_help" | "balanced";
    feedback_reception: "proactive" | "neutral" | "defensive";
    coordination_role: "driving" | "contributing" | "peripheral";
    interaction_friction: "present" | "unclear" | "absent";
    /** §6 Steps 19–20 — coordination extension signals (same level enum as delivery_strength). */
    scope_ambiguity: "low" | "moderate" | "high";
    discussion_churn: "low" | "moderate" | "high";
    contradiction_density: "low" | "moderate" | "high";
    explain: Record<string, string>;
  };
  interpretations: {
    run_id: string;
    tenant_id: string;
    window_days: number;
    generated_via: "llm" | "fallback";
    fallback_reason: string | null;
    model: string | null;
    latency_ms: number | null;
    prompt_tokens: number | null;
    completion_tokens: number | null;
    total_tokens: number | null;
    llm_response_text: string | null;
    llm_response_truncated: boolean;
    llm_parsed_interpretation_rows: number | null;
    rejected_interpretations: Array<{
      index: number;
      reason: string;
      raw: Record<string, unknown>;
    }>;
    llm_error: string | null;
    items: Array<{
      id: string;
      type: string;
      description: string;
      based_on_signals: string[];
      evidence: string[];
      based_on_gaps: string[];
      based_on_blockers: string[];
      based_on_highlights: string[];
      confidence: "high" | "medium" | "low";
    }>;
  };
  insights: {
    run_id: string;
    tenant_id: string;
    window_days: number;
    generated_via: "llm" | "fallback";
    fallback_reason: string | null;
    model: string | null;
    latency_ms: number | null;
    prompt_tokens: number | null;
    completion_tokens: number | null;
    total_tokens: number | null;
    llm_response_text: string | null;
    llm_response_truncated: boolean;
    llm_parsed_insight_rows: number | null;
    rejected_insights: Array<{
      index: number;
      reason: string;
      raw: Record<string, unknown>;
    }>;
    llm_error: string | null;
    items: Array<{
      id: string;
      observation: string;
      interpretation: string;
      implication: string;
      evidence: string[];
      evidence_ids: string[];
      based_on_interpretations: string[];
      based_on_signals: string[];
      primary_work_item_ids: string[];
      supporting_work_item_ids: string[];
      primary_entities: Array<{ name: string; kind: "project" | "feature" | "system" }>;
      based_on_gaps: string[];
      based_on_blockers: string[];
      based_on_highlights: string[];
      confidence: "high" | "medium" | "low";
      priority: "critical" | "high" | "medium" | "low";
    }>;
  };
  decisions: CoordinationDecisionBundleExample | null;
  decisions_prioritized: CoordinationDecisionBundleExample["items"] | null;
  rejected_perception_rows: Array<{
    index: number;
    reason: string;
    raw: Record<string, unknown>;
  }>;
  execution_graph: Record<string, unknown> | null;
  perception: Record<string, unknown> | null;
  coordination_settings: ManagerInsightsCoordinationSettingsDebug;
  perception_qa: ManagerInsightPerceptionQaDebug;
  /** §6 Step 32 — DB primary keys for capped `decisions_prioritized` when `?persist_decisions=1` (same order). */
  persisted_decision_ids: string[];
};

/** §6 Steps 19–21 — `signals` row keys (excludes the explain map). */
type ManagerInsightSignalRowKey = Exclude<keyof ManagerInsightFetchDebugResponse["signals"], "explain">;

/** §6 Step 14 — original P6 signal slots (pre–coordination extension). */
const P6_SIGNAL_CORE_KEYS: readonly ManagerInsightSignalRowKey[] = [
  "delivery_strength",
  "urgent_pressure",
  "expectation_coverage",
  "follow_through",
  "blocker_visibility",
  "repeated_discussion_present",
  "execution_momentum",
  "documentation_linkage",
  "focus",
  "collaboration_intensity",
  "support_pattern",
  "feedback_reception",
  "coordination_role",
  "interaction_friction",
];

/** §6 Steps 19–21 — coordination extension signals (`SignalsV0Debug`); own subsection in admin P6. */
const P6_SIGNAL_EXTENSION_KEYS = ["scope_ambiguity", "discussion_churn", "contradiction_density"] as const;

function formatManagerInsightSignalValue(
  signals: ManagerInsightFetchDebugResponse["signals"],
  key: ManagerInsightSignalRowKey,
): string {
  if (key === "repeated_discussion_present") {
    return String(signals.repeated_discussion_present);
  }
  return String(signals[key]);
}

/** Keys added in §6 Step 3 — must stay in sync with `ManagerInsightFetchDebugResponse` above. */
type Step3CoordinationTopLevelKeys = Extract<
  keyof ManagerInsightFetchDebugResponse,
  "decisions" | "decisions_prioritized" | "rejected_perception_rows" | "execution_graph" | "perception"
>;
const _STEP3_COORDINATION_KEYS: Step3CoordinationTopLevelKeys[] = [
  "decisions",
  "decisions_prioritized",
  "rejected_perception_rows",
  "execution_graph",
  "perception",
];
void _STEP3_COORDINATION_KEYS;

/** §6 Step 6 — coordination_settings on fetch-debug. */
type Step6CoordinationSettingsKey = Extract<keyof ManagerInsightFetchDebugResponse, "coordination_settings">;
const _STEP6_COORDINATION_SETTINGS_KEY: Step6CoordinationSettingsKey[] = ["coordination_settings"];
void _STEP6_COORDINATION_SETTINGS_KEY;

/** §6 Step 7 — perception_row_example under coordination_contracts. */
type Step7CoordinationContractsPerceptionKey = Extract<
  keyof ManagerInsightFetchDebugResponse["coordination_contracts"],
  "perception_row_example"
>;
const _STEP7_COORDINATION_PERCEPTION_KEY: Step7CoordinationContractsPerceptionKey[] = ["perception_row_example"];
void _STEP7_COORDINATION_PERCEPTION_KEY;

/** §6 Step 8 — perception_validation_demo under coordination_contracts. */
type Step8CoordinationContractsValidationKey = Extract<
  keyof ManagerInsightFetchDebugResponse["coordination_contracts"],
  "perception_validation_demo"
>;
const _STEP8_COORDINATION_VALIDATION_KEY: Step8CoordinationContractsValidationKey[] = [
  "perception_validation_demo",
];
void _STEP8_COORDINATION_VALIDATION_KEY;

/** §6 Step 9 — perception_execution_state_demo under coordination_contracts. */
type Step9CoordinationContractsLlmKey = Extract<
  keyof ManagerInsightFetchDebugResponse["coordination_contracts"],
  "perception_execution_state_demo"
>;
const _STEP9_COORDINATION_LLM_KEY: Step9CoordinationContractsLlmKey[] = ["perception_execution_state_demo"];
void _STEP9_COORDINATION_LLM_KEY;

/** §6 Step 11 — perception_qa on fetch-debug. */
type Step11PerceptionQaKey = Extract<keyof ManagerInsightFetchDebugResponse, "perception_qa">;
const _STEP11_PERCEPTION_QA_KEY: Step11PerceptionQaKey[] = ["perception_qa"];
void _STEP11_PERCEPTION_QA_KEY;

/** §6 Step 12 — LinkBundle.perception_rows_used_for_linking */
type Step12LinksPerceptionKey = Extract<
  keyof ManagerInsightFetchDebugResponse["links"],
  "perception_rows_used_for_linking"
>;
const _STEP12_LINKS_PERCEPTION_KEY: Step12LinksPerceptionKey[] = ["perception_rows_used_for_linking"];
void _STEP12_LINKS_PERCEPTION_KEY;

function perceptionPathLabel(path: PerceptionEvidencePath): string {
  return path === "llm_perception_plus_regex_evidence"
    ? "LLM perception + regex evidence"
    : "Regex evidence only (no LLM perception)";
}

function engineDecisionCount(data: ManagerInsightFetchDebugResponse): number {
  if (data.decisions === null) {
    return 0;
  }
  return data.decisions.items.length;
}

function prioritizedDecisionCount(data: ManagerInsightFetchDebugResponse): number {
  if (data.decisions_prioritized === null) {
    return 0;
  }
  return data.decisions_prioritized.length;
}

/** §6 Step 29 — label for P7 header: surfaced count / full prioritized count · applied cap. */
function p7PrioritizedSurfaceBadge(data: ManagerInsightFetchDebugResponse): string | null {
  if (data.decisions_prioritized === null || data.decisions_prioritized.length === 0) {
    return null;
  }
  const surf = data.decisions_prioritized.length;
  const full = Math.max(data.perception_qa.decisions_prioritized_full_count, surf);
  return `#${surf}/${full} · cap ${data.perception_qa.max_decisions_cap_applied}`;
}

/** Folded header line for Execution graph & perception admin section. */
function graphPerceptionPhaseFoldSummary(data: ManagerInsightFetchDebugResponse): string {
  let graphPart: string;
  if (data.execution_graph === null) {
    graphPart = "Graph not attached";
  } else {
    const g = parseExecutionGraphPayload(data.execution_graph);
    graphPart = `${g.nodes.length} nodes · ${g.edges.length} edges · ${g.unresolved_dependency_refs.length} unresolved`;
  }
  const rej = data.rejected_perception_rows.length;
  let perc: string;
  if (
    data.perception !== null &&
    typeof data.perception === "object" &&
    "accepted_count" in data.perception
  ) {
    perc = `${String(data.perception.accepted_count)} accepted · ${String(data.perception.rejected_count)} rejected`;
  } else {
    perc = "perception null";
  }
  return `${graphPart} · ${perc} · ${rej} rejected perception row${rej === 1 ? "" : "s"}`;
}

type MonitorHealth = "ok" | "warn" | "error" | "info";

function worstMonitorHealth(...levels: MonitorHealth[]): MonitorHealth {
  const rank: Record<MonitorHealth, number> = { error: 0, warn: 1, info: 2, ok: 3 };
  return levels.reduce((a, b) => (rank[a] < rank[b] ? a : b), "ok" as MonitorHealth);
}

function MonitorStatusPill(props: { health: MonitorHealth; children: ReactNode }) {
  const { health, children } = props;
  const dot =
    health === "ok"
      ? "bg-emerald-500 shadow-[0_0_0_3px_rgba(16,185,129,0.25)]"
      : health === "warn"
        ? "bg-amber-500 shadow-[0_0_0_3px_rgba(245,158,11,0.25)]"
        : health === "error"
          ? "bg-rose-500 shadow-[0_0_0_3px_rgba(244,63,94,0.25)]"
          : "bg-sky-500 shadow-[0_0_0_3px_rgba(14,165,233,0.2)]";
  const ring =
    health === "ok"
      ? "bg-emerald-50 text-emerald-950 ring-emerald-200/80"
      : health === "warn"
        ? "bg-amber-50 text-amber-950 ring-amber-200/80"
        : health === "error"
          ? "bg-rose-50 text-rose-950 ring-rose-200/80"
          : "bg-sky-50 text-sky-950 ring-sky-200/70";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ring-1 ring-inset ${ring}`}
    >
      <span className={`h-2 w-2 shrink-0 rounded-full ${dot}`} aria-hidden />
      {children}
    </span>
  );
}

function MonitorKpi(props: {
  label: string;
  value: ReactNode;
  hint?: string;
  variant?: "neutral" | "good" | "caution" | "bad";
}) {
  const v = props.variant ?? "neutral";
  const box =
    v === "good"
      ? "border-emerald-200/90 bg-emerald-50/50"
      : v === "caution"
        ? "border-amber-200/90 bg-amber-50/40"
        : v === "bad"
          ? "border-rose-200/90 bg-rose-50/50"
          : "border-stone-200/90 bg-white";
  return (
    <div className={`rounded-lg border px-3 py-2 shadow-sm ${box}`}>
      <p className="text-[10px] font-semibold uppercase tracking-wide text-stone-500">{props.label}</p>
      <div className="mt-0.5 text-base font-semibold tabular-nums text-stone-900">{props.value}</div>
      {props.hint ? <p className="mt-0.5 text-[10px] leading-snug text-stone-500">{props.hint}</p> : null}
    </div>
  );
}

function monitorP05Health(data: ManagerInsightFetchDebugResponse): { health: MonitorHealth; why: string } {
  const lows = (["slack", "github", "linear", "notion", "calls"] as const).filter(
    (k) => data.data_reliability[k].tier === "low",
  );
  const meds = (["slack", "github", "linear", "notion", "calls"] as const).filter(
    (k) => data.data_reliability[k].tier === "medium",
  );
  if (data.data_reliability.overall_confidence === "low") {
    return { health: "error", why: "Overall connector reliability is low — treat downstream signals cautiously." };
  }
  if (lows.length > 0) {
    return {
      health: "warn",
      why: `${lows.length} source(s) at low tier (${lows.join(", ")}). Check reasons on cards below.`,
    };
  }
  if (data.data_reliability.overall_confidence === "medium" || meds.length > 0) {
    return { health: "info", why: "Acceptable reliability with some medium-tier connectors — see per-source cards." };
  }
  return { health: "ok", why: "All connectors report strong enough reliability for this window." };
}

function monitorP1Health(data: ManagerInsightFetchDebugResponse): { health: MonitorHealth; why: string } {
  const conns = Object.values(data.fetch.connectors);
  const err = conns.filter((c) => c.errors.length > 0);
  const bad = conns.filter((c) => c.status !== "ok");
  if (err.length > 0) {
    return { health: "warn", why: `${err.length} connector(s) logged fetch errors — expand per connector for messages.` };
  }
  if (bad.length > 0) {
    return { health: "info", why: `${bad.length} connector(s) returned non-ok status (may still be usable).` };
  }
  return { health: "ok", why: "Connector fetches completed without hard errors." };
}

function monitorIngestRollup(data: ManagerInsightFetchDebugResponse): { health: MonitorHealth; why: string } {
  const a = monitorP05Health(data);
  const b = monitorP1Health(data);
  const wi = data.work_items.items.length;
  const ev =
    data.evidence.action_items.length + data.evidence.blockers.length + data.evidence.decisions.length;
  let c: MonitorHealth = "ok";
  let cWhy = "";
  if (wi === 0) {
    c = "warn";
    cWhy = "No normalized work items — pipeline has little to analyze.";
  } else if (ev === 0) {
    c = "info";
    cWhy = "No regex evidence rows — may be normal if content is thin; check P3.";
  }
  const h = worstMonitorHealth(a.health, b.health, c);
  const parts = [a.why, b.why, cWhy].filter(Boolean);
  return { health: h, why: parts.join(" ") || "Ingest stages completed." };
}

function monitorGraphHealth(data: ManagerInsightFetchDebugResponse): { health: MonitorHealth; why: string } {
  if (data.execution_graph === null) {
    return {
      health: "info",
      why: "No execution graph attached — enable include_execution_graph or env for graph-backed QA.",
    };
  }
  const g = parseExecutionGraphPayload(data.execution_graph);
  if (g.nodes.length === 0) {
    return { health: "warn", why: "Graph payload is empty — linking/gaps may rely on evidence only." };
  }
  const rej = data.rejected_perception_rows.length;
  if (
    data.perception !== null &&
    typeof data.perception === "object" &&
    "rejected_count" in data.perception &&
    Number(data.perception.rejected_count) > 0
  ) {
    return {
      health: "info",
      why: `Perception validation rejected ${String(data.perception.rejected_count)} row(s); ${rej} raw rejects logged.`,
    };
  }
  return { health: "ok", why: "Graph built and perception path produced usable rows for this run." };
}

function monitorStructureHealth(data: ManagerInsightFetchDebugResponse): { health: MonitorHealth; why: string } {
  const n = data.links.links.length;
  const g = data.gaps.gaps.length;
  if (n === 0 && data.work_items.items.length > 5) {
    return {
      health: "warn",
      why: "Very few semantic links vs work items — cross-tool overlap may be weak.",
    };
  }
  if (g === 0) {
    return { health: "ok", why: "No coordination gaps detected from current inputs (clean scan)." };
  }
  return {
    health: "info",
    why: `${g} gap(s) identified — expected when coordination risks exist; decisions map from these.`,
  };
}

function monitorP4LinksHealth(data: ManagerInsightFetchDebugResponse): { health: MonitorHealth; why: string } {
  const n = data.links.links.length;
  const wi = data.work_items.items.length;
  if (n === 0) {
    return {
      health: wi > 5 ? "warn" : "info",
      why:
        wi > 5
          ? "No edges above similarity floor despite many work items — titles/refs may not overlap across tools."
          : "No links in this window — may be normal for a small corpus.",
    };
  }
  const hi = data.links.links.filter((L) => L.confidence === "high").length;
  const hiPct = Math.round((hi / n) * 100);
  return {
    health: "ok",
    why: `${n} link candidate(s); ${hiPct}% high-confidence — these feed gap detection.`,
  };
}

function monitorP5GapsHealth(data: ManagerInsightFetchDebugResponse): { health: MonitorHealth; why: string } {
  const g = data.gaps.gaps.length;
  if (g === 0) {
    return { health: "ok", why: "No structural coordination gaps surfaced (inputs look aligned)." };
  }
  return {
    health: "info",
    why: `${g} gap(s) to triage — each becomes a candidate decision in the next stage.`,
  };
}

function monitorSignalsHealth(data: ManagerInsightFetchDebugResponse): { health: MonitorHealth; why: string } {
  const s = data.signals;
  const risks: string[] = [];
  if (s.scope_ambiguity === "high") {
    risks.push("scope ambiguity high");
  }
  if (s.discussion_churn === "high" && s.contradiction_density === "high") {
    risks.push("churn + contradictions both high");
  }
  if (s.focus === "fragmented") {
    risks.push("focus fragmented");
  }
  if (s.execution_momentum === "slowing") {
    risks.push("execution slowing");
  }
  if (risks.length >= 2) {
    return { health: "warn", why: `Coordination strain: ${risks.slice(0, 3).join("; ")}.` };
  }
  if (risks.length === 1) {
    return { health: "info", why: `Watch: ${risks[0]}.` };
  }
  return { health: "ok", why: "Signal vector has no high-severity coordination red flags in this pass." };
}

function monitorDecisionsHealth(data: ManagerInsightFetchDebugResponse): { health: MonitorHealth; why: string } {
  const n = engineDecisionCount(data);
  const p = prioritizedDecisionCount(data);
  if (n === 0) {
    return { health: "info", why: "No decision rows — usually means zero gaps to act on." };
  }
  if (p === 0) {
    return { health: "warn", why: "Engine produced decisions but prioritized surface is empty — check cap / filters." };
  }
  return {
    health: "ok",
    why: `${n} engine decision(s); ${p} on prioritized surface (ranked for action).`,
  };
}

/** Live pipeline strip: health + one-line “why” per major phase (monitoring-first). */
function ManagerInsightPipelineMonitorStrip(props: { data: ManagerInsightFetchDebugResponse }) {
  const { data } = props;
  const steps: {
    key: string;
    title: string;
    subtitle: string;
    health: MonitorHealth;
    why: string;
  }[] = [
    {
      key: "ingest",
      title: "Ingest",
      subtitle: `${PIPELINE.p05}→${PIPELINE.p3}`,
      ...(() => {
        const m = monitorIngestRollup(data);
        return { health: m.health, why: m.why };
      })(),
    },
    {
      key: "graph",
      title: "Graph & perception",
      subtitle: "Execution graph + LLM rows",
      ...monitorGraphHealth(data),
    },
    {
      key: "structure",
      title: "Structure",
      subtitle: `${PIPELINE.p4}→${PIPELINE.p5}`,
      ...monitorStructureHealth(data),
    },
    {
      key: "rollups",
      title: "Rollups",
      subtitle: `${PIPELINE.p55} / ${PIPELINE.p56}`,
      health: "info" as const,
      why: `${data.key_achievements.items.length} achievements · ${data.raw_highlights.items.length} highlights`,
    },
    {
      key: "signals",
      title: "Signals",
      subtitle: PIPELINE.p6,
      ...monitorSignalsHealth(data),
    },
    {
      key: "actions",
      title: "Decisions → actions",
      subtitle: "Prioritized surface",
      ...monitorDecisionsHealth(data),
    },
  ];

  return (
    <div
      className="overflow-hidden rounded-xl border border-slate-200/90 bg-gradient-to-br from-slate-50 via-white to-sky-50/40 shadow-md"
      data-testid="manager-insight-pipeline-overview"
    >
      <div className="border-b border-slate-200/80 bg-white/70 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-900">Ingestion monitor</h2>
        <p className="mt-0.5 text-xs text-slate-600">
          End-to-end health for this fetch-debug run. Expand each section below for metrics; open{" "}
          <span className="font-medium text-slate-800">Technical details</span> only when debugging.
        </p>
      </div>
      <ul className="divide-y divide-slate-100">
        {steps.map((s) => (
          <li key={s.key} className="flex flex-col gap-1.5 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
            <div className="min-w-0">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">{s.subtitle}</p>
              <p className="truncate text-sm font-semibold text-slate-900">{s.title}</p>
              <p className="mt-0.5 text-xs leading-snug text-slate-600">{s.why}</p>
            </div>
            <div className="shrink-0">
              <MonitorStatusPill health={s.health}>
                {s.health === "ok"
                  ? "Good"
                  : s.health === "warn"
                    ? "Attention"
                    : s.health === "error"
                      ? "Critical"
                      : "FYI"}
              </MonitorStatusPill>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function signalCardTone(
  key: ManagerInsightSignalRowKey,
  value: string,
): "neutral" | "good" | "caution" | "bad" {
  const v = value.toLowerCase();
  if (key === "repeated_discussion_present") {
    return value === "true" ? "caution" : "good";
  }
  if (
    v.includes("high") &&
    (key === "scope_ambiguity" || key === "discussion_churn" || key === "contradiction_density" || key === "urgent_pressure")
  ) {
    return "caution";
  }
  if (v === "fragmented" || v === "slowing" || v === "not_linked" || v === "not_visible" || v === "partial") {
    return "caution";
  }
  if (v === "low" && (key === "delivery_strength" || key === "expectation_coverage")) {
    return "caution";
  }
  if (v === "high" && key === "delivery_strength") {
    return "good";
  }
  if (v === "steady" || v === "focused" || v === "strong" || v === "high") {
    return "good";
  }
  return "neutral";
}

function signalCardClass(tone: ReturnType<typeof signalCardTone>): string {
  if (tone === "good") {
    return "border-l-emerald-500 bg-emerald-50/25";
  }
  if (tone === "caution") {
    return "border-l-amber-500 bg-amber-50/25";
  }
  if (tone === "bad") {
    return "border-l-rose-500 bg-rose-50/25";
  }
  return "border-l-slate-300 bg-white";
}

function humanDecisionTypeLabel(t: CoordinationDecisionType): string {
  const map: Record<CoordinationDecisionType, string> = {
    LINK_OR_CLOSE_COMMITMENT: "Link or close commitment",
    THREAD_TO_TRACKING_LINK: "Connect thread to work",
    BLOCKER_ESCALATION: "Blocker escalation",
    DOC_EXECUTION_BRIDGE: "Doc ↔ execution bridge",
    HOLD_START: "Pause / hold start",
    CLARIFY_SPEC: "Clarify spec",
    RECENTER: "Recenter scope",
    PAUSE_INVESTMENT: "Pause investment",
  };
  return map[t] ?? t.replace(/_/g, " ");
}

function humanSignalHeading(key: ManagerInsightSignalRowKey): string {
  const m: Partial<Record<ManagerInsightSignalRowKey, string>> = {
    delivery_strength: "Delivery strength",
    urgent_pressure: "Urgent pressure",
    expectation_coverage: "Expectation coverage",
    follow_through: "Follow-through",
    blocker_visibility: "Blocker visibility",
    repeated_discussion_present: "Repeated discussion",
    execution_momentum: "Execution pace",
    documentation_linkage: "Docs linked to work",
    focus: "Team focus",
    collaboration_intensity: "Collaboration intensity",
    support_pattern: "Support pattern",
    feedback_reception: "Feedback reception",
    coordination_role: "Coordination role",
    interaction_friction: "Interaction friction",
    scope_ambiguity: "Scope clarity",
    discussion_churn: "Discussion churn",
    contradiction_density: "Contradictions",
  };
  return m[key] ?? key.replace(/_/g, " ");
}

/** Human-facing status line for cards (avoids raw enum keys in the demo UI). */
function humanSignalStatusLine(key: ManagerInsightSignalRowKey, signals: ManagerInsightFetchDebugResponse["signals"]): string {
  const v = formatManagerInsightSignalValue(signals, key);
  if (key === "execution_momentum") {
    return v === "slowing" ? "Slowing" : v === "accelerating" ? "Accelerating" : "Steady";
  }
  if (key === "scope_ambiguity") {
    return v === "high" ? "Scope unclear" : v === "moderate" ? "Some ambiguity" : "Clear enough";
  }
  if (key === "blocker_visibility") {
    return v === "not_visible" ? "Blockers not fully tracked" : v === "partial" ? "Partial visibility" : "Visible";
  }
  if (key === "focus") {
    return v === "fragmented" ? "Focus fragmented" : v === "focused" ? "Focused" : "Moderate focus";
  }
  if (key === "documentation_linkage") {
    return v === "not_linked" ? "Docs not linked" : v === "partially_linked" ? "Partially linked" : "Linked";
  }
  if (key === "repeated_discussion_present") {
    return v === "true" ? "Present" : "Not present";
  }
  return v.replace(/_/g, " ");
}

type SignalProductEntry = {
  key: ManagerInsightSignalRowKey;
  label: string;
  statusLine: string;
  explain: string;
  bucket: "good" | "risk" | "neutral";
};

function buildSignalProductEntries(data: ManagerInsightFetchDebugResponse): {
  good: SignalProductEntry[];
  risk: SignalProductEntry[];
  neutral: SignalProductEntry[];
} {
  const keys = [...P6_SIGNAL_CORE_KEYS, ...P6_SIGNAL_EXTENSION_KEYS] as ManagerInsightSignalRowKey[];
  const good: SignalProductEntry[] = [];
  const risk: SignalProductEntry[] = [];
  const neutral: SignalProductEntry[] = [];
  for (const key of keys) {
    const val = formatManagerInsightSignalValue(data.signals, key);
    const tone = signalCardTone(key, val);
    const entry: SignalProductEntry = {
      key,
      label: humanSignalHeading(key),
      statusLine: humanSignalStatusLine(key, data.signals),
      explain: data.signals.explain[key] ?? "—",
      bucket: tone === "good" ? "good" : tone === "caution" || tone === "bad" ? "risk" : "neutral",
    };
    if (entry.bucket === "good") {
      good.push(entry);
    } else if (entry.bucket === "risk") {
      risk.push(entry);
    } else {
      neutral.push(entry);
    }
  }
  return { good, risk, neutral };
}

/** Shared chrome for the main execution run readout (not used for Advanced debug). */
function ExecutionRunSectionShell(props: {
  sectionIndex: string;
  kicker: string;
  title: string;
  description?: ReactNode;
  "data-testid"?: string;
  children: ReactNode;
}) {
  const tid = props["data-testid"];
  return (
    <section
      className="rounded-2xl border border-slate-200/90 bg-white p-8 shadow-[0_1px_2px_rgba(15,23,42,0.04),0_12px_32px_rgba(15,23,42,0.06)]"
      data-testid={tid}
    >
      <header className="border-b border-slate-100 pb-6">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">
          Section {props.sectionIndex} · {props.kicker}
        </p>
        <h2 className="mt-2 text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">{props.title}</h2>
        {props.description ? (
          <div className="mt-2 max-w-prose text-sm leading-relaxed text-slate-600">{props.description}</div>
        ) : null}
      </header>
      <div className="pt-6">{props.children}</div>
    </section>
  );
}

function pipelineExecutionTimelineSteps(data: ManagerInsightFetchDebugResponse): {
  key: string;
  title: string;
  health: MonitorHealth;
  why: string;
}[] {
  const ingest = monitorIngestRollup(data);
  const graph = monitorGraphHealth(data);
  const structure = monitorStructureHealth(data);
  const roll = `${data.key_achievements.items.length} shipped · ${data.raw_highlights.items.length} highlights`;
  const signals = monitorSignalsHealth(data);
  const decisions = monitorDecisionsHealth(data);
  return [
    { key: "ingest", title: "Ingest", health: ingest.health, why: ingest.why },
    { key: "graph", title: "Graph & perception", health: graph.health, why: graph.why },
    {
      key: "structure",
      title: "Structure",
      health: structure.health,
      why: `${structure.why} · Rollups: ${roll}.`,
    },
    { key: "signals", title: "Signals", health: signals.health, why: signals.why },
    { key: "decisions", title: "Decisions", health: decisions.health, why: decisions.why },
  ];
}

function ExecutionRunSummaryMetrics(props: { data: ManagerInsightFetchDebugResponse }) {
  const { data } = props;
  const sh = monitorSignalsHealth(data);
  const execLabel =
    sh.health === "warn" ? "Strained" : sh.health === "error" ? "Critical" : sh.health === "info" ? "Watch" : "Good";
  const mom = data.signals.execution_momentum;
  const delivery =
    mom === "slowing" ? "Slowing" : mom === "accelerating" ? "Accelerating" : "Steady";
  const dr =
    data.data_reliability.overall_confidence === "high"
      ? "High"
      : data.data_reliability.overall_confidence === "medium"
        ? "Mixed"
        : "Attention";
  const top = data.decisions_prioritized?.[0]?.decision.title ?? null;
  const nDec = prioritizedDecisionCount(data);
  const nGaps = data.gaps.gaps.length;

  const metricCard = (
    label: string,
    value: ReactNode,
    sub?: string,
    accent?: "emerald" | "amber" | "rose" | "sky",
  ) => {
    const ring =
      accent === "emerald"
        ? "ring-emerald-200/80"
        : accent === "amber"
          ? "ring-amber-200/80"
          : accent === "rose"
            ? "ring-rose-200/80"
            : "ring-sky-200/70";
    return (
      <div className={`rounded-xl bg-slate-50/90 px-4 py-3 shadow-sm ring-1 ring-inset ${ring}`}>
        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{label}</p>
        <p className="mt-1.5 text-2xl font-semibold tabular-nums tracking-tight text-slate-900">{value}</p>
        {sub ? <p className="mt-1 text-xs text-slate-500">{sub}</p> : null}
      </div>
    );
  };

  return (
    <div className="space-y-6" data-testid="manager-insight-execution-run-hero">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {metricCard("Decisions surfaced", nDec, "Prioritized for action", nDec > 0 ? "emerald" : "sky")}
        {metricCard("Coordination gaps", nGaps, "From structure pass", nGaps > 3 ? "amber" : "emerald")}
        {metricCard("Execution health", execLabel, "From signal posture", sh.health === "ok" ? "emerald" : "amber")}
        {metricCard("Delivery momentum", delivery, "Pace of completion", mom === "slowing" ? "amber" : "emerald")}
        {metricCard("Data reliability", dr, "Connector confidence", dr === "Attention" ? "rose" : "emerald")}
      </div>
      <div className="rounded-xl border border-slate-200 bg-slate-50/80 px-5 py-4">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Top priority</p>
        {top ? (
          <p className="mt-2 text-base font-semibold leading-snug text-slate-900">{top}</p>
        ) : (
          <p className="mt-2 text-sm text-slate-500">No prioritized decision on this run — run the pipeline or relax caps.</p>
        )}
      </div>
    </div>
  );
}

function ManagerInsightPipelineExecutionTimeline(props: { data: ManagerInsightFetchDebugResponse }) {
  const { data } = props;
  const steps = pipelineExecutionTimelineSteps(data);
  const nWork = data.work_items.items.length;
  const nGaps = data.gaps.gaps.length;
  const nDec = prioritizedDecisionCount(data);
  const description = (
    <>
      Vector analyzed <span className="font-semibold text-slate-800 tabular-nums">{nWork}</span> work items and identified{" "}
      <span className="font-semibold text-slate-800 tabular-nums">{nGaps}</span> coordination gaps
      {nDec > 0 ? (
        <>
          , surfacing <span className="font-semibold text-slate-800 tabular-nums">{nDec}</span> prioritized actions. The
          timeline below shows how each stage contributed to that picture — expand a step for status detail.
        </>
      ) : (
        ". Expand each stage to see how ingest through decisions behaved on this run."
      )}
    </>
  );

  return (
    <ExecutionRunSectionShell
      sectionIndex="1"
      kicker="Run overview"
      title="Execution pipeline"
      description={description}
      data-testid="manager-insight-pipeline-timeline"
    >
      <ExecutionRunSummaryMetrics data={data} />
      <div className="mt-8 border-t border-slate-100 pt-8">
        <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-slate-500">Pipeline stages</p>
        <p className="mt-1 max-w-prose text-sm text-slate-600">
          Read top to bottom — each stage feeds the next. Status pills reflect deterministic checks on this run&apos;s payloads.
        </p>
        <ol className="relative mt-6 space-y-0 border-l border-slate-200 pl-8">
          {steps.map((s, i) => (
            <li key={s.key} className="pb-10 last:pb-0">
              <span
                className="absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-slate-800 shadow ring-2 ring-slate-200"
                aria-hidden
              />
              <details className="group rounded-xl bg-slate-50/90 ring-1 ring-slate-100 open:bg-white open:shadow-md open:ring-slate-200/80">
                <summary className="flex cursor-pointer list-none flex-wrap items-start justify-between gap-3 px-4 py-4 marker:content-none [&::-webkit-details-marker]:hidden">
                  <div className="min-w-0">
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                      Stage {i + 1} · {s.title}
                    </p>
                    <p className="mt-1 text-sm font-medium leading-snug text-slate-900">{s.why}</p>
                  </div>
                  <MonitorStatusPill health={s.health}>
                    {s.health === "ok"
                      ? "Good"
                      : s.health === "warn"
                        ? "Attention"
                        : s.health === "error"
                          ? "Critical"
                          : "FYI"}
                  </MonitorStatusPill>
                </summary>
                <div className="border-t border-slate-100 px-4 py-3 text-xs leading-relaxed text-slate-600">
                  Open <span className="font-medium text-slate-800">Advanced debug</span> → <span className="font-medium">Full pipeline</span>{" "}
                  for raw payloads and JSON for this stage.
                </div>
              </details>
            </li>
          ))}
        </ol>
      </div>
    </ExecutionRunSectionShell>
  );
}

function PrioritizedDecisionsSpotlight(props: { data: ManagerInsightFetchDebugResponse }) {
  const rows = props.data.decisions_prioritized?.slice(0, 3) ?? [];
  return (
    <ExecutionRunSectionShell
      sectionIndex="4"
      kicker="What to do next"
      title="Prioritized decisions"
      description="Ranked actions derived from gaps and signals. Evidence stays behind each card — approve or ignore when you wire actions."
      data-testid="manager-insight-prioritized-spotlight"
    >
      {rows.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/80 px-6 py-12 text-center text-sm text-slate-600">
          No prioritized decisions — usually zero gaps, an empty engine bundle, or a cap of zero.
        </div>
      ) : (
        <ul className="space-y-6">
          {rows.map((row, idx) => (
            <li
              key={`${row.decision.id}-spot-${idx}`}
              className="rounded-xl border border-slate-200/90 bg-slate-50/40 p-6 shadow-sm ring-1 ring-slate-100"
              data-testid={`manager-insight-prioritized-spotlight-card-${idx}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <span className="inline-flex rounded-full bg-indigo-50 px-2.5 py-0.5 text-[11px] font-semibold text-indigo-900 ring-1 ring-indigo-100">
                    {humanDecisionTypeLabel(row.decision.decision_type)}
                  </span>
                  <h3 className="mt-3 text-xl font-semibold leading-snug text-slate-900">{row.decision.title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-slate-600">{row.decision.rationale}</p>
                </div>
                <span className="shrink-0 rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-bold tabular-nums text-slate-700">
                  #{idx + 1}
                </span>
              </div>
              <details className="mt-6 rounded-xl border border-slate-100 bg-slate-50/50">
                <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-slate-800">Evidence &amp; refs</summary>
                <div className="border-t border-slate-100 px-4 py-3 text-xs text-slate-600">
                  {row.decision.evidence_refs.length ? (
                    <ul className="list-inside list-disc space-y-1">
                      {row.decision.evidence_refs.map((r) => (
                        <li key={r} className="font-mono text-[11px]">
                          {r}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-slate-500">No evidence refs on this row.</p>
                  )}
                </div>
              </details>
              <div className="mt-6 flex flex-wrap gap-3">
                <button
                  type="button"
                  className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-slate-800"
                  disabled
                  title="Coming soon"
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50"
                  disabled
                  title="Coming soon"
                >
                  Ignore
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </ExecutionRunSectionShell>
  );
}

function ExecutionSignalsWhySection(props: { data: ManagerInsightFetchDebugResponse }) {
  const { good, risk, neutral } = buildSignalProductEntries(props.data);
  return (
    <ExecutionRunSectionShell
      sectionIndex="3"
      kicker="Why this matters"
      title="Signals"
      description="Deterministic read on coordination posture — supportive signals on the left, risks and friction on the right, neutral context below."
      data-testid="manager-insight-signals-why-product"
    >
      <div className="grid gap-8 lg:grid-cols-2">
        <div>
          <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-emerald-800">Healthy / supportive</h3>
          <ul className="space-y-3">
            {good.length === 0 ? (
              <li className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-6 text-sm text-slate-600">
                No strongly positive flags — check context column.
              </li>
            ) : (
              good.map((s) => (
                <li
                  key={s.key}
                  className="rounded-xl border border-emerald-100/80 bg-emerald-50/40 px-4 py-3 shadow-sm"
                  data-testid={`manager-insight-signal-product-good-${s.key}`}
                >
                  <p className="text-sm font-semibold text-slate-900">{s.label}</p>
                  <p className="mt-0.5 text-xs font-medium text-emerald-900">{s.statusLine}</p>
                  <p className="mt-2 text-xs leading-relaxed text-slate-600">{s.explain}</p>
                </li>
              ))
            )}
          </ul>
        </div>
        <div>
          <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-amber-900">Risks &amp; friction</h3>
          <ul className="space-y-3">
            {risk.length === 0 ? (
              <li className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-6 text-sm text-slate-600">
                No elevated risk flags on this pass.
              </li>
            ) : (
              risk.map((s) => (
                <li
                  key={s.key}
                  className="rounded-xl border border-amber-100/90 bg-amber-50/50 px-4 py-3 shadow-sm"
                  data-testid={`manager-insight-signal-product-risk-${s.key}`}
                >
                  <p className="text-sm font-semibold text-slate-900">{s.label}</p>
                  <p className="mt-0.5 text-xs font-medium text-amber-950">{s.statusLine}</p>
                  <p className="mt-2 text-xs leading-relaxed text-slate-600">{s.explain}</p>
                </li>
              ))
            )}
          </ul>
        </div>
      </div>
      {neutral.length > 0 ? (
        <div>
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Context</h3>
          <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {neutral.map((s) => (
              <li
                key={s.key}
                className="rounded-lg border border-slate-100 bg-white px-3 py-2.5 text-xs shadow-sm ring-1 ring-slate-100"
                data-testid={`manager-insight-signal-product-neutral-${s.key}`}
              >
                <p className="font-semibold text-slate-800">{s.label}</p>
                <p className="mt-0.5 text-slate-600">{s.statusLine}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </ExecutionRunSectionShell>
  );
}

function ExecutionGapsSummary(props: { data: ManagerInsightFetchDebugResponse }) {
  const gaps = props.data.gaps.gaps;
  const byType = (t: GapType) => gaps.filter((g) => g.type === t).length;
  const types: { type: GapType; label: string }[] = [
    { type: "expected_not_executed", label: "Expected, not executed" },
    { type: "discussed_not_linked_to_work", label: "Discussed, not linked" },
    { type: "blocker_not_tracked", label: "Blocker not tracked" },
    { type: "doc_not_connected_to_execution", label: "Doc vs execution" },
  ];
  return (
    <ExecutionRunSectionShell
      sectionIndex="2"
      kicker="Structural risks"
      title="Coordination gaps"
      description="Grouped counts from the gap pass — each type can produce engine decisions. Full records and evidence JSON are in Advanced debug."
      data-testid="manager-insight-gaps-summary-product"
    >
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {types.map(({ type, label }) => (
          <div key={type} className="rounded-xl border border-slate-100 bg-slate-50/90 px-4 py-3 shadow-sm">
            <p className="text-[11px] font-medium text-slate-500">{label}</p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-900">{byType(type)}</p>
          </div>
        ))}
      </div>
      <details className="mt-6 rounded-xl border border-slate-100 bg-slate-50/50">
        <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-slate-800">Example gaps</summary>
        <ul className="space-y-2 border-t border-slate-100 px-4 py-3">
          {gaps.slice(0, 5).map((g) => (
            <li key={g.id} className="text-sm text-slate-700">
              <span className="mr-2 rounded bg-slate-200/80 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-slate-700">
                {g.type.replace(/_/g, " ")}
              </span>
              {g.description}
            </li>
          ))}
          {gaps.length === 0 ? <li className="text-sm text-slate-500">No gaps in this run.</li> : null}
        </ul>
      </details>
    </ExecutionRunSectionShell>
  );
}

/** §6 Step 24 — engine decisions as a QA table (columns + expandable row JSON / debug). */
function CoordinationDecisionsTable(props: {
  items: CoordinationDecisionBundleExample["items"];
}) {
  const { items } = props;
  return (
    <div className="mt-3 overflow-x-auto rounded-md border border-amber-200/90 bg-white shadow-sm">
      <table
        className="w-full min-w-[32rem] border-collapse text-left text-xs text-stone-800"
        data-testid="manager-insight-decisions-table"
      >
        <thead>
          <tr className="border-b border-amber-200 bg-amber-100/50">
            <th scope="col" className="px-3 py-2 font-semibold text-stone-900">
              decision_type
            </th>
            <th scope="col" className="px-3 py-2 font-semibold text-stone-900">
              gap_id
            </th>
            <th scope="col" className="min-w-[12rem] px-3 py-2 font-semibold text-stone-900">
              title
            </th>
            <th scope="col" className="w-[1%] whitespace-nowrap px-3 py-2 font-semibold text-stone-900">
              JSON
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((row, idx) => (
            <tr
              key={`${row.decision.id}-${idx}`}
              className="border-b border-amber-100 last:border-b-0"
              data-testid={`manager-insight-decision-row-${idx}`}
            >
              <td className="align-top px-3 py-2 font-mono text-[11px] text-stone-800">
                {row.decision.decision_type}
              </td>
              <td className="align-top px-3 py-2 font-mono text-[11px] text-stone-700">
                {row.decision.gap_id}
              </td>
              <td className="align-top px-3 py-2 text-stone-900">{row.decision.title}</td>
              <td className="align-top px-3 py-2">
                <details className="group/rowjson max-w-xs">
                  <summary className="cursor-pointer list-none text-[11px] font-medium text-amber-900 underline decoration-amber-300 underline-offset-2 marker:content-none [&::-webkit-details-marker]:hidden">
                    {row.decision_debug || row.decision_emission_debug
                      ? "Expand (incl. debug)"
                      : "Expand"}
                  </summary>
                  <pre className="mt-2 max-h-56 overflow-auto rounded border border-amber-100 bg-stone-50 p-2 text-[10px] leading-snug text-stone-800">
                    {JSON.stringify(row, null, 2)}
                  </pre>
                </details>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** §6 Step 29 — same rows as `decisions_prioritized` with rank 1..n (Step 27 order, Step 28 cap). */
function PrioritizedDecisionsSurfaceTable(props: {
  items: CoordinationDecisionBundleExample["items"];
}) {
  const { items } = props;
  return (
    <div className="mt-4 overflow-x-auto rounded-md border border-teal-200/90 bg-white shadow-sm">
      <h4 className="border-b border-teal-100 bg-teal-50/80 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-teal-950">
        Prioritized surface <span className="font-normal text-teal-800">(§6 Steps 27–29)</span>
      </h4>
      <table
        className="w-full min-w-[36rem] border-collapse text-left text-xs text-stone-800"
        data-testid="manager-insight-prioritized-decisions-table"
      >
        <thead>
          <tr className="border-b border-teal-100 bg-teal-50/60">
            <th scope="col" className="w-[1%] whitespace-nowrap px-3 py-2 font-semibold text-teal-950">
              rank
            </th>
            <th scope="col" className="px-3 py-2 font-semibold text-stone-900">
              decision_type
            </th>
            <th scope="col" className="px-3 py-2 font-semibold text-stone-900">
              gap_id
            </th>
            <th scope="col" className="min-w-[12rem] px-3 py-2 font-semibold text-stone-900">
              title
            </th>
            <th scope="col" className="w-[1%] whitespace-nowrap px-3 py-2 font-semibold text-stone-900">
              JSON
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((row, idx) => (
            <tr
              key={`${row.decision.id}-prio-${idx}`}
              className="border-b border-teal-50 last:border-b-0"
              data-testid={`manager-insight-prioritized-decision-row-${idx}`}
            >
              <td className="align-top px-3 py-2 text-center font-mono text-[11px] font-semibold tabular-nums text-teal-900">
                {idx + 1}
              </td>
              <td className="align-top px-3 py-2 font-mono text-[11px] text-stone-800">
                {row.decision.decision_type}
              </td>
              <td className="align-top px-3 py-2 font-mono text-[11px] text-stone-700">
                {row.decision.gap_id}
              </td>
              <td className="align-top px-3 py-2 text-stone-900">{row.decision.title}</td>
              <td className="align-top px-3 py-2">
                <details className="group/rowjson max-w-xs">
                  <summary className="cursor-pointer list-none text-[11px] font-medium text-teal-900 underline decoration-teal-300 underline-offset-2 marker:content-none [&::-webkit-details-marker]:hidden">
                    {row.decision_debug || row.decision_emission_debug ? "Expand (incl. debug)" : "Expand"}
                  </summary>
                  <pre className="mt-2 max-h-56 overflow-auto rounded border border-teal-100 bg-stone-50 p-2 text-[10px] leading-snug text-stone-800">
                    {JSON.stringify(row, null, 2)}
                  </pre>
                </details>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function tierBadge(tier: ReliabilityTier) {
  const cls =
    tier === "high"
      ? "bg-emerald-50 text-emerald-900 ring-emerald-200"
      : tier === "medium"
        ? "bg-amber-50 text-amber-950 ring-amber-200"
        : "bg-rose-50 text-rose-900 ring-rose-200";
  return (
    <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${cls}`}>
      {tier}
    </span>
  );
}

/** §6 Step 17 — coordination §4.5: nodes / edges / unresolved refs + raw JSON for QA. */
function ExecutionGraphFourFiveSection(props: { raw: Record<string, unknown> | null }) {
  const { raw } = props;
  const g = parseExecutionGraphPayload(raw);
  const attached = raw !== null;
  const nodeCount = g?.nodes.length ?? 0;
  const edgeCount = g?.edges.length ?? 0;
  const unresolvedCount = g?.unresolved_dependency_refs.length ?? 0;

  return (
    <div
      className="rounded-md border border-teal-200 bg-white/95 p-3 shadow-sm"
      data-testid="manager-insight-execution-graph-fetch-debug"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-teal-900">
          Execution graph <span className="font-normal text-teal-700">(4.5 — §6 Step 17)</span>
        </h3>
        <div
          className="flex flex-wrap gap-2 tabular-nums"
          data-testid="manager-insight-execution-graph-counts"
        >
          <span
            className="rounded-md bg-stone-100 px-2 py-0.5 text-[11px] font-medium text-stone-800 ring-1 ring-stone-200"
            title="len(execution_graph.nodes)"
          >
            nodes: {attached ? nodeCount : "—"}
          </span>
          <span
            className="rounded-md bg-stone-100 px-2 py-0.5 text-[11px] font-medium text-stone-800 ring-1 ring-stone-200"
            title="len(execution_graph.edges)"
          >
            edges: {attached ? edgeCount : "—"}
          </span>
          <span
            className="rounded-md bg-stone-100 px-2 py-0.5 text-[11px] font-medium text-stone-800 ring-1 ring-stone-200"
            title="len(execution_graph.unresolved_dependency_refs)"
          >
            unresolved: {attached ? unresolvedCount : "—"}
          </span>
        </div>
      </div>
      <p className="mt-2 text-xs text-stone-600">
        Built by <span className="font-mono text-[11px]">build_execution_graph</span> (§6 Step 15); attached on fetch-debug
        when §6 Step 16 is satisfied (<span className="font-mono text-[11px]">?include_execution_graph=1</span> or env). No
        DB persistence.
      </p>
      {!attached ? (
        <p className="mt-2 text-xs text-amber-900">
          <span className="font-semibold">execution_graph</span> is <span className="font-mono">null</span> — enable the
          checkbox <span className="font-mono text-[11px]">include_execution_graph=1</span> (or set{" "}
          <code className="text-[11px]">VECTOR_MANAGER_INSIGHTS_INCLUDE_EXECUTION_GRAPH</code>) and re-run.
        </p>
      ) : null}
      {g ? (
        <>
          {g.run_id || g.tenant_id || g.window_days !== undefined ? (
            <p className="mt-2 text-[11px] text-stone-500">
              {g.run_id ? (
                <>
                  <span className="font-medium text-stone-600">run_id</span>{" "}
                  <span className="font-mono text-stone-700">{g.run_id}</span>
                  {" · "}
                </>
              ) : null}
              {g.tenant_id ? (
                <>
                  <span className="font-medium text-stone-600">tenant_id</span>{" "}
                  <span className="font-mono text-stone-700">{g.tenant_id}</span>
                  {" · "}
                </>
              ) : null}
              {g.window_days !== undefined ? (
                <>
                  <span className="font-medium text-stone-600">window_days</span>{" "}
                  <span className="tabular-nums text-stone-700">{g.window_days}</span>
                </>
              ) : null}
            </p>
          ) : null}
          <div className="mt-3 grid gap-4 xl:grid-cols-2" data-testid="manager-insight-execution-graph-45">
            <div data-testid="manager-insight-execution-graph-nodes">
              <h4 className="text-[11px] font-semibold uppercase tracking-wide text-teal-800">Nodes</h4>
              <div className="mt-1 overflow-x-auto rounded border border-teal-100">
                <table className="min-w-full border-collapse text-left text-[11px]">
                  <thead className="bg-teal-50/80 text-teal-950">
                    <tr>
                      <th className="border-b border-teal-100 px-2 py-1 font-semibold">id</th>
                      <th className="border-b border-teal-100 px-2 py-1 font-semibold">kind</th>
                      <th className="border-b border-teal-100 px-2 py-1 font-semibold">execution_state</th>
                      <th className="border-b border-teal-100 px-2 py-1 font-semibold">owner_hint</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white text-stone-800">
                    {g.nodes.length === 0 ? (
                      <tr>
                        <td className="border-t border-teal-50 px-2 py-2 italic text-stone-500" colSpan={4}>
                          No nodes (empty graph).
                        </td>
                      </tr>
                    ) : (
                      g.nodes.map((row, idx) => (
                        <tr key={`${displayCell(row.id)}-${idx}`} className="border-t border-teal-50">
                          <td className="max-w-[12rem] whitespace-normal break-all px-2 py-1 font-mono text-[10px] leading-snug">
                            {displayCell(row.id)}
                          </td>
                          <td className="whitespace-nowrap px-2 py-1">{displayCell(row.kind)}</td>
                          <td className="whitespace-nowrap px-2 py-1">{displayCell(row.execution_state)}</td>
                          <td className="max-w-[10rem] whitespace-normal break-all px-2 py-1 text-stone-700">
                            {displayCell(row.owner_hint)}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
            <div data-testid="manager-insight-execution-graph-edges">
              <h4 className="text-[11px] font-semibold uppercase tracking-wide text-teal-800">Edges</h4>
              <div className="mt-1 overflow-x-auto rounded border border-teal-100">
                <table className="min-w-full border-collapse text-left text-[11px]">
                  <thead className="bg-teal-50/80 text-teal-950">
                    <tr>
                      <th className="border-b border-teal-100 px-2 py-1 font-semibold">id</th>
                      <th className="border-b border-teal-100 px-2 py-1 font-semibold">from_id</th>
                      <th className="border-b border-teal-100 px-2 py-1 font-semibold">to_id</th>
                      <th className="border-b border-teal-100 px-2 py-1 font-semibold">relation</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white text-stone-800">
                    {g.edges.length === 0 ? (
                      <tr>
                        <td className="border-t border-teal-50 px-2 py-2 italic text-stone-500" colSpan={4}>
                          No edges.
                        </td>
                      </tr>
                    ) : (
                      g.edges.map((row, idx) => (
                        <tr key={`${displayCell(row.id)}-${idx}`} className="border-t border-teal-50">
                          <td className="max-w-[9rem] whitespace-normal break-all px-2 py-1 font-mono text-[10px] leading-snug">
                            {displayCell(row.id)}
                          </td>
                          <td className="max-w-[9rem] whitespace-normal break-all px-2 py-1 font-mono text-[10px]">
                            {displayCell(row.from_id)}
                          </td>
                          <td className="max-w-[9rem] whitespace-normal break-all px-2 py-1 font-mono text-[10px]">
                            {displayCell(row.to_id)}
                          </td>
                          <td className="whitespace-nowrap px-2 py-1">{displayCell(row.relation)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <div className="mt-4" data-testid="manager-insight-execution-graph-unresolved">
            <h4 className="text-[11px] font-semibold uppercase tracking-wide text-teal-800">
              unresolved_dependency_refs
            </h4>
            {g.unresolved_dependency_refs.length === 0 ? (
              <p className="mt-1 text-xs text-stone-500">None</p>
            ) : (
              <ul className="mt-1 list-inside list-disc space-y-0.5 text-xs text-stone-800">
                {g.unresolved_dependency_refs.map((s) => (
                  <li key={s} className="font-mono">
                    {s}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      ) : null}
      <details className="mt-3 rounded-md border border-teal-100 bg-teal-50/40 p-2" data-testid="manager-insight-execution-graph-raw-json">
        <summary className="cursor-pointer text-xs font-semibold text-teal-950 marker:text-teal-800">
          Expand raw execution_graph JSON
        </summary>
        <pre className="mt-2 max-h-56 overflow-auto rounded-md border border-teal-100 bg-white p-3 text-xs text-stone-800">
          {JSON.stringify(raw, null, 2)}
        </pre>
      </details>
    </div>
  );
}

export default function AdminTenantManagerInsightPage() {
  const { tenantId = "" } = useParams<{ tenantId: string }>();
  const [appendPerceptionRegexQuery, setAppendPerceptionRegexQuery] = useState(false);
  const [appendIncludeExecutionGraphQuery, setAppendIncludeExecutionGraphQuery] = useState(false);
  /** §6 Step 32 — append `persist_decisions=1` to persist capped prioritized rows to PostgreSQL. */
  const [appendPersistDecisionsQuery, setAppendPersistDecisionsQuery] = useState(false);
  /** §6 Steps 35–36 — skip P7 / P8 narrative bundles entirely (faster QA; stricter than skip_llm fallbacks). */
  const [appendSkipInterpretationsQuery, setAppendSkipInterpretationsQuery] = useState(false);
  const [appendSkipInsightsQuery, setAppendSkipInsightsQuery] = useState(false);
  /** §6 Step 28 — optional `?max_decisions=` (empty = omit; server uses env default, usually 3). */
  const [maxDecisionsQuery, setMaxDecisionsQuery] = useState("");
  /** Default on: request-scoped §6 coordination path (perception LLM, execution_graph, gaps graph) — no P7/P8 LLM. */
  const [fullCoordinationDebug, setFullCoordinationDebug] = useState(true);

  /** §6 Step 33 — query params for persisted-decisions list API. */
  const [persistListLimit, setPersistListLimit] = useState("50");
  const [persistListOffset, setPersistListOffset] = useState("0");
  const [persistListStatus, setPersistListStatus] = useState("");
  const [persistListDecisionType, setPersistListDecisionType] = useState("");
  const [persistListGapType, setPersistListGapType] = useState("");
  const [persistListGapId, setPersistListGapId] = useState("");
  const [persistListRunId, setPersistListRunId] = useState("");
  /** §6 Step 39 — query params for persisted-outcomes list API. */
  const [outcomesListLimit, setOutcomesListLimit] = useState("50");
  const [outcomesListOffset, setOutcomesListOffset] = useState("0");
  /** §6 Step 37 — dry-run apply preview for one persisted row. */
  const [applyDryRunPreview, setApplyDryRunPreview] = useState<{
    decisionId: string;
    body: ManagerInsightApplyDryRunResponse;
  } | null>(null);
  const [applyDryRunError, setApplyDryRunError] = useState<string | null>(null);
  const [applyDryRunLoadingId, setApplyDryRunLoadingId] = useState<string | null>(null);
  /** §6 Step 38 — staging acknowledgement before enabling Apply live. */
  const [applyLiveStagingAck, setApplyLiveStagingAck] = useState(false);
  const [applyLivePreview, setApplyLivePreview] = useState<{
    decisionId: string;
    body: ManagerInsightApplyLiveResponse;
  } | null>(null);
  const [applyLiveError, setApplyLiveError] = useState<string | null>(null);
  const [applyLiveLoadingId, setApplyLiveLoadingId] = useState<string | null>(null);
  /** §6 Step 40 — dismiss outcome + decision status. */
  const [dismissPreview, setDismissPreview] = useState<{
    decisionId: string;
    body: ManagerInsightDismissDecisionResponse;
  } | null>(null);
  const [dismissError, setDismissError] = useState<string | null>(null);
  const [dismissLoadingId, setDismissLoadingId] = useState<string | null>(null);
  /** §6 Step 41 — batch ground_truth evaluation. */
  const [evaluatePreview, setEvaluatePreview] = useState<ManagerInsightEvaluateOutcomesResponse | null>(null);
  const [evaluateError, setEvaluateError] = useState<string | null>(null);
  const [evaluateLoading, setEvaluateLoading] = useState(false);
  const [advancedDebugTab, setAdvancedDebugTab] = useState<
    "perception" | "graph" | "decisions" | "signals" | "pipeline"
  >("pipeline");

  const q = useQuery({
    queryKey: [
      "admin-manager-insight-fetch",
      tenantId,
      appendPerceptionRegexQuery,
      appendIncludeExecutionGraphQuery,
      appendPersistDecisionsQuery,
      appendSkipInterpretationsQuery,
      appendSkipInsightsQuery,
      fullCoordinationDebug,
      maxDecisionsQuery,
    ],
    queryFn: () => {
      const params = new URLSearchParams({ window_days: "30" });
      if (appendPerceptionRegexQuery) {
        params.set("perception", "regex");
      }
      if (appendIncludeExecutionGraphQuery) {
        params.set("include_execution_graph", "1");
      }
      if (fullCoordinationDebug) {
        params.set("master_plan_debug", "1");
      }
      if (appendPersistDecisionsQuery) {
        params.set("persist_decisions", "1");
      }
      if (appendSkipInterpretationsQuery) {
        params.set("skip_interpretations", "1");
      }
      if (appendSkipInsightsQuery) {
        params.set("skip_insights", "1");
      }
      const rawMax = maxDecisionsQuery.trim();
      if (rawMax !== "") {
        const n = Number.parseInt(rawMax, 10);
        if (!Number.isNaN(n) && n >= 1) {
          params.set("max_decisions", String(Math.min(n, 50)));
        }
      }
      return adminJson<ManagerInsightFetchDebugResponse>(
        `/admin/tenants/${tenantId}/manager-insight/fetch-debug?${params.toString()}`,
      );
    },
    enabled: false,
  });

  const persistedListQ = useQuery({
    queryKey: [
      "admin-manager-insight-decisions-list",
      tenantId,
      persistListLimit,
      persistListOffset,
      persistListStatus,
      persistListDecisionType,
      persistListGapType,
      persistListGapId,
      persistListRunId,
    ],
    queryFn: () => {
      const p = new URLSearchParams();
      const lim = parsePersistedListLimit(persistListLimit);
      p.set("limit", String(lim));
      const off = parsePersistedListOffset(persistListOffset);
      p.set("offset", String(off));
      const st = persistListStatus.trim();
      if (st !== "") {
        p.set("status", st);
      }
      const dt = persistListDecisionType.trim();
      if (dt !== "") {
        p.set("decision_type", dt);
      }
      const gt = persistListGapType.trim();
      if (gt !== "") {
        p.set("gap_type", gt);
      }
      const gid = persistListGapId.trim();
      if (gid !== "") {
        p.set("gap_id", gid);
      }
      const rid = persistListRunId.trim();
      if (rid !== "") {
        p.set("run_id", rid);
      }
      return adminJson<ManagerInsightPersistedDecisionsListResponse>(
        `/admin/tenants/${tenantId}/manager-insight/decisions?${p.toString()}`,
      );
    },
    enabled: false,
  });

  const outcomesListQ = useQuery({
    queryKey: ["admin-manager-insight-outcomes-list", tenantId, outcomesListLimit, outcomesListOffset],
    queryFn: () => {
      const p = new URLSearchParams();
      const lim = parsePersistedListLimit(outcomesListLimit);
      p.set("limit", String(lim));
      const off = parsePersistedListOffset(outcomesListOffset);
      p.set("offset", String(off));
      return adminJson<ManagerInsightPersistedOutcomesListResponse>(
        `/admin/tenants/${tenantId}/manager-insight/outcomes?${p.toString()}`,
      );
    },
    enabled: false,
  });

  const persistedPager = persistedListQ.data
    ? (() => {
        const { total, limit: lim, offset: off } = persistedListQ.data;
        const lastOff = lastPageOffset(total, lim);
        return {
          total,
          lim,
          off,
          returned: persistedListQ.data.items.length,
          canFirst: off > 0,
          canPrev: off > 0,
          canNext: off + lim < total,
          canLast: total > 0 && lastOff !== off,
          lastOff,
        };
      })()
    : null;

  const outcomesPager = outcomesListQ.data
    ? (() => {
        const { total, limit: lim, offset: off } = outcomesListQ.data;
        const lastOff = lastPageOffset(total, lim);
        return {
          total,
          lim,
          off,
          returned: outcomesListQ.data.items.length,
          canFirst: off > 0,
          canPrev: off > 0,
          canNext: off + lim < total,
          canLast: total > 0 && lastOff !== off,
          lastOff,
        };
      })()
    : null;

  const applyBusy =
    applyDryRunLoadingId !== null ||
    applyLiveLoadingId !== null ||
    dismissLoadingId !== null ||
    evaluateLoading;

  const fetchApplyDryRunPreview = async (decisionId: string) => {
    setApplyDryRunError(null);
    setApplyLiveError(null);
    setApplyDryRunLoadingId(decisionId);
    try {
      const body = await adminJson<ManagerInsightApplyDryRunResponse>(
        `/admin/tenants/${tenantId}/manager-insight/decisions/${decisionId}/apply`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ dry_run: true }),
        },
      );
      setApplyDryRunPreview({ decisionId, body });
    } catch (err) {
      setApplyDryRunPreview(null);
      setApplyDryRunError(err instanceof Error ? err.message : String(err));
    } finally {
      setApplyDryRunLoadingId(null);
    }
  };

  const fetchApplyLive = async (decisionId: string) => {
    if (!applyLiveStagingAck) {
      setApplyLiveError("Check the staging acknowledgement box first (§6 Step 38).");
      return;
    }
    setApplyDryRunError(null);
    setApplyLiveError(null);
    setApplyLiveLoadingId(decisionId);
    try {
      const body = await adminJson<ManagerInsightApplyLiveResponse>(
        `/admin/tenants/${tenantId}/manager-insight/decisions/${decisionId}/apply`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ dry_run: false }),
        },
      );
      setApplyLivePreview({ decisionId, body });
      setApplyDryRunPreview(null);
      void persistedListQ.refetch();
    } catch (err) {
      setApplyLivePreview(null);
      setApplyLiveError(err instanceof Error ? err.message : String(err));
    } finally {
      setApplyLiveLoadingId(null);
    }
  };

  const fetchEvaluateOutcomes = async (reset: boolean) => {
    setEvaluateError(null);
    setEvaluateLoading(true);
    try {
      const body = await adminJson<ManagerInsightEvaluateOutcomesResponse>(
        `/admin/tenants/${tenantId}/manager-insight/evaluate-outcomes`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ limit: 50, reset }),
        },
      );
      setEvaluatePreview(body);
      void outcomesListQ.refetch();
    } catch (err) {
      setEvaluatePreview(null);
      setEvaluateError(err instanceof Error ? err.message : String(err));
    } finally {
      setEvaluateLoading(false);
    }
  };

  const fetchDismissDecision = async (decisionId: string) => {
    setDismissError(null);
    setApplyDryRunError(null);
    setApplyLiveError(null);
    setDismissLoadingId(decisionId);
    try {
      const body = await adminJson<ManagerInsightDismissDecisionResponse>(
        `/admin/tenants/${tenantId}/manager-insight/decisions/${decisionId}/dismiss`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        },
      );
      setDismissPreview({ decisionId, body });
      setApplyDryRunPreview(null);
      setApplyLivePreview(null);
      void persistedListQ.refetch();
      void outcomesListQ.refetch();
    } catch (err) {
      setDismissPreview(null);
      setDismissError(err instanceof Error ? err.message : String(err));
    } finally {
      setDismissLoadingId(null);
    }
  };

  if (!tenantId) {
    return null;
  }

  return (
    <div className="min-h-screen space-y-8 bg-slate-50/80 pb-16 pt-2">
      <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm ring-1 ring-slate-200/40">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-slate-900">Execution Run Viewer</h1>
            <p className="mt-1 text-sm text-slate-600">
              <span className="font-medium text-slate-800">Manager insight</span> · Coordination §6{" "}
              <span className="tabular-nums">
                {COORDINATION_SECTION6.stepsDone}/{COORDINATION_SECTION6.stepsTotal}
              </span>{" "}
              micro-steps. Run a fetch to populate the execution summary; expand{" "}
              <span className="font-medium text-slate-800">Fetch parameters</span> for flags and QA notes.
            </p>
          </div>
          <button
            type="button"
            className="shrink-0 rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white shadow-md transition hover:bg-slate-800 disabled:opacity-50"
            disabled={q.isFetching}
            onClick={() => {
              void q.refetch();
            }}
          >
            {q.isFetching ? "Running pipeline…" : "Run execution pipeline"}
          </button>
        </div>
        <details className="mt-5 rounded-xl border border-slate-100 bg-slate-50/60 p-3" data-testid="manager-insight-fetch-params">
          <summary className="cursor-pointer text-sm font-semibold text-slate-800">
            Fetch parameters &amp; toggles
          </summary>
          <div className="mt-3 space-y-3 border-t border-slate-200/80 pt-3">
        <details
          className="mt-2 rounded-md border border-stone-200 bg-stone-50/80 p-2"
          data-testid="manager-insight-qa-notes-details"
        >
          <summary className="cursor-pointer text-xs font-semibold text-stone-800">
            §6 QA notes &amp; implementation hints
          </summary>
          <div className="mt-2 space-y-1 border-t border-stone-200 pt-2">
        <p
          className="text-xs text-slate-700"
          data-testid="manager-insight-step30-persistence-note"
        >
          §6 Step 30: PostgreSQL table <code className="text-[11px]">manager_insight_decisions</code> (§5.1) is created by
          Alembic <code className="text-[11px]">20260430_0026</code>. Run{" "}
          <code className="text-[11px]">alembic upgrade head</code> on the API database to apply; ORM + inserts ship in §6
          Step 31–32 (no new fetch-debug fields from this step alone).
        </p>
        <p className="mt-1 text-xs text-slate-700" data-testid="manager-insight-step31-orm-note">
          §6 Step 31: ORM <code className="text-[11px]">ManagerInsightDecision</code> + repository{" "}
          <code className="text-[11px]">insert_decisions_bulk</code> /{" "}
          <code className="text-[11px]">insert_decision_items_bulk</code> in{" "}
          <code className="text-[11px]">vector.infrastructure.db.repositories.manager_insight_decisions</code> — maps{" "}
          <code className="text-[11px]">DecisionItem</code> → rows (deterministic UUID from tenant + engine id). Upsert path
          in §6 Step 32.
        </p>
        <p className="mt-1 text-xs text-slate-700" data-testid="manager-insight-step32-persist-note">
          §6 Step 32: With <code className="text-[11px]">?persist_decisions=1</code>, fetch-debug upserts the capped{" "}
          <span className="font-mono text-xs">decisions_prioritized</span> list into{" "}
          <code className="text-[11px]">manager_insight_decisions</code> (<code className="text-[11px]">upsert_decision_items_bulk</code>
          ). Response <span className="font-mono text-xs">persisted_decision_ids</span> lists deterministic PKs in surface order;
          <span className="font-mono text-xs"> perception_qa.query_persist_decisions</span> echoes the query flag.
        </p>
        <p className="mt-1 text-xs text-slate-700" data-testid="manager-insight-step33-list-api-note">
          §6 Step 33: <code className="text-[11px]">GET /admin/tenants/{"{tenant}"}/manager-insight/decisions</code> lists rows from{" "}
          <code className="text-[11px]">manager_insight_decisions</code> with <code className="text-[11px]">limit</code>,{" "}
          <code className="text-[11px]">offset</code>, and optional exact-match filters{" "}
          <code className="text-[11px]">status</code>, <code className="text-[11px]">decision_type</code>,{" "}
          <code className="text-[11px]">gap_type</code>, <code className="text-[11px]">run_id</code>. Optional{" "}
          <code className="text-[11px]">gap_id</code> ships in §6 Step 34. Expand <span className="font-medium text-stone-800">Persisted decisions</span>{" "}
          in the Execution Run Viewer card (requires admin password in the app).
        </p>
        <p className="mt-1 text-xs text-slate-700" data-testid="manager-insight-step34-persisted-view-note">
          §6 Step 34: Persisted decisions view — paging controls, parity columns (<code className="text-[11px]">id</code>,{" "}
          <code className="text-[11px]">gap_id</code>, <code className="text-[11px]">run_id</code>), copy-id, and a parity hint vs
          fetch-debug <span className="font-mono text-xs">persisted_decision_ids</span> when a debug run is loaded.
        </p>
        <p className="mt-1 text-xs text-slate-700" data-testid="manager-insight-step35-skip-narrative-note">
          §6 Step 35 (API): <code className="text-[11px]">?skip_interpretations=1</code> /{" "}
          <code className="text-[11px]">?skip_insights=1</code> on fetch-debug skip P7/P8 generators entirely (empty bundles,
          stricter than narrative fallbacks). Response <span className="font-mono text-xs">perception_qa</span> echoes the
          flags.
        </p>
        <p className="mt-1 text-xs text-slate-700" data-testid="manager-insight-step36-skip-narrative-note">
          §6 Step 36 (admin): Use the checkboxes below to append those query params without hand-editing the URL. After a run,
          confirm teal <span className="font-mono text-xs">interpretations</span> / <span className="font-mono text-xs">insights</span>{" "}
          JSON and amber <span className="font-mono text-xs">perception_qa</span> badges (
          <code className="text-[11px]">manager-insight-query-skip-interpretations-badge</code>,{" "}
          <code className="text-[11px]">manager-insight-query-skip-insights-badge</code>).
        </p>
        <p className="mt-1 text-xs text-slate-700" data-testid="manager-insight-step37-apply-note">
          §6 Step 37: <code className="text-[11px]">POST /admin/tenants/{"{tenant}"}/manager-insight/decisions/{"{id}"}/apply</code> with body{" "}
          <code className="text-[11px]">{"{ \"dry_run\": true }"}</code> returns the planned payload only (no Slack/connector I/O). In{" "}
          <span className="font-medium text-stone-800">Persisted decisions</span>, use row <strong>Preview</strong> (
          <code className="text-[11px]">manager-insight-persisted-row-apply-preview-*</code>) and expand the teal panel (
          <code className="text-[11px]">manager-insight-persisted-apply-dry-run-panel</code>).
        </p>
        <p className="mt-1 text-xs text-amber-950" data-testid="manager-insight-step38-apply-note">
          §6 Step 38: same POST with <code className="text-[11px]">{"{ \"dry_run\": false }"}</code> when the API has{" "}
          <code className="text-[11px]">VECTOR_MANAGER_INSIGHTS_LIVE_APPLY_ENABLED=1</code> — runs Slack{" "}
          <code className="text-[11px]">post_message</code> (or <code className="text-[11px]">noop</code>) and persists{" "}
          <code className="text-[11px]">receipt</code>. Admin: acknowledge staging, then <strong>Apply live</strong> (
          <code className="text-[11px]">manager-insight-persisted-row-apply-live-*</code>); panel{" "}
          <code className="text-[11px]">manager-insight-persisted-apply-live-panel</code>.
        </p>
        <p className="mt-1 text-xs text-slate-700" data-testid="manager-insight-step39-outcomes-note">
          §6 Step 39: Alembic <code className="text-[11px]">20260430_0027</code> adds{" "}
          <code className="text-[11px]">manager_insight_outcomes</code> and{" "}
          <code className="text-[11px]">manager_insight_policy_counters</code> (§5.2–§5.3). Admin:{" "}
          <code className="text-[11px]">GET /admin/tenants/{"{tenant}"}/manager-insight/outcomes</code> — expand{" "}
          <span className="font-medium text-stone-800">Persisted outcomes</span> (
          <code className="text-[11px]">manager-insight-outcomes-view-step39</code>). Policy counters have no list route yet;
          verify in SQL or integration tests.
        </p>
        <p className="mt-1 text-xs text-slate-700" data-testid="manager-insight-step40-dismiss-note">
          §6 Step 40: <code className="text-[11px]">POST /admin/tenants/{"{tenant}"}/manager-insight/decisions/{"{id}"}/dismiss</code>{" "}
          inserts <code className="text-[11px]">manager_insight_outcomes</code> (<code className="text-[11px]">outcome_type=dismissed</code>) and sets
          the decision row <code className="text-[11px]">status</code> to <code className="text-[11px]">dismissed</code>. Admin:{" "}
          <strong>Dismiss</strong> in <span className="font-medium text-stone-800">Persisted decisions</span> (
          <code className="text-[11px]">manager-insight-persisted-row-dismiss-*</code>); teal panel{" "}
          <code className="text-[11px]">manager-insight-persisted-dismiss-panel</code>. Repeat POST returns{" "}
          <code className="text-[11px]">idempotent: true</code> with the same outcome id.
        </p>
        <p className="mt-1 text-xs text-slate-700" data-testid="manager-insight-step41-evaluate-note">
          §6 Step 41: <code className="text-[11px]">POST /admin/tenants/{"{tenant}"}/manager-insight/evaluate-outcomes</code>{" "}
          merges deterministic flags into <code className="text-[11px]">ground_truth</code> (see{" "}
          <code className="text-[11px]">vector.domains.manager_insights.evaluate_outcomes</code>,{" "}
          <code className="text-[11px]">step41_v0</code>). Admin: expand <span className="font-medium text-stone-800">Persisted outcomes</span> →{" "}
          <strong>Evaluate outcomes</strong> / <strong>Re-run (reset)</strong> (
          <code className="text-[11px]">manager-insight-outcomes-evaluate-incremental</code>,{" "}
          <code className="text-[11px]">manager-insight-outcomes-evaluate-reset</code>); JSON panel{" "}
          <code className="text-[11px]">manager-insight-outcomes-evaluate-panel</code>.
        </p>
        <p className="mt-2 text-xs text-teal-800">
          §6 Step 4: TypeScript types in this file mirror <code className="text-[11px]">manager_insights_activity</code>{" "}
          (literal unions, evidence <code className="text-[11px]">linked_work_items</code>, reliability{" "}
          <code className="text-[11px]">metrics</code>). CI gate:{" "}
          <code className="text-[11px]">npx tsc --noEmit</code>.
        </p>
        <p className="mt-1 text-xs text-stone-600">
          §6 Step 6: After a run, <span className="font-medium text-stone-800">Coordination settings</span> shows{" "}
          <code className="text-[11px]">perception_llm</code>, <code className="text-[11px]">include_execution_graph</code>,{" "}
          <code className="text-[11px]">skip_narrative_steps</code>, <code className="text-[11px]">gaps_use_graph</code>{" "}
          from the server env (defaults off; §6 Step 18 wires graph merge into <span className="font-mono text-xs">compute_gaps</span>).{" "}
          This admin run already skips narrative OpenAI on <span className="font-mono text-xs">{PIPELINE.p7}/{PIPELINE.p8}</span>. Set{" "}
          <code className="text-[11px]">VECTOR_MANAGER_INSIGHTS_*</code> for other flags.
        </p>
        <p className="mt-1 text-xs text-stone-600">
          §6 Step 7: <span className="font-medium text-stone-800">perception_row_example</span> in the contract reference block mirrors the{" "}
          <code className="text-[11px]">PerceptionRow</code> contract (LLM path); live <span className="font-mono text-xs">perception</span>{" "}
          JSON ships with §6 Steps 10–11 (pipeline + admin QA).
        </p>
        <p className="mt-1 text-xs text-stone-600">
          §6 Step 8: <span className="font-medium text-stone-800">perception_validation_demo</span> runs{" "}
          <code className="text-[11px]">validate_perception_rows</code> on fixed fixtures — expect{" "}
          <span className="tabular-nums">1</span> accepted / <span className="tabular-nums">4</span> rejected (
          duplicate, bad quote, unknown work item, schema).
        </p>
        <p className="mt-1 text-xs text-stone-600">
          §6 Step 9: <span className="font-medium text-stone-800">perception_execution_state_demo</span> shows{" "}
          <span className="font-mono text-xs">perceive_execution_state</span> parse output from an internal stub LLM (no network).
        </p>
        <p className="mt-1 text-xs text-stone-600">
          §6 Step 10: When <span className="font-medium text-stone-800">perception_llm</span> is <strong>on</strong>, the live{" "}
          <span className="font-mono text-xs">perception</span> object fills after work items (LLM + validation); turn on{" "}
          <code className="text-[11px]">VECTOR_MANAGER_INSIGHTS_PERCEPTION_LLM</code> and restart the API. Regex evidence (
          <span className="font-mono text-xs">extract_evidence</span>) is unchanged.
        </p>
        <p className="mt-1 text-xs text-stone-600">
          §6 Step 11: Run QA shows <span className="font-medium text-stone-800">perception_qa</span> (flag-driven path
          label + optional <code className="text-[11px]">?perception=regex</code> echo). Raw{" "}
          <span className="font-mono text-xs">perception</span> / <span className="font-mono text-xs">rejected_perception_rows</span>{" "}
          JSON is behind expanders. Use the checkbox below to append the query param on the next run.
        </p>
        <p className="mt-1 text-xs text-stone-600">
          §6 Step 12: <span className="font-mono text-xs">{PIPELINE.p4}</span> linking consumes{" "}
          <span className="font-medium text-stone-800">CoordinationLinkInputBundle</span> — Step-3{" "}
          <span className="font-mono text-xs">evidence</span> plus validated{" "}
          <span className="font-mono text-xs">PerceptionRow</span> text when <span className="font-mono text-xs">perception_llm</span>{" "}
          is on. The semantic links header shows <span className="font-mono text-xs">perception_rows_used_for_linking</span>.
        </p>
          </div>
        </details>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <label className="flex max-w-xl cursor-pointer items-start gap-2 text-xs text-stone-700">
            <input
              type="checkbox"
              className="mt-0.5 rounded border-stone-300 text-emerald-700 focus:ring-emerald-600"
              checked={fullCoordinationDebug}
              onChange={(e) => {
                setFullCoordinationDebug(e.target.checked);
              }}
              data-testid="manager-insight-full-coordination-debug"
            />
            <span>
              <span className="font-semibold text-stone-800">Full coordination debug</span> (
              <span className="font-mono text-[11px]">master_plan_debug=1</span>) — for this run only: §6 perception LLM
              on, <span className="font-mono text-[11px]">execution_graph</span> attached, graph merged into gaps. Leaves
              legacy {PIPELINE.p7}/{PIPELINE.p8} on fallbacks (no narrative LLM). Uncheck to rely on server env flags only.
            </span>
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-xs text-stone-700">
            <input
              type="checkbox"
              className="rounded border-stone-300 text-teal-700 focus:ring-teal-600"
              checked={appendPerceptionRegexQuery}
              onChange={(e) => {
                setAppendPerceptionRegexQuery(e.target.checked);
              }}
              data-testid="manager-insight-append-perception-regex-query"
            />
            Append <code className="text-[11px]">perception=regex</code> to fetch-debug URL (QA label only)
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-xs text-stone-700">
            <input
              type="checkbox"
              className="rounded border-stone-300 text-teal-700 focus:ring-teal-600"
              checked={appendIncludeExecutionGraphQuery}
              onChange={(e) => {
                setAppendIncludeExecutionGraphQuery(e.target.checked);
              }}
              data-testid="manager-insight-append-include-execution-graph-query"
            />
            Also append <code className="text-[11px]">include_execution_graph=1</code> (redundant when full coordination is
            on; use if full coordination is off)
          </label>
          <label className="flex flex-wrap items-center gap-2 text-xs text-stone-700">
            <span className="shrink-0">§6 Step 28 — optional</span>
            <code className="rounded bg-stone-100 px-1 text-[11px]">max_decisions=</code>
            <input
              type="text"
              inputMode="numeric"
              placeholder="(default)"
              className="w-20 rounded border border-stone-300 px-2 py-1 text-stone-800 tabular-nums"
              value={maxDecisionsQuery}
              onChange={(e) => {
                setMaxDecisionsQuery(e.target.value);
              }}
              data-testid="manager-insight-max-decisions-query"
              title="Leave empty for server default (Coordination settings). Integer 1–50."
            />
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-xs text-stone-700">
            <input
              type="checkbox"
              className="rounded border-stone-300 text-violet-700 focus:ring-violet-600"
              checked={appendPersistDecisionsQuery}
              onChange={(e) => {
                setAppendPersistDecisionsQuery(e.target.checked);
              }}
              data-testid="manager-insight-append-persist-decisions-query"
            />
            §6 Step 32 — append <code className="text-[11px]">persist_decisions=1</code> (upsert capped surface to DB)
          </label>
          <div
            className="flex w-full flex-wrap items-center gap-3 border-t border-dashed border-stone-200 pt-2"
            data-testid="manager-insight-step36-fetch-debug-skip-controls"
          >
            <label className="flex cursor-pointer items-center gap-2 text-xs text-stone-700">
              <input
                type="checkbox"
                className="rounded border-stone-300 text-amber-700 focus:ring-amber-600"
                checked={appendSkipInterpretationsQuery}
                onChange={(e) => {
                  setAppendSkipInterpretationsQuery(e.target.checked);
                }}
                data-testid="manager-insight-append-skip-interpretations-query"
              />
              §6 Step 36 — append <code className="text-[11px]">skip_interpretations=1</code> (skip P7 entirely)
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-xs text-stone-700">
              <input
                type="checkbox"
                className="rounded border-stone-300 text-amber-700 focus:ring-amber-600"
                checked={appendSkipInsightsQuery}
                onChange={(e) => {
                  setAppendSkipInsightsQuery(e.target.checked);
                }}
                data-testid="manager-insight-append-skip-insights-query"
              />
              §6 Step 36 — append <code className="text-[11px]">skip_insights=1</code> (skip P8 entirely)
            </label>
          </div>
        </div>
          </div>
        </details>

        <details
          className="mt-4 rounded-xl border border-violet-200/80 bg-violet-50/30 shadow-sm ring-1 ring-violet-100/60"
          data-testid="manager-insight-persisted-view-step34"
        >
          <summary className="cursor-pointer list-none px-4 py-3 marker:text-violet-700 [&::-webkit-details-marker]:hidden">
            <span className="text-sm font-semibold text-violet-950">Persisted decisions (database)</span>
            <span className="mt-1 block text-xs font-normal text-violet-900/90">
              Read-only list from <code className="rounded bg-white/80 px-1 text-[11px]">GET …/manager-insight/decisions</code>
              ; per-row <span className="font-medium text-violet-950">Preview</span> / <span className="font-medium text-amber-950">Apply live</span> /{" "}
              <span className="font-medium text-slate-800">Dismiss</span> call{" "}
              <code className="rounded bg-white/80 px-1 text-[11px]">POST …/decisions/{"{id}"}/apply</code> (
              <code className="text-[11px]">dry_run: true</code> or gated <code className="text-[11px]">false</code> +{" "}
              <code className="text-[11px]">VECTOR_MANAGER_INSIGHTS_LIVE_APPLY_ENABLED</code>) or{" "}
              <code className="rounded bg-white/80 px-1 text-[11px]">POST …/decisions/{"{id}"}/dismiss</code> (§6 Step 40). Requires{" "}
              <code className="rounded bg-white/80 px-1 text-[11px]">ADMIN_PASSWORD</code> in the admin client —{" "}
              <span className="font-medium text-violet-950">expand to use.</span>
            </span>
          </summary>
          <div className="border-t border-violet-100/80 px-4 pb-4 pt-3">
        {q.data && q.data.persisted_decision_ids.length > 0 ? (
          <p
            className="mt-2 rounded-md border border-teal-200 bg-teal-50/60 px-2 py-1.5 text-[11px] text-teal-950"
            data-testid="manager-insight-persisted-parity-hint"
          >
            <span className="font-medium text-teal-900">Parity (§6 Step 34):</span> the loaded fetch-debug run reported{" "}
            <span className="font-mono tabular-nums">{q.data.persisted_decision_ids.length}</span>{" "}
            <span className="font-mono text-[10px]">persisted_decision_ids</span>. Load this list with empty filters; each
            row’s <span className="font-mono text-[10px]">id</span> should appear in that list (same tenant, after Step 32
            persist).
          </p>
        ) : null}
        <div className="mt-3 flex flex-wrap items-end gap-3 text-xs text-stone-700">
          <label className="flex flex-col gap-0.5">
            <span className="font-medium text-stone-800">limit</span>
            <input
              type="text"
              inputMode="numeric"
              className="w-16 rounded border border-stone-300 px-2 py-1 font-mono tabular-nums"
              value={persistListLimit}
              onChange={(e) => {
                setPersistListLimit(e.target.value);
              }}
              data-testid="manager-insight-persisted-list-limit"
            />
          </label>
          <label className="flex flex-col gap-0.5">
            <span className="font-medium text-stone-800">offset</span>
            <input
              type="text"
              inputMode="numeric"
              className="w-16 rounded border border-stone-300 px-2 py-1 font-mono tabular-nums"
              value={persistListOffset}
              onChange={(e) => {
                setPersistListOffset(e.target.value);
              }}
              data-testid="manager-insight-persisted-list-offset"
            />
          </label>
          <label className="flex min-w-[6rem] flex-col gap-0.5">
            <span className="font-medium text-stone-800">status</span>
            <input
              type="text"
              className="rounded border border-stone-300 px-2 py-1 font-mono text-[11px]"
              placeholder="(any)"
              value={persistListStatus}
              onChange={(e) => {
                setPersistListStatus(e.target.value);
              }}
              data-testid="manager-insight-persisted-list-filter-status"
            />
          </label>
          <label className="flex min-w-[8rem] flex-col gap-0.5">
            <span className="font-medium text-stone-800">decision_type</span>
            <input
              type="text"
              className="rounded border border-stone-300 px-2 py-1 font-mono text-[11px]"
              placeholder="(any)"
              value={persistListDecisionType}
              onChange={(e) => {
                setPersistListDecisionType(e.target.value);
              }}
              data-testid="manager-insight-persisted-list-filter-decision-type"
            />
          </label>
          <label className="flex min-w-[8rem] flex-col gap-0.5">
            <span className="font-medium text-stone-800">gap_type</span>
            <input
              type="text"
              className="rounded border border-stone-300 px-2 py-1 font-mono text-[11px]"
              placeholder="(any)"
              value={persistListGapType}
              onChange={(e) => {
                setPersistListGapType(e.target.value);
              }}
              data-testid="manager-insight-persisted-list-filter-gap-type"
            />
          </label>
          <label className="flex min-w-[8rem] flex-col gap-0.5">
            <span className="font-medium text-stone-800">gap_id</span>
            <input
              type="text"
              className="rounded border border-stone-300 px-2 py-1 font-mono text-[11px]"
              placeholder="(any)"
              value={persistListGapId}
              onChange={(e) => {
                setPersistListGapId(e.target.value);
              }}
              data-testid="manager-insight-persisted-list-filter-gap-id"
            />
          </label>
          <label className="flex min-w-[14rem] flex-col gap-0.5">
            <span className="font-medium text-stone-800">run_id</span>
            <input
              type="text"
              className="rounded border border-stone-300 px-2 py-1 font-mono text-[11px]"
              placeholder="(any)"
              value={persistListRunId}
              onChange={(e) => {
                setPersistListRunId(e.target.value);
              }}
              data-testid="manager-insight-persisted-list-filter-run-id"
            />
          </label>
          <button
            type="button"
            className="rounded-lg border border-violet-300 bg-violet-100 px-3 py-2 text-sm font-medium text-violet-950 hover:bg-violet-200 disabled:opacity-50"
            disabled={persistedListQ.isFetching}
            onClick={() => {
              void persistedListQ.refetch();
            }}
            data-testid="manager-insight-persisted-list-load"
          >
            {persistedListQ.isFetching ? "Loading…" : "Load persisted rows"}
          </button>
        </div>
        {persistedListQ.isError ? (
          <p className="mt-2 text-sm text-rose-700" role="alert">
            {(persistedListQ.error as Error).message}
          </p>
        ) : null}
        {persistedListQ.data ? (
          <div className="mt-4 space-y-2">
            <p className="text-xs text-stone-600" data-testid="manager-insight-persisted-list-summary">
              <span className="font-medium text-stone-800">total</span>{" "}
              <span className="font-mono tabular-nums">{persistedListQ.data.total}</span>
              {" · "}
              <span className="font-medium text-stone-800">limit</span>{" "}
              <span className="font-mono tabular-nums">{persistedListQ.data.limit}</span>
              {" · "}
              <span className="font-medium text-stone-800">offset</span>{" "}
              <span className="font-mono tabular-nums">{persistedListQ.data.offset}</span>
              {" · "}
              <span className="font-medium text-stone-800">returned</span>{" "}
              <span className="font-mono tabular-nums">{persistedListQ.data.items.length}</span>
              {persistedPager && persistedPager.total > 0 ? (
                <>
                  {" · "}
                  <span className="font-medium text-stone-800">rows</span>{" "}
                  <span className="font-mono tabular-nums">
                    {persistedPager.off + 1}–{persistedPager.off + persistedPager.returned}
                  </span>
                  <span className="text-stone-500"> of </span>
                  <span className="font-mono tabular-nums">{persistedPager.total}</span>
                </>
              ) : null}
            </p>
            {applyDryRunError ? (
              <p
                className="text-xs text-rose-700"
                role="alert"
                data-testid="manager-insight-persisted-apply-dry-run-error"
              >
                {applyDryRunError}
              </p>
            ) : null}
            {applyLiveError ? (
              <p
                className="text-xs text-rose-800"
                role="alert"
                data-testid="manager-insight-persisted-apply-live-error"
              >
                {applyLiveError}
              </p>
            ) : null}
            {dismissError ? (
              <p className="text-xs text-rose-800" role="alert" data-testid="manager-insight-persisted-dismiss-error">
                {dismissError}
              </p>
            ) : null}
            {persistedListQ.data.items.length > 0 ? (
              <label
                className="flex max-w-xl cursor-pointer items-start gap-2 rounded-md border border-amber-200 bg-amber-50/80 px-2 py-2 text-[11px] text-amber-950"
                data-testid="manager-insight-step38-live-apply-ack-label"
              >
                <input
                  type="checkbox"
                  className="mt-0.5 rounded border-amber-400 text-amber-800 focus:ring-amber-600"
                  checked={applyLiveStagingAck}
                  onChange={(e) => {
                    setApplyLiveStagingAck(e.target.checked);
                  }}
                  data-testid="manager-insight-step38-live-apply-ack"
                />
                <span>
                  §6 Step 38 — I understand <strong>Apply live</strong> can post to Slack (or persist a noop receipt). The API
                  must have <code className="text-[10px]">VECTOR_MANAGER_INSIGHTS_LIVE_APPLY_ENABLED=1</code>.
                </span>
              </label>
            ) : null}
            {persistedListQ.data.items.length > 0 ? (
              <p className="text-[11px] text-stone-500" data-testid="manager-insight-persisted-status-breakdown">
                By status (this page):{" "}
                {Object.entries(
                  persistedListQ.data.items.reduce<Record<string, number>>((acc, r) => {
                    const k = r.status;
                    acc[k] = (acc[k] ?? 0) + 1;
                    return acc;
                  }, {}),
                )
                  .map(([k, v]) => `${k}=${v}`)
                  .join(" · ")}
              </p>
            ) : null}
            {persistedPager ? (
              <div
                className="flex flex-wrap items-center gap-2 text-xs text-stone-700"
                data-testid="manager-insight-persisted-list-pager"
              >
                <button
                  type="button"
                  className="rounded border border-violet-200 bg-white px-2 py-1 font-medium text-violet-900 hover:bg-violet-50 disabled:cursor-not-allowed disabled:opacity-40"
                  disabled={!persistedPager.canFirst || persistedListQ.isFetching}
                  onClick={() => {
                    flushSync(() => {
                      setPersistListOffset("0");
                    });
                    void persistedListQ.refetch();
                  }}
                  data-testid="manager-insight-persisted-pager-first"
                >
                  First
                </button>
                <button
                  type="button"
                  className="rounded border border-violet-200 bg-white px-2 py-1 font-medium text-violet-900 hover:bg-violet-50 disabled:cursor-not-allowed disabled:opacity-40"
                  disabled={!persistedPager.canPrev || persistedListQ.isFetching}
                  onClick={() => {
                    flushSync(() => {
                      setPersistListOffset(String(Math.max(0, persistedPager.off - persistedPager.lim)));
                    });
                    void persistedListQ.refetch();
                  }}
                  data-testid="manager-insight-persisted-pager-prev"
                >
                  Prev
                </button>
                <button
                  type="button"
                  className="rounded border border-violet-200 bg-white px-2 py-1 font-medium text-violet-900 hover:bg-violet-50 disabled:cursor-not-allowed disabled:opacity-40"
                  disabled={!persistedPager.canNext || persistedListQ.isFetching}
                  onClick={() => {
                    flushSync(() => {
                      setPersistListOffset(String(persistedPager.off + persistedPager.lim));
                    });
                    void persistedListQ.refetch();
                  }}
                  data-testid="manager-insight-persisted-pager-next"
                >
                  Next
                </button>
                <button
                  type="button"
                  className="rounded border border-violet-200 bg-white px-2 py-1 font-medium text-violet-900 hover:bg-violet-50 disabled:cursor-not-allowed disabled:opacity-40"
                  disabled={!persistedPager.canLast || persistedListQ.isFetching}
                  onClick={() => {
                    flushSync(() => {
                      setPersistListOffset(String(persistedPager.lastOff));
                    });
                    void persistedListQ.refetch();
                  }}
                  data-testid="manager-insight-persisted-pager-last"
                >
                  Last
                </button>
              </div>
            ) : null}
            <div className="overflow-x-auto rounded-md border border-violet-100 bg-white shadow-sm">
              <table
                className="w-full min-w-[60rem] border-collapse text-left text-xs text-stone-800"
                data-testid="manager-insight-persisted-list-table"
              >
                <thead>
                  <tr className="border-b border-violet-100 bg-violet-50/80">
                    <th className="max-w-[11rem] px-2 py-2 font-semibold">id</th>
                    <th className="w-[1%] px-2 py-2 font-semibold">copy</th>
                    <th className="w-[1%] px-2 py-2 font-semibold">actions</th>
                    <th className="px-2 py-2 font-semibold">gap_id</th>
                    <th className="max-w-[9rem] px-2 py-2 font-semibold">run_id</th>
                    <th className="px-2 py-2 font-semibold">rank</th>
                    <th className="px-2 py-2 font-semibold">decision_type</th>
                    <th className="px-2 py-2 font-semibold">gap_type</th>
                    <th className="px-2 py-2 font-semibold">status</th>
                    <th className="px-2 py-2 font-semibold">title</th>
                    <th className="px-2 py-2 font-semibold">updated_at</th>
                    <th className="w-[1%] px-2 py-2 font-semibold">JSON</th>
                  </tr>
                </thead>
                <tbody>
                  {persistedListQ.data.items.length === 0 ? (
                    <tr>
                      <td className="px-2 py-3 italic text-stone-500" colSpan={12}>
                        No rows for this tenant / filters.
                      </td>
                    </tr>
                  ) : (
                    persistedListQ.data.items.map((row, idx) => (
                      <Fragment key={row.id}>
                        <tr className="border-b border-violet-50 last:border-b-0">
                        <td className="max-w-[11rem] break-all px-2 py-2 font-mono text-[10px] text-stone-800">{row.id}</td>
                        <td className="whitespace-nowrap px-2 py-2">
                          <button
                            type="button"
                            className="text-[11px] font-medium text-violet-800 underline decoration-violet-300"
                            onClick={() => {
                              copyTextToClipboard(row.id);
                            }}
                            data-testid={`manager-insight-persisted-row-copy-id-${idx}`}
                          >
                            Copy id
                          </button>
                        </td>
                        <td className="whitespace-nowrap px-2 py-2 align-top">
                          <div className="flex flex-col gap-1">
                            <button
                              type="button"
                              className="text-left text-[11px] font-medium text-teal-800 underline decoration-teal-300 disabled:cursor-not-allowed disabled:opacity-40"
                              disabled={applyBusy}
                              onClick={() => {
                                void fetchApplyDryRunPreview(row.id);
                              }}
                              data-testid={`manager-insight-persisted-row-apply-preview-${idx}`}
                            >
                              {applyDryRunLoadingId === row.id ? "…" : "Preview"}
                            </button>
                            <button
                              type="button"
                              className="text-left text-[11px] font-medium text-amber-900 underline decoration-amber-400 disabled:cursor-not-allowed disabled:opacity-40"
                              disabled={applyBusy || !applyLiveStagingAck}
                              title={
                                applyLiveStagingAck
                                  ? "POST apply with dry_run=false (staging)"
                                  : "Check the staging acknowledgement above first"
                              }
                              onClick={() => {
                                void fetchApplyLive(row.id);
                              }}
                              data-testid={`manager-insight-persisted-row-apply-live-${idx}`}
                            >
                              {applyLiveLoadingId === row.id ? "…" : "Apply live"}
                            </button>
                            <button
                              type="button"
                              className="text-left text-[11px] font-medium text-slate-700 underline decoration-slate-400 disabled:cursor-not-allowed disabled:opacity-40"
                              disabled={applyBusy}
                              onClick={() => {
                                void fetchDismissDecision(row.id);
                              }}
                              data-testid={`manager-insight-persisted-row-dismiss-${idx}`}
                            >
                              {dismissLoadingId === row.id ? "…" : "Dismiss"}
                            </button>
                          </div>
                        </td>
                        <td className="px-2 py-2 font-mono text-[11px]">{row.gap_id}</td>
                        <td className="max-w-[9rem] break-all px-2 py-2 font-mono text-[10px] text-stone-700">{row.run_id}</td>
                        <td className="px-2 py-2 font-mono text-[11px] tabular-nums">{row.rank ?? "—"}</td>
                        <td className="px-2 py-2 font-mono text-[11px]">{row.decision_type}</td>
                        <td className="px-2 py-2 font-mono text-[11px]">{row.gap_type}</td>
                        <td className="px-2 py-2 font-mono text-[11px]">{row.status}</td>
                        <td className="max-w-[12rem] px-2 py-2 text-stone-900">{row.title}</td>
                        <td className="whitespace-nowrap px-2 py-2 font-mono text-[10px] text-stone-600">
                          {row.updated_at}
                        </td>
                        <td className="px-2 py-2 align-top">
                          <details className="group/rowjson max-w-xs">
                            <summary className="cursor-pointer list-none text-[11px] font-medium text-violet-900 underline decoration-violet-300 underline-offset-2 marker:content-none [&::-webkit-details-marker]:hidden">
                              Expand
                            </summary>
                            <pre className="mt-2 max-h-56 overflow-auto rounded border border-violet-100 bg-stone-50 p-2 text-[10px] leading-snug text-stone-800">
                              {JSON.stringify(row, null, 2)}
                            </pre>
                          </details>
                        </td>
                        </tr>
                        {applyDryRunPreview?.decisionId === row.id ? (
                          <tr className="border-b border-violet-50 bg-teal-50/40 last:border-b-0">
                            <td
                              className="px-2 py-3"
                              colSpan={12}
                              data-testid="manager-insight-persisted-apply-dry-run-panel"
                            >
                              <p className="mb-2 text-[11px] font-medium text-teal-950">
                                §6 Step 37 — apply dry-run response (no external I/O)
                              </p>
                              <pre className="max-h-64 overflow-auto rounded border border-teal-100 bg-white p-2 text-[10px] leading-snug text-stone-800">
                                {JSON.stringify(applyDryRunPreview.body, null, 2)}
                              </pre>
                            </td>
                          </tr>
                        ) : null}
                        {applyLivePreview?.decisionId === row.id ? (
                          <tr className="border-b border-violet-50 bg-amber-50/50 last:border-b-0">
                            <td
                              className="px-2 py-3"
                              colSpan={12}
                              data-testid="manager-insight-persisted-apply-live-panel"
                            >
                              <p className="mb-2 text-[11px] font-medium text-amber-950">
                                §6 Step 38 — live apply response (receipt persisted on row)
                              </p>
                              <pre className="max-h-64 overflow-auto rounded border border-amber-200 bg-white p-2 text-[10px] leading-snug text-stone-800">
                                {JSON.stringify(applyLivePreview.body, null, 2)}
                              </pre>
                            </td>
                          </tr>
                        ) : null}
                        {dismissPreview?.decisionId === row.id ? (
                          <tr className="border-b border-violet-50 bg-teal-50/40 last:border-b-0">
                            <td
                              className="px-2 py-3"
                              colSpan={12}
                              data-testid="manager-insight-persisted-dismiss-panel"
                            >
                              <p className="mb-2 text-[11px] font-medium text-teal-950">
                                §6 Step 40 — dismiss response (outcome row + decision status)
                                {dismissPreview.body.idempotent ? (
                                  <span className="ml-2 font-mono text-[10px] text-teal-800">
                                    idempotent replay
                                  </span>
                                ) : null}
                              </p>
                              <pre className="max-h-64 overflow-auto rounded border border-teal-100 bg-white p-2 text-[10px] leading-snug text-stone-800">
                                {JSON.stringify(dismissPreview.body, null, 2)}
                              </pre>
                            </td>
                          </tr>
                        ) : null}
                      </Fragment>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}
          </div>
        </details>

        <details
          className="mt-4 rounded-xl border border-emerald-200/80 bg-emerald-50/25 shadow-sm ring-1 ring-emerald-100/60"
          data-testid="manager-insight-outcomes-view-step39"
        >
          <summary className="cursor-pointer list-none px-4 py-3 marker:text-emerald-700 [&::-webkit-details-marker]:hidden">
            <span className="text-sm font-semibold text-emerald-950">Persisted outcomes (database)</span>
            <span className="mt-1 block text-xs font-normal text-emerald-900/90">
              Read-only list from{" "}
              <code className="rounded bg-white/80 px-1 text-[11px]">GET …/manager-insight/outcomes</code> (§6 Step 39).
              Requires <code className="rounded bg-white/80 px-1 text-[11px]">ADMIN_PASSWORD</code> — expand to use.
            </span>
          </summary>
          <div className="border-t border-emerald-100/80 px-4 pb-4 pt-3">
            <div className="mt-1 flex flex-wrap items-end gap-3 text-xs text-stone-700">
              <label className="flex flex-col gap-0.5">
                <span className="font-medium text-stone-800">limit</span>
                <input
                  type="text"
                  inputMode="numeric"
                  className="w-16 rounded border border-stone-300 px-2 py-1 font-mono tabular-nums"
                  value={outcomesListLimit}
                  onChange={(e) => {
                    setOutcomesListLimit(e.target.value);
                  }}
                  data-testid="manager-insight-outcomes-list-limit"
                />
              </label>
              <label className="flex flex-col gap-0.5">
                <span className="font-medium text-stone-800">offset</span>
                <input
                  type="text"
                  inputMode="numeric"
                  className="w-16 rounded border border-stone-300 px-2 py-1 font-mono tabular-nums"
                  value={outcomesListOffset}
                  onChange={(e) => {
                    setOutcomesListOffset(e.target.value);
                  }}
                  data-testid="manager-insight-outcomes-list-offset"
                />
              </label>
              <button
                type="button"
                className="rounded-lg bg-emerald-800 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-emerald-900 disabled:opacity-50"
                disabled={outcomesListQ.isFetching}
                onClick={() => {
                  void outcomesListQ.refetch();
                }}
                data-testid="manager-insight-outcomes-list-load"
              >
                {outcomesListQ.isFetching ? "Loading…" : "Load outcome rows"}
              </button>
              <button
                type="button"
                className="rounded-lg border border-emerald-700 bg-white px-3 py-1.5 text-xs font-semibold text-emerald-900 shadow-sm hover:bg-emerald-50 disabled:opacity-50"
                disabled={evaluateLoading}
                onClick={() => {
                  void fetchEvaluateOutcomes(false);
                }}
                data-testid="manager-insight-outcomes-evaluate-incremental"
              >
                {evaluateLoading ? "Evaluating…" : "Evaluate outcomes"}
              </button>
              <button
                type="button"
                className="rounded-lg border border-amber-600 bg-amber-50/90 px-3 py-1.5 text-xs font-semibold text-amber-950 shadow-sm hover:bg-amber-100 disabled:opacity-50"
                disabled={evaluateLoading}
                onClick={() => {
                  void fetchEvaluateOutcomes(true);
                }}
                data-testid="manager-insight-outcomes-evaluate-reset"
              >
                Re-run (reset rules)
              </button>
            </div>
            {evaluateError ? (
              <p className="mt-2 text-sm text-rose-800" role="alert" data-testid="manager-insight-outcomes-evaluate-error">
                {evaluateError}
              </p>
            ) : null}
            {evaluatePreview ? (
              <div
                className="mt-3 rounded-md border border-teal-200 bg-teal-50/50 p-3"
                data-testid="manager-insight-outcomes-evaluate-panel"
              >
                <p className="mb-2 text-[11px] font-medium text-teal-950">
                  §6 Step 41 — evaluate-outcomes response (processed / skipped / scanned)
                </p>
                <pre className="max-h-64 overflow-auto rounded border border-teal-100 bg-white p-2 text-[10px] leading-snug text-stone-800">
                  {JSON.stringify(evaluatePreview, null, 2)}
                </pre>
              </div>
            ) : null}
            {outcomesListQ.isError ? (
              <p className="mt-2 text-sm text-rose-700" role="alert">
                {(outcomesListQ.error as Error).message}
              </p>
            ) : null}
            {outcomesListQ.data ? (
              <div className="mt-4 space-y-2">
                <p className="text-xs text-stone-600" data-testid="manager-insight-outcomes-list-summary">
                  <span className="font-medium text-stone-800">total</span>{" "}
                  <span className="font-mono tabular-nums">{outcomesListQ.data.total}</span>
                  {" · "}
                  <span className="font-medium text-stone-800">limit</span>{" "}
                  <span className="font-mono tabular-nums">{outcomesListQ.data.limit}</span>
                  {" · "}
                  <span className="font-medium text-stone-800">offset</span>{" "}
                  <span className="font-mono tabular-nums">{outcomesListQ.data.offset}</span>
                  {" · "}
                  <span className="font-medium text-stone-800">returned</span>{" "}
                  <span className="font-mono tabular-nums">{outcomesListQ.data.items.length}</span>
                </p>
                {outcomesPager && outcomesPager.total > 0 ? (
                  <div
                    className="flex flex-wrap items-center gap-2 text-xs text-stone-700"
                    data-testid="manager-insight-outcomes-list-pager"
                  >
                    <button
                      type="button"
                      className="rounded border border-emerald-200 bg-white px-2 py-1 font-medium text-emerald-900 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-40"
                      disabled={!outcomesPager.canFirst || outcomesListQ.isFetching}
                      onClick={() => {
                        flushSync(() => {
                          setOutcomesListOffset("0");
                        });
                        void outcomesListQ.refetch();
                      }}
                      data-testid="manager-insight-outcomes-pager-first"
                    >
                      First
                    </button>
                    <button
                      type="button"
                      className="rounded border border-emerald-200 bg-white px-2 py-1 font-medium text-emerald-900 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-40"
                      disabled={!outcomesPager.canPrev || outcomesListQ.isFetching}
                      onClick={() => {
                        flushSync(() => {
                          setOutcomesListOffset(String(Math.max(0, outcomesPager.off - outcomesPager.lim)));
                        });
                        void outcomesListQ.refetch();
                      }}
                      data-testid="manager-insight-outcomes-pager-prev"
                    >
                      Prev
                    </button>
                    <button
                      type="button"
                      className="rounded border border-emerald-200 bg-white px-2 py-1 font-medium text-emerald-900 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-40"
                      disabled={!outcomesPager.canNext || outcomesListQ.isFetching}
                      onClick={() => {
                        flushSync(() => {
                          setOutcomesListOffset(String(outcomesPager.off + outcomesPager.lim));
                        });
                        void outcomesListQ.refetch();
                      }}
                      data-testid="manager-insight-outcomes-pager-next"
                    >
                      Next
                    </button>
                    <button
                      type="button"
                      className="rounded border border-emerald-200 bg-white px-2 py-1 font-medium text-emerald-900 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-40"
                      disabled={!outcomesPager.canLast || outcomesListQ.isFetching}
                      onClick={() => {
                        flushSync(() => {
                          setOutcomesListOffset(String(outcomesPager.lastOff));
                        });
                        void outcomesListQ.refetch();
                      }}
                      data-testid="manager-insight-outcomes-pager-last"
                    >
                      Last
                    </button>
                  </div>
                ) : null}
                <div className="overflow-x-auto rounded-md border border-emerald-100 bg-white shadow-sm">
                  <table
                    className="w-full min-w-[48rem] border-collapse text-left text-xs text-stone-800"
                    data-testid="manager-insight-outcomes-list-table"
                  >
                    <thead>
                      <tr className="border-b border-emerald-100 bg-emerald-50/80">
                        <th className="max-w-[11rem] px-2 py-2 font-semibold">id</th>
                        <th className="w-[1%] px-2 py-2 font-semibold">copy</th>
                        <th className="max-w-[11rem] px-2 py-2 font-semibold">decision_id</th>
                        <th className="px-2 py-2 font-semibold">outcome_type</th>
                        <th className="px-2 py-2 font-semibold">observed_at</th>
                        <th className="px-2 py-2 font-semibold">false_positive</th>
                        <th className="px-2 py-2 font-semibold">user_attribution</th>
                        <th className="w-[1%] px-2 py-2 font-semibold">JSON</th>
                      </tr>
                    </thead>
                    <tbody>
                      {outcomesListQ.data.items.length === 0 ? (
                        <tr>
                          <td className="px-2 py-3 italic text-stone-500" colSpan={8}>
                            No outcome rows for this tenant yet — use <strong>Dismiss</strong> on a persisted decision (§6
                            Step 40) then reload, or seed via integration tests.
                          </td>
                        </tr>
                      ) : (
                        outcomesListQ.data.items.map((row, idx) => (
                          <tr key={row.id} className="border-b border-emerald-50 last:border-b-0">
                            <td className="max-w-[11rem] break-all px-2 py-2 font-mono text-[10px] text-stone-800">
                              {row.id}
                            </td>
                            <td className="whitespace-nowrap px-2 py-2">
                              <button
                                type="button"
                                className="text-[11px] font-medium text-emerald-800 underline decoration-emerald-300"
                                onClick={() => {
                                  copyTextToClipboard(row.id);
                                }}
                                data-testid={`manager-insight-outcomes-row-copy-id-${idx}`}
                              >
                                Copy id
                              </button>
                            </td>
                            <td className="max-w-[11rem] break-all px-2 py-2 font-mono text-[10px] text-stone-700">
                              {row.decision_id}
                            </td>
                            <td className="px-2 py-2 font-mono text-[11px]">{row.outcome_type}</td>
                            <td className="whitespace-nowrap px-2 py-2 font-mono text-[10px] text-stone-600">
                              {row.observed_at}
                            </td>
                            <td className="px-2 py-2 font-mono text-[11px]">
                              {row.false_positive === null ? "—" : String(row.false_positive)}
                            </td>
                            <td className="max-w-[8rem] truncate px-2 py-2 text-stone-800">
                              {row.user_attribution ?? "—"}
                            </td>
                            <td className="px-2 py-2 align-top">
                              <details className="group/rowjson max-w-xs">
                                <summary className="cursor-pointer list-none text-[11px] font-medium text-emerald-900 underline decoration-emerald-300 underline-offset-2 marker:content-none [&::-webkit-details-marker]:hidden">
                                  Expand
                                </summary>
                                <pre className="mt-2 max-h-56 overflow-auto rounded border border-emerald-100 bg-stone-50 p-2 text-[10px] leading-snug text-stone-800">
                                  {JSON.stringify(row, null, 2)}
                                </pre>
                              </details>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}
          </div>
        </details>
      </div>

      {q.isLoading ? <p className="text-sm text-stone-600">Loading…</p> : null}
      {q.isError ? (
        <p className="text-sm text-rose-700" role="alert">
          {(q.error as Error).message}
        </p>
      ) : null}
      {!q.data && !q.isFetching && !q.isError ? (
        <p className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm">
          No execution run loaded yet. Use <span className="font-medium text-slate-800">Run execution pipeline</span> above
          to fetch and populate the summary.
        </p>
      ) : null}

      {q.data ? (
        <div className="mx-auto max-w-6xl space-y-16" data-testid="manager-insight-fetch-debug-body">
          <ManagerInsightPipelineExecutionTimeline data={q.data} />
          <ExecutionGapsSummary data={q.data} />
          <ExecutionSignalsWhySection data={q.data} />
          <PrioritizedDecisionsSpotlight data={q.data} />

          <details
            className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/70 p-6 shadow-sm"
            data-testid="manager-insight-advanced-debug"
          >
            <summary className="cursor-pointer list-none marker:text-slate-400">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400">Section 5 · Developer tools</p>
              <p className="mt-2 text-base font-semibold text-slate-900">Advanced debug</p>
              <span className="mt-1 block text-sm font-normal text-slate-500">
                Raw payloads, QA blocks, full pipeline tables, and tabbed JSON — separate from the operator readout above.
              </span>
            </summary>
            <div className="mt-6 border-t border-slate-200/80 pt-6">
              <div className="flex flex-wrap gap-2 border-b border-slate-200/80 pb-4" role="tablist" aria-label="Advanced debug views">
                {(
                  [
                    ["perception", "Perception"],
                    ["graph", "Graph"],
                    ["decisions", "Decisions JSON"],
                    ["signals", "Signals JSON"],
                    ["pipeline", "Full pipeline"],
                  ] as const
                ).map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    role="tab"
                    aria-selected={advancedDebugTab === id}
                    className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                      advancedDebugTab === id
                        ? "bg-slate-900 text-white shadow-sm"
                        : "bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
                    }`}
                    onClick={() => {
                      setAdvancedDebugTab(id);
                    }}
                    data-testid={`manager-insight-advanced-tab-${id}`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              <div className="mt-6 space-y-6">
                {advancedDebugTab === "perception" ? (
                  <div className="space-y-4" data-testid="manager-insight-advanced-panel-perception">
                    <p className="text-sm text-slate-600">
                      Perception QA flags and path echo. Raw JSON is available to copy; the full Run QA card also appears in
                      the Full pipeline tab.
                    </p>
                    <CopyJsonButton
                      label="Copy perception_qa JSON"
                      value={q.data.perception_qa}
                      data-testid="manager-insight-copy-perception-qa-json-advanced"
                    />
                    <pre className="max-h-[32rem] overflow-auto rounded-xl border border-slate-200 bg-white p-4 text-xs text-slate-800 shadow-inner">
                      {JSON.stringify(q.data.perception_qa, null, 2)}
                    </pre>
                  </div>
                ) : null}
                {advancedDebugTab === "graph" ? (
                  <div className="space-y-4" data-testid="manager-insight-advanced-panel-graph">
                    <CopyJsonButton
                      label="Copy execution_graph JSON"
                      value={q.data.execution_graph}
                      data-testid="manager-insight-copy-execution-graph-json-advanced"
                    />
                    <ExecutionGraphFourFiveSection raw={q.data.execution_graph} />
                    <pre className="max-h-64 overflow-auto rounded-xl border border-slate-200 bg-slate-950 p-4 text-xs text-slate-100">
                      {JSON.stringify(q.data.execution_graph, null, 2)}
                    </pre>
                  </div>
                ) : null}
                {advancedDebugTab === "decisions" ? (
                  <div className="space-y-4" data-testid="manager-insight-advanced-panel-decisions-json">
                    <div className="flex flex-wrap gap-2">
                      <CopyJsonButton label="Copy decisions JSON" value={q.data.decisions} data-testid="manager-insight-copy-decisions-json-advanced" />
                      <CopyJsonButton
                        label="Copy decisions_prioritized JSON"
                        value={q.data.decisions_prioritized}
                        data-testid="manager-insight-copy-decisions-prioritized-json-advanced"
                      />
                    </div>
                    <pre className="max-h-[28rem] overflow-auto rounded-xl border border-slate-200 bg-white p-4 text-xs text-slate-800">
                      {JSON.stringify({ decisions: q.data.decisions, decisions_prioritized: q.data.decisions_prioritized }, null, 2)}
                    </pre>
                    {engineDecisionCount(q.data) > 0 && q.data.decisions !== null ? (
                      <CoordinationDecisionsTable items={q.data.decisions.items} />
                    ) : null}
                    {q.data.decisions_prioritized !== null && q.data.decisions_prioritized.length > 0 ? (
                      <PrioritizedDecisionsSurfaceTable items={q.data.decisions_prioritized} />
                    ) : null}
                  </div>
                ) : null}
                {advancedDebugTab === "signals" ? (
                  <div className="space-y-4" data-testid="manager-insight-advanced-panel-signals-json">
                    <pre className="max-h-[32rem] overflow-auto rounded-xl border border-slate-200 bg-white p-4 text-xs text-slate-800">
                      {JSON.stringify(q.data.signals, null, 2)}
                    </pre>
                  </div>
                ) : null}
                {advancedDebugTab === "pipeline" ? (
                  <div className="space-y-6">
          <ManagerInsightPipelineMonitorStrip data={q.data} />
          <section
            className="rounded-lg border border-slate-200 bg-slate-50/80 p-4 shadow-sm"
            data-testid="manager-insight-coordination-settings"
          >
            <h2 className="text-sm font-semibold text-slate-900">
              Coordination settings <span className="font-normal text-slate-500">(§6 Step 6)</span>
            </h2>
            <p className="mt-1 text-xs text-slate-600">
              Feature flags read by the backend process; pipeline behavior wires up in later §6 steps.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {(
                [
                  ["perception_llm", q.data.coordination_settings.perception_llm],
                  ["include_execution_graph", q.data.coordination_settings.include_execution_graph],
                  ["skip_narrative_steps", q.data.coordination_settings.skip_narrative_steps],
                  ["gaps_use_graph", q.data.coordination_settings.gaps_use_graph],
                ] as const
              ).map(([label, on]) => (
                <span
                  key={label}
                  className={`rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${
                    on
                      ? "bg-emerald-50 text-emerald-900 ring-emerald-200"
                      : "bg-stone-100 text-stone-600 ring-stone-200"
                  }`}
                  title={
                    label === "perception_llm"
                      ? "VECTOR_MANAGER_INSIGHTS_PERCEPTION_LLM"
                      : label === "include_execution_graph"
                        ? "VECTOR_MANAGER_INSIGHTS_INCLUDE_EXECUTION_GRAPH"
                        : label === "gaps_use_graph"
                          ? "VECTOR_MANAGER_INSIGHTS_GAPS_USE_GRAPH"
                          : "VECTOR_MANAGER_INSIGHTS_SKIP_NARRATIVE_STEPS"
                  }
                >
                  {label}: {on ? "on" : "off"}
                </span>
              ))}
            </div>
            <p
              className="mt-3 text-xs text-slate-600"
              data-testid="manager-insight-hold-start-threshold"
            >
              HOLD_START cluster threshold:{" "}
              <span className="font-mono tabular-nums">
                {q.data.coordination_settings.hold_start_affected_wi_threshold}
              </span>{" "}
              <span className="text-slate-500">
                (open execution items in gap neighborhood must exceed this; §6 Step 26; env{" "}
                <code className="text-[11px]">VECTOR_MANAGER_INSIGHTS_HOLD_START_AFFECTED_WI_THRESHOLD</code>)
              </span>
            </p>
            <p className="mt-2 text-xs text-slate-600" data-testid="manager-insight-max-decisions-surfaced">
              Default <span className="font-mono text-xs">decisions_prioritized</span> cap (§6 Step 28):{" "}
              <span className="font-mono tabular-nums">{q.data.coordination_settings.max_decisions_surfaced}</span>{" "}
              <span className="text-slate-500">
                (env <code className="text-[11px]">VECTOR_MANAGER_INSIGHTS_MAX_DECISIONS_SURFACED</code>; override with{" "}
                <code className="text-[11px]">?max_decisions=</code>)
              </span>
            </p>
          </section>

          <section className="rounded-lg border border-teal-200 bg-teal-50/30 p-4 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-stone-900">
                  Run QA <span className="font-normal text-teal-700">(perception_qa)</span>
                </h2>
                <p className="mt-1 max-w-3xl text-xs text-stone-600">
                  Effective evidence path and echo of query flags for this fetch-debug response (§6 Steps 11 &amp; 16).
                </p>
              </div>
              <CopyJsonButton
                label="Copy perception_qa JSON"
                value={q.data.perception_qa}
                data-testid="manager-insight-copy-perception-qa-json"
              />
            </div>
            <div className="mt-3 space-y-3">
              <div
                className="rounded-md border border-teal-100 bg-white/90 p-3 shadow-sm"
                data-testid="manager-insight-perception-qa"
              >
                <h3 className="text-xs font-semibold uppercase tracking-wide text-teal-900">
                  perception_qa <span className="font-normal text-teal-700">(§6 Step 11)</span>
                </h3>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span
                    className={`rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${
                      q.data.perception_qa.evidence_path === "llm_perception_plus_regex_evidence"
                        ? "bg-emerald-50 text-emerald-900 ring-emerald-200"
                        : "bg-stone-100 text-stone-700 ring-stone-200"
                    }`}
                    title={
                      q.data.perception_qa.query_master_plan_debug
                        ? "Effective path for this run (master_plan_debug may override env)"
                        : "Derived from coordination_settings.perception_llm at run time"
                    }
                  >
                    {perceptionPathLabel(q.data.perception_qa.evidence_path)}
                  </span>
                  {q.data.perception_qa.query_master_plan_debug ? (
                    <span
                      className="rounded-md bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-950 ring-1 ring-inset ring-emerald-200"
                      data-testid="manager-insight-query-master-plan-debug-badge"
                      title="Fetch used ?master_plan_debug=1"
                    >
                      Query: master_plan_debug
                    </span>
                  ) : null}
                  {q.data.perception_qa.query_perception_regex ? (
                    <span
                      className="rounded-md bg-violet-50 px-2 py-1 text-xs font-medium text-violet-900 ring-1 ring-inset ring-violet-200"
                      data-testid="manager-insight-perception-query-regex-badge"
                      title="Fetch used ?perception=regex (QA hint only)"
                    >
                      Query: perception=regex
                    </span>
                  ) : null}
                  {q.data.perception_qa.query_include_execution_graph ? (
                    <span
                      className="rounded-md bg-sky-50 px-2 py-1 text-xs font-medium text-sky-900 ring-1 ring-inset ring-sky-200"
                      data-testid="manager-insight-query-include-execution-graph-badge"
                      title="Fetch used ?include_execution_graph=1"
                    >
                      Query: include_execution_graph=1
                    </span>
                  ) : null}
                  {q.data.perception_qa.query_max_decisions !== null ? (
                    <span
                      className="rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-950 ring-1 ring-inset ring-amber-200"
                      data-testid="manager-insight-query-max-decisions-badge"
                      title="Fetch used ?max_decisions="
                    >
                      Query: max_decisions={q.data.perception_qa.query_max_decisions}
                    </span>
                  ) : null}
                  {q.data.perception_qa.query_persist_decisions ? (
                    <span
                      className="rounded-md bg-violet-50 px-2 py-1 text-xs font-medium text-violet-950 ring-1 ring-inset ring-violet-200"
                      data-testid="manager-insight-query-persist-decisions-badge"
                      title="Fetch used ?persist_decisions=1"
                    >
                      Query: persist_decisions=1
                    </span>
                  ) : null}
                  {q.data.perception_qa.query_skip_interpretations ? (
                    <span
                      className="rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-950 ring-1 ring-inset ring-amber-200"
                      data-testid="manager-insight-query-skip-interpretations-badge"
                      title="Fetch used ?skip_interpretations=1"
                    >
                      Query: skip_interpretations=1
                    </span>
                  ) : null}
                  {q.data.perception_qa.query_skip_insights ? (
                    <span
                      className="rounded-md bg-amber-50 px-2 py-1 text-xs font-medium text-amber-950 ring-1 ring-inset ring-amber-200"
                      data-testid="manager-insight-query-skip-insights-badge"
                      title="Fetch used ?skip_insights=1"
                    >
                      Query: skip_insights=1
                    </span>
                  ) : null}
                  <span
                    className="rounded-md bg-stone-100 px-2 py-1 text-xs text-stone-700 ring-1 ring-inset ring-stone-200"
                    data-testid="manager-insight-cap-applied-badge"
                    title="Applied cap after Step 27 sort"
                  >
                    Cap applied: {q.data.perception_qa.max_decisions_cap_applied} · full prioritized:{" "}
                    {q.data.perception_qa.decisions_prioritized_full_count}
                  </span>
                  {Object.keys(q.data.perception_qa.step42_gap_demotion_by_gap_type ?? {}).length >
                  0 ? (
                    <span
                      className="rounded-md bg-violet-50 px-2 py-1 text-xs font-medium text-violet-950 ring-1 ring-inset ring-violet-200"
                      data-testid="manager-insight-step42-learning-sort-badge"
                      title="§6 Step 42: non-zero gap demotion from policy/outcomes (see perception_qa JSON)"
                    >
                      Step 42 learning:{" "}
                      {Object.keys(q.data.perception_qa.step42_gap_demotion_by_gap_type).length} gap type(s)
                    </span>
                  ) : null}
                </div>
                <details className="mt-3 rounded-md border border-teal-100 bg-teal-50/40 p-2">
                  <summary className="cursor-pointer text-xs font-semibold text-teal-950 marker:text-teal-800">
                    Expand raw perception_qa JSON
                  </summary>
                  <pre className="mt-2 max-h-48 overflow-auto rounded-md border border-teal-100 bg-white p-3 text-xs text-stone-800">
                    {JSON.stringify(q.data.perception_qa, null, 2)}
                  </pre>
                </details>
              </div>
            </div>
          </section>

          <section
            className="rounded-xl border border-stone-200 bg-gradient-to-b from-white to-emerald-50/20 p-4 shadow-sm"
            data-testid="manager-insight-p05-monitor"
          >
            {(() => {
              const m = monitorP05Health(q.data);
              const lowN = (["slack", "github", "linear", "notion", "calls"] as const).filter(
                (k) => q.data.data_reliability[k].tier === "low",
              ).length;
              return (
                <>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-stone-400">
                        {PIPELINE.p05} · Connector health
                      </p>
                      <h2 className="mt-0.5 text-base font-semibold text-stone-900">Data reliability</h2>
                      <p className="mt-1 max-w-prose text-xs leading-relaxed text-stone-600">{m.why}</p>
                    </div>
                    <MonitorStatusPill health={m.health}>
                      {m.health === "ok"
                        ? "Good"
                        : m.health === "warn"
                          ? "Attention"
                          : m.health === "error"
                            ? "Critical"
                            : "FYI"}
                    </MonitorStatusPill>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-2 lg:grid-cols-4">
                    <MonitorKpi
                      label="Overall confidence"
                      value={q.data.data_reliability.overall_confidence}
                      variant={
                        q.data.data_reliability.overall_confidence === "high"
                          ? "good"
                          : q.data.data_reliability.overall_confidence === "low"
                            ? "bad"
                            : "caution"
                      }
                    />
                    <MonitorKpi
                      label="Sources at low tier"
                      value={lowN}
                      hint="Fewer is better"
                      variant={lowN > 0 ? "caution" : "good"}
                    />
                    <MonitorKpi
                      label="Sources at medium tier"
                      value={
                        (["slack", "github", "linear", "notion", "calls"] as const).filter(
                          (k) => q.data.data_reliability[k].tier === "medium",
                        ).length
                      }
                      variant="neutral"
                    />
                    <MonitorKpi
                      label="Sources at high tier"
                      value={
                        (["slack", "github", "linear", "notion", "calls"] as const).filter(
                          (k) => q.data.data_reliability[k].tier === "high",
                        ).length
                      }
                      variant="good"
                    />
                  </div>
                  <details className="mt-4 rounded-lg border border-stone-200/90 bg-white/80">
                    <summary className="cursor-pointer px-3 py-2.5 text-xs font-semibold text-stone-800">
                      Per-source reasons &amp; diagnostics
                    </summary>
                    <ul className="grid gap-2 border-t border-stone-100 p-3 sm:grid-cols-2 lg:grid-cols-3">
                      {(["slack", "github", "linear", "notion", "calls"] as const).map((key) => {
                        const d = q.data.data_reliability[key];
                        return (
                          <li
                            key={key}
                            className="rounded-lg border border-stone-100 bg-stone-50/90 px-3 py-2 text-sm shadow-sm"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-medium capitalize text-stone-800">{key}</span>
                              {tierBadge(d.tier)}
                            </div>
                            {d.reasons.length ? (
                              <ul className="mt-1.5 list-inside list-disc text-xs text-stone-600">
                                {d.reasons.map((r) => (
                                  <li key={r}>{r}</li>
                                ))}
                              </ul>
                            ) : (
                              <p className="mt-1 text-[11px] text-stone-400">No extra reasons recorded.</p>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                  </details>
                </>
              );
            })()}
          </section>

          <section
            className="rounded-xl border border-stone-200 bg-gradient-to-b from-white to-sky-50/25 p-4 shadow-sm"
            data-testid="manager-insight-p1-monitor"
          >
            {(() => {
              const m = monitorP1Health(q.data);
              const conns = Object.values(q.data.fetch.connectors);
              const errN = conns.filter((c) => c.errors.length > 0).length;
              return (
                <>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-stone-400">
                        {PIPELINE.p1} · Raw fetch
                      </p>
                      <h2 className="mt-0.5 text-base font-semibold text-stone-900">Fetch activity</h2>
                      <p className="mt-1 max-w-prose text-xs leading-relaxed text-stone-600">{m.why}</p>
                      <p className="mt-1 font-mono text-[11px] text-stone-500">run_id {q.data.fetch.run_id}</p>
                    </div>
                    <MonitorStatusPill health={m.health}>
                      {m.health === "ok"
                        ? "Good"
                        : m.health === "warn"
                          ? "Attention"
                          : m.health === "error"
                            ? "Critical"
                            : "FYI"}
                    </MonitorStatusPill>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-2 lg:grid-cols-4">
                    <MonitorKpi label="Connectors" value={conns.length} variant="neutral" />
                    <MonitorKpi
                      label="With errors"
                      value={errN}
                      variant={errN > 0 ? "bad" : "good"}
                      hint="Should be 0"
                    />
                    <MonitorKpi
                      label="Non-ok status"
                      value={conns.filter((c) => c.status !== "ok").length}
                      variant={conns.some((c) => c.status !== "ok") ? "caution" : "good"}
                    />
                    <MonitorKpi label="Window" value={`${q.data.fetch.window_days}d`} variant="neutral" />
                  </div>
                  <details className="mt-4 rounded-lg border border-stone-200/90 bg-white/80">
                    <summary className="cursor-pointer px-3 py-2.5 text-xs font-semibold text-stone-800">
                      Connector payloads &amp; raw JSON
                    </summary>
                    <div className="space-y-3 border-t border-stone-100 p-3">
                      {conns.map((c) => (
                        <details
                          key={c.connector}
                          className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2"
                        >
                          <summary className="cursor-pointer text-sm font-medium text-stone-800">
                            {c.connector}{" "}
                            <span className="font-normal text-stone-500">({c.status})</span>
                          </summary>
                          <dl className="mt-2 grid gap-1 text-xs text-stone-600">
                            <div>
                              <dt className="font-medium text-stone-700">fetched_at</dt>
                              <dd className="font-mono">{c.fetched_at ?? "—"}</dd>
                            </div>
                            <div>
                              <dt className="font-medium text-stone-700">window</dt>
                              <dd className="font-mono">
                                {c.window_start} → {c.window_end}
                              </dd>
                            </div>
                            {c.caps_applied.length ? (
                              <div>
                                <dt className="font-medium text-stone-700">caps_applied</dt>
                                <dd>{c.caps_applied.join(", ")}</dd>
                              </div>
                            ) : null}
                            {c.errors.length ? (
                              <div>
                                <dt className="font-medium text-rose-800">errors</dt>
                                <dd className="text-rose-800">{c.errors.join(" · ")}</dd>
                              </div>
                            ) : null}
                            {c.coverage ? (
                              <div>
                                <dt className="font-medium text-stone-700">coverage</dt>
                                <dd className="font-mono">{JSON.stringify(c.coverage)}</dd>
                              </div>
                            ) : null}
                            {c.completeness ? (
                              <div>
                                <dt className="font-medium text-stone-700">completeness</dt>
                                <dd className="font-mono">{JSON.stringify(c.completeness)}</dd>
                              </div>
                            ) : null}
                          </dl>
                          <pre className="mt-2 max-h-64 overflow-auto rounded bg-stone-900/90 p-2 text-xs text-stone-100">
                            {JSON.stringify(c.payload, null, 2)}
                          </pre>
                        </details>
                      ))}
                    </div>
                  </details>
                </>
              );
            })()}
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm" data-testid="manager-insight-p2-work-items">
            <details className="group" data-testid="manager-insight-p2-work-items-details">
              <summary className="flex cursor-pointer list-none items-start justify-between gap-3 marker:content-none [&::-webkit-details-marker]:hidden">
                <div>
                  <h2 className="text-sm font-semibold text-stone-900">
                    <span className="font-mono font-normal text-stone-500">{PIPELINE.p2}</span> Work items
                  </h2>
                  <p className="mt-1 text-xs text-stone-500">
                    {q.data.work_items.items.length} normalized · run_id {q.data.work_items.run_id}
                  </p>
                </div>
                <span className="shrink-0 pt-0.5 text-xs font-medium text-stone-400 group-open:hidden">Expand list</span>
                <span className="hidden shrink-0 pt-0.5 text-xs font-medium text-stone-400 group-open:inline">
                  Collapse list
                </span>
              </summary>
              <div className="mt-4 border-t border-stone-100 pt-4">
                <div className="space-y-3">
                  {q.data.work_items.items.length === 0 ? (
                    <p className="text-xs text-stone-500">
                      No normalized work items produced from current fetch payloads.
                    </p>
                  ) : null}
                  {q.data.work_items.items.map((item) => (
                    <details
                      key={item.id}
                      className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2"
                    >
                      <summary className="cursor-pointer text-sm font-medium text-stone-800">
                        {item.title}{" "}
                        <span className="font-normal text-stone-500">
                          ({item.source} / {item.type})
                        </span>
                      </summary>
                      <dl className="mt-2 grid gap-1 text-xs text-stone-600">
                        <div>
                          <dt className="font-medium text-stone-700">id</dt>
                          <dd className="font-mono">{item.id}</dd>
                        </div>
                        <div>
                          <dt className="font-medium text-stone-700">status</dt>
                          <dd>{item.status ?? "—"}</dd>
                        </div>
                        <div>
                          <dt className="font-medium text-stone-700">summary</dt>
                          <dd>{item.summary ?? "—"}</dd>
                        </div>
                        <div>
                          <dt className="font-medium text-stone-700">updated_at</dt>
                          <dd className="font-mono">{item.updated_at ?? "—"}</dd>
                        </div>
                      </dl>
                      <pre className="mt-2 max-h-64 overflow-auto rounded bg-stone-900/90 p-2 text-xs text-stone-100">
                        {JSON.stringify(item, null, 2)}
                      </pre>
                    </details>
                  ))}
                </div>
              </div>
            </details>
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm" data-testid="manager-insight-p3-evidence">
            <details className="group" data-testid="manager-insight-p3-evidence-details">
              <summary className="flex cursor-pointer list-none items-start justify-between gap-3 marker:content-none [&::-webkit-details-marker]:hidden">
                <div>
                  <h2 className="text-sm font-semibold text-stone-900">
                    <span className="font-mono font-normal text-stone-500">{PIPELINE.p3}</span> Evidence extraction
                  </h2>
                  <p className="mt-1 text-xs text-stone-500">
                    Action items: {q.data.evidence.action_items.length} · Blockers:{" "}
                    {q.data.evidence.blockers.length} · Evidence decisions: {q.data.evidence.decisions.length} · Discarded
                    (no quote): {q.data.evidence.discarded_without_evidence}
                  </p>
                </div>
                <span className="shrink-0 pt-0.5 text-xs font-medium text-stone-400 group-open:hidden">Expand details</span>
                <span className="hidden shrink-0 pt-0.5 text-xs font-medium text-stone-400 group-open:inline">
                  Collapse details
                </span>
              </summary>
              <div className="mt-4 border-t border-stone-100 pt-4">
                <div className="grid gap-4 lg:grid-cols-3">
                  {(
                    [
                      ["Action items", q.data.evidence.action_items],
                      ["Blockers", q.data.evidence.blockers],
                      ["Decisions", q.data.evidence.decisions],
                    ] as const
                  ).map(([label, rows]) => (
                    <div key={label} className="rounded-md border border-stone-100 bg-stone-50 p-3">
                      <h3 className="text-sm font-semibold text-stone-800">{label}</h3>
                      {rows.length === 0 ? (
                        <p className="mt-2 text-xs text-stone-500">No items extracted.</p>
                      ) : (
                        <ul className="mt-2 space-y-2">
                          {rows.map((row) => (
                            <li key={row.id} className="rounded border border-stone-200 bg-white p-2 text-xs">
                              <p className="font-medium text-stone-800">{row.statement}</p>
                              <p className="mt-1 text-stone-600">Quote: "{row.evidence}"</p>
                              <p className="mt-1 font-mono text-stone-500">{row.source_work_item_id}</p>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </details>
          </section>

          <section
            className="rounded-lg border border-indigo-200 bg-indigo-50/25 p-4 shadow-sm"
            data-testid="manager-insight-graph-perception-phase"
          >
            <details className="group" data-testid="manager-insight-graph-perception-phase-details">
              <summary className="flex cursor-pointer list-none items-start justify-between gap-3 marker:content-none [&::-webkit-details-marker]:hidden">
                <div className="min-w-0 flex-1">
                  <h2 className="text-sm font-semibold text-indigo-950">
                    Execution graph &amp; LLM perception{" "}
                    <span className="font-normal text-indigo-700">(§6 Steps 10–11, 15–17)</span>
                  </h2>
                  <p className="mt-1 text-xs text-indigo-950/90">{graphPerceptionPhaseFoldSummary(q.data)}</p>
                </div>
                <div className="flex shrink-0 items-start gap-3">
                  <div
                    className="flex flex-col items-end gap-2 sm:flex-row"
                    onClick={(e) => {
                      e.stopPropagation();
                    }}
                    onKeyDown={(e) => {
                      e.stopPropagation();
                    }}
                  >
                    <CopyJsonButton
                      label="Copy perception JSON"
                      value={q.data.perception}
                      data-testid="manager-insight-copy-perception-json"
                    />
                    <CopyJsonButton
                      label="Copy rejected_perception_rows"
                      value={q.data.rejected_perception_rows}
                      data-testid="manager-insight-copy-rejected-perception-json"
                    />
                  </div>
                  <span className="pt-0.5 text-xs font-medium text-indigo-700/90 group-open:hidden">Expand section</span>
                  <span className="hidden pt-0.5 text-xs font-medium text-indigo-700/90 group-open:inline">
                    Collapse section
                  </span>
                </div>
              </summary>
              <div className="mt-4 space-y-4 border-t border-indigo-100 pt-4">
                <p className="max-w-3xl text-xs text-indigo-950/85">
                  Optional <span className="font-mono text-[11px]">execution_graph</span> from{" "}
                  <span className="font-mono text-[11px]">build_execution_graph</span>, plus validated perception rows that
                  feed {PIPELINE.p4}/{PIPELINE.p5}/{PIPELINE.p6}. Rejected LLM rows are listed for debugging.
                </p>
                <ExecutionGraphFourFiveSection raw={q.data.execution_graph} />
                <details
                  className="rounded-md border border-indigo-100 bg-white open:border-indigo-200 open:shadow-sm"
                  data-testid="manager-insight-rejected-perception-rows-raw"
                >
                  <summary className="cursor-pointer px-3 py-2 text-xs font-semibold uppercase tracking-wide text-indigo-900 marker:text-indigo-700">
                    rejected_perception_rows ({q.data.rejected_perception_rows.length}) — expand raw JSON
                  </summary>
                  <pre className="max-h-96 overflow-auto border-t border-indigo-100 bg-white p-3 text-xs text-stone-800">
                    {JSON.stringify(q.data.rejected_perception_rows, null, 2)}
                  </pre>
                </details>
                <div data-testid="manager-insight-pipeline-perception">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-indigo-900">
                    perception <span className="font-normal text-indigo-700">(§6 Steps 10–11)</span>
                  </h3>
                  <p className="mt-1 text-xs text-stone-600">
                    Top-level rejected row count:{" "}
                    <span className="font-semibold tabular-nums text-indigo-950">
                      {q.data.rejected_perception_rows.length}
                    </span>
                    .
                    {q.data.perception !== null &&
                    typeof q.data.perception === "object" &&
                    "accepted_count" in q.data.perception ? (
                      <>
                        {" "}
                        Validation summary in JSON:{" "}
                        <span className="font-semibold text-indigo-950 tabular-nums">
                          {String(q.data.perception.accepted_count)} accepted
                        </span>
                        ,{" "}
                        <span className="font-semibold text-indigo-950 tabular-nums">
                          {String(q.data.perception.rejected_count)} rejected
                        </span>
                        .
                      </>
                    ) : (
                      <>
                        {" "}
                        With <span className="font-mono text-xs">perception_llm</span> off,{" "}
                        <span className="font-mono text-xs">perception</span> stays <span className="font-medium">null</span>.
                      </>
                    )}
                  </p>
                  <details
                    className="mt-2 rounded-md border border-indigo-100 bg-white open:border-indigo-200 open:shadow-sm"
                    data-testid="manager-insight-pipeline-perception-raw"
                  >
                    <summary className="cursor-pointer px-3 py-2 text-xs font-semibold text-indigo-950 marker:text-indigo-800">
                      Expand raw perception JSON
                    </summary>
                    <pre className="max-h-[28rem] overflow-auto border-t border-indigo-100 bg-white p-3 text-xs text-stone-800">
                      {JSON.stringify(q.data.perception, null, 2)}
                    </pre>
                  </details>
                </div>
              </div>
            </details>
          </section>

          <section
            className="rounded-xl border border-violet-200/80 bg-gradient-to-b from-white to-violet-50/30 p-4 shadow-sm"
            data-testid="manager-insight-p4-monitor"
          >
            {(() => {
              const m = monitorP4LinksHealth(q.data);
              const links = q.data.links.links;
              const n = links.length;
              const hi = links.filter((L) => L.confidence === "high").length;
              const med = links.filter((L) => L.confidence === "medium").length;
              const low = links.filter((L) => L.confidence === "low").length;
              const pct = (x: number) => (n === 0 ? 0 : Math.round((x / n) * 100));
              const topPreview = [...links]
                .sort((a, b) => b.similarity - a.similarity)
                .slice(0, 5);
              return (
                <>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-violet-700/90">
                        {PIPELINE.p4} · Cross-tool threading
                      </p>
                      <h2 className="mt-0.5 text-base font-semibold text-stone-900">Semantic links</h2>
                      <p className="mt-1 max-w-prose text-xs leading-relaxed text-stone-600">{m.why}</p>
                    </div>
                    <MonitorStatusPill health={m.health}>
                      {m.health === "ok"
                        ? "Good"
                        : m.health === "warn"
                          ? "Attention"
                          : m.health === "error"
                            ? "Critical"
                            : "FYI"}
                    </MonitorStatusPill>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-2 lg:grid-cols-4">
                    <MonitorKpi label="Total edges" value={n} variant="neutral" />
                    <MonitorKpi label="High confidence" value={hi} hint={`${pct(hi)}% of edges`} variant="good" />
                    <MonitorKpi label="Medium" value={med} variant="caution" />
                    <MonitorKpi label="Low" value={low} variant={low > n * 0.5 ? "caution" : "neutral"} />
                  </div>
                  {n > 0 ? (
                    <div className="mt-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-stone-500">
                        Confidence mix
                      </p>
                      <div className="mt-1 flex h-2.5 overflow-hidden rounded-full bg-stone-200/80">
                        <div
                          className="bg-emerald-500 transition-all"
                          style={{ width: `${pct(hi)}%` }}
                          title={`high ${pct(hi)}%`}
                        />
                        <div
                          className="bg-amber-400 transition-all"
                          style={{ width: `${pct(med)}%` }}
                          title={`medium ${pct(med)}%`}
                        />
                        <div
                          className="bg-stone-400 transition-all"
                          style={{ width: `${pct(low)}%` }}
                          title={`low ${pct(low)}%`}
                        />
                      </div>
                      <p className="mt-1 text-[10px] text-stone-500">
                        Green = high · amber = medium · gray = low (best-effort, not ground truth)
                      </p>
                    </div>
                  ) : null}
                  {topPreview.length > 0 ? (
                    <div className="mt-4 rounded-lg border border-violet-100 bg-white/90 p-3">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-violet-900">
                        Strongest edges (preview)
                      </p>
                      <ul className="mt-2 space-y-2">
                        {topPreview.map((L) => (
                          <li key={L.id} className="text-xs text-stone-800">
                            <span className="font-mono text-[11px]">{L.from_work_item_id}</span>
                            <span className="text-stone-400"> → </span>
                            <span className="font-mono text-[11px]">{L.to_work_item_id}</span>
                            <span className="ml-2 text-stone-500">sim {L.similarity.toFixed(3)}</span>
                            {tierBadge(L.confidence)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  <details className="mt-4 rounded-lg border border-stone-200/90 bg-white/80">
                    <summary className="cursor-pointer px-3 py-2.5 text-xs font-semibold text-stone-800">
                      Full link list &amp; §6 Step 12 metadata
                    </summary>
                    <div className="border-t border-stone-100 p-3 text-xs text-stone-600">
                      <p>
                        run_id {q.data.links.run_id} · perception rows merged:{" "}
                        {q.data.links.perception_rows_used_for_linking}
                        {q.data.links.work_items_capped > 0
                          ? ` · capped to first ${q.data.links.work_items_capped} work items`
                          : ""}
                      </p>
                      {n === 0 ? (
                        <p className="mt-3 text-stone-500">
                          No links above the minimum similarity floor. Add overlapping titles or shared keys across tools.
                        </p>
                      ) : (
                        <ul className="mt-3 max-h-96 space-y-2 overflow-y-auto">
                          {links.map((L) => (
                            <li
                              key={L.id}
                              className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2 text-xs"
                            >
                              <div className="flex flex-wrap items-center gap-2 text-stone-800">
                                <span className="font-mono">{L.from_work_item_id}</span>
                                <span className="text-stone-400">→</span>
                                <span className="font-mono">{L.to_work_item_id}</span>
                                <span className="rounded bg-stone-200/80 px-1.5 py-0.5 text-[10px] uppercase text-stone-600">
                                  {L.link_type.replace("_", " ")}
                                </span>
                                {tierBadge(L.confidence)}
                                <span className="text-stone-500">sim {L.similarity.toFixed(3)}</span>
                              </div>
                              <p className="mt-1 text-stone-600">{L.evidence}</p>
                              <p className="mt-0.5 font-mono text-[10px] text-stone-400">{L.method}</p>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </details>
                </>
              );
            })()}
          </section>

          <section
            className="rounded-xl border border-amber-200/90 bg-gradient-to-b from-white to-amber-50/25 p-4 shadow-sm"
            data-testid="manager-insight-gaps-p5"
          >
            {(() => {
              const m = monitorP5GapsHealth(q.data);
              const gaps = q.data.gaps.gaps;
              const nExe = gaps.filter((g) => g.type === "expected_not_executed").length;
              const nDisc = gaps.filter((g) => g.type === "discussed_not_linked_to_work").length;
              const nBlock = gaps.filter((g) => g.type === "blocker_not_tracked").length;
              const nDoc = gaps.filter((g) => g.type === "doc_not_connected_to_execution").length;
              const preview = gaps.slice(0, 4);
              return (
                <>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-amber-800/90">
                        {PIPELINE.p5} · Coordination gaps
                      </p>
                      <h2 className="mt-0.5 text-base font-semibold text-stone-900">Gaps</h2>
                      <p className="mt-1 max-w-prose text-xs leading-relaxed text-stone-600">{m.why}</p>
                    </div>
                    <MonitorStatusPill health={m.health}>
                      {m.health === "ok"
                        ? "Clear"
                        : m.health === "warn"
                          ? "Attention"
                          : m.health === "error"
                            ? "Critical"
                            : "FYI"}
                    </MonitorStatusPill>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-2 lg:grid-cols-5">
                    <MonitorKpi label="Total gaps" value={gaps.length} variant={gaps.length > 0 ? "caution" : "good"} />
                    <MonitorKpi label="Not executed" value={nExe} variant="neutral" />
                    <MonitorKpi label="Discussed not linked" value={nDisc} variant="caution" />
                    <MonitorKpi label="Blocker not tracked" value={nBlock} variant="caution" />
                    <MonitorKpi label="Doc vs execution" value={nDoc} variant="neutral" />
                  </div>
                  {preview.length > 0 ? (
                    <ul className="mt-4 space-y-2 rounded-lg border border-amber-100 bg-white/90 p-3">
                      {preview.map((g) => (
                        <li key={g.id} className="text-xs">
                          <span className="rounded bg-amber-100/90 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-amber-950">
                            {g.type.replace(/_/g, " ")}
                          </span>
                          <p className="mt-1 font-medium text-stone-800">{g.description}</p>
                        </li>
                      ))}
                      {gaps.length > preview.length ? (
                        <p className="text-[11px] text-stone-500">
                          +{gaps.length - preview.length} more in full list below
                        </p>
                      ) : null}
                    </ul>
                  ) : null}
                  <details className="mt-4 rounded-lg border border-stone-200/90 bg-white/80">
                    <summary className="cursor-pointer px-3 py-2.5 text-xs font-semibold text-stone-800">
                      How gaps are computed · §6 Step 18 graph merge · evidence JSON
                    </summary>
                    <div className="space-y-3 border-t border-stone-100 p-3 text-xs text-stone-600">
                      <p>
                        <span className="font-medium text-stone-800">compute_gaps</span> uses the same bundle as P4
                        (evidence + validated perception). Perception text can provide cross-item adjacency; graph merge
                        is optional.
                      </p>
                      <p data-testid="manager-insight-gaps-debug-step18">
                        <span className="font-semibold text-stone-800">§6 Step 18</span>
                        {q.data.gaps.gaps_debug != null && String(q.data.gaps.gaps_debug).length > 0 ? (
                          <>: {q.data.gaps.gaps_debug}</>
                        ) : (
                          <>
                            : Graph adjacency merge is off unless{" "}
                            <code className="text-[11px]">VECTOR_MANAGER_INSIGHTS_GAPS_USE_GRAPH=true</code>.
                          </>
                        )}
                      </p>
                      <p className="font-mono text-[11px] text-stone-500">run_id {q.data.gaps.run_id}</p>
                      {gaps.length === 0 ? (
                        <p className="text-stone-500">No deterministic gaps for this run.</p>
                      ) : (
                        <ul className="max-h-96 space-y-2 overflow-y-auto">
                          {gaps.map((g) => (
                            <li key={g.id} className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2">
                              <div className="flex flex-wrap items-center gap-2 text-stone-800">
                                <span className="rounded bg-stone-200/80 px-1.5 py-0.5 text-[10px] uppercase text-stone-600">
                                  {g.type.replace(/_/g, " ")}
                                </span>
                                <span className="font-mono text-stone-500">{g.id}</span>
                              </div>
                              <p className="mt-1 text-stone-700">{g.description}</p>
                              <pre className="mt-2 max-h-40 overflow-auto rounded bg-stone-900/90 p-2 text-[11px] text-stone-100">
                                {JSON.stringify(g.evidence_pointers, null, 2)}
                              </pre>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </details>
                </>
              );
            })()}
          </section>

          <section
            className="rounded-xl border border-emerald-200/80 bg-gradient-to-b from-white to-emerald-50/20 p-4 shadow-sm"
            data-testid="manager-insight-p55-monitor"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-emerald-900/80">
                  {PIPELINE.p55} · Shipped work
                </p>
                <h2 className="mt-0.5 text-base font-semibold text-stone-900">Key achievements</h2>
                <p className="mt-1 text-xs text-stone-600">
                  Closed issues and merged PRs in the window — shows delivery throughput.
                </p>
              </div>
              <MonitorStatusPill health="info">
                {q.data.key_achievements.items.length} items
              </MonitorStatusPill>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
              <MonitorKpi label="Achievements" value={q.data.key_achievements.items.length} variant="good" />
              <MonitorKpi label="run_id" value={q.data.key_achievements.run_id.slice(0, 8) + "…"} variant="neutral" />
            </div>
            {q.data.key_achievements.items.length === 0 ? (
              <p className="mt-3 text-xs text-stone-500">No closed/merged execution items in window.</p>
            ) : (
              <>
                <ul className="mt-4 space-y-2 rounded-lg border border-emerald-100 bg-white/90 p-3">
                  {q.data.key_achievements.items.slice(0, 5).map((k) => (
                    <li key={k.id} className="border-b border-emerald-50 pb-2 text-xs last:border-b-0 last:pb-0">
                      <p className="font-medium text-stone-900">{k.title}</p>
                      <p className="mt-0.5 text-[11px] text-stone-500">{k.linked_items.slice(0, 3).join(", ")}</p>
                    </li>
                  ))}
                </ul>
                <details className="mt-3 rounded-lg border border-stone-200 bg-stone-50/60">
                  <summary className="cursor-pointer px-3 py-2 text-xs font-semibold text-stone-800">
                    All achievements + evidence lines
                  </summary>
                  <ul className="max-h-96 space-y-2 overflow-y-auto border-t border-stone-200 p-3">
                    {q.data.key_achievements.items.map((k) => (
                      <li key={k.id} className="rounded-md border border-stone-100 bg-white px-3 py-2 text-xs">
                        <p className="font-medium text-stone-800">{k.title}</p>
                        <p className="mt-0.5 font-mono text-[10px] text-stone-500">{k.id}</p>
                        <p className="mt-1 text-stone-600">Linked: {k.linked_items.join(", ")}</p>
                        <ul className="mt-1 list-inside list-disc text-stone-600">
                          {k.evidence.map((e) => (
                            <li key={e} className="text-[11px]">
                              {e}
                            </li>
                          ))}
                        </ul>
                      </li>
                    ))}
                  </ul>
                </details>
              </>
            )}
          </section>

          <section
            className="rounded-xl border border-cyan-200/80 bg-gradient-to-b from-white to-cyan-50/25 p-4 shadow-sm"
            data-testid="manager-insight-p56-monitor"
          >
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-cyan-900/80">
                  {PIPELINE.p56} · Factual snippets
                </p>
                <h2 className="mt-0.5 text-base font-semibold text-stone-900">Raw highlights</h2>
                <p className="mt-1 text-xs text-stone-600">Short factual lines extracted for signal inputs.</p>
              </div>
              <MonitorStatusPill health="info">{q.data.raw_highlights.items.length} lines</MonitorStatusPill>
            </div>
            {q.data.raw_highlights.items.length === 0 ? (
              <p className="mt-3 text-xs text-stone-500">No raw highlights for this run.</p>
            ) : (
              <>
                <ul className="mt-4 space-y-2 rounded-lg border border-cyan-100 bg-white/90 p-3">
                  {q.data.raw_highlights.items.slice(0, 6).map((h) => (
                    <li key={h.id} className="text-sm text-stone-800">
                      <span className="text-cyan-800">•</span> {h.text}
                    </li>
                  ))}
                </ul>
                <details className="mt-3 rounded-lg border border-stone-200 bg-stone-50/60">
                  <summary className="cursor-pointer px-3 py-2 text-xs font-semibold text-stone-800">
                    All highlights + sources
                  </summary>
                  <ul className="max-h-96 space-y-2 overflow-y-auto border-t border-stone-200 p-3">
                    {q.data.raw_highlights.items.map((h) => (
                      <li key={h.id} className="rounded-md border border-stone-100 bg-white px-3 py-2 text-xs">
                        <p className="text-stone-800">{h.text}</p>
                        <p className="mt-1 font-mono text-[10px] text-stone-500">sources: {h.sources.join(", ")}</p>
                      </li>
                    ))}
                  </ul>
                </details>
              </>
            )}
          </section>

          <section
            className="rounded-xl border border-indigo-200/90 bg-gradient-to-b from-white to-indigo-50/20 p-4 shadow-sm"
            data-testid="manager-insight-signals-p6"
          >
            {(() => {
              const m = monitorSignalsHealth(q.data);
              return (
                <>
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-indigo-900/80">
                        {PIPELINE.p6} · Coordination posture
                      </p>
                      <h2 className="mt-0.5 text-base font-semibold text-stone-900">Signals</h2>
                      <p className="mt-1 max-w-prose text-xs leading-relaxed text-stone-600">{m.why}</p>
                    </div>
                    <MonitorStatusPill health={m.health}>
                      {m.health === "ok"
                        ? "Stable"
                        : m.health === "warn"
                          ? "Strain"
                          : m.health === "error"
                            ? "Critical"
                            : "FYI"}
                    </MonitorStatusPill>
                  </div>
                  <details className="mt-3 rounded-lg border border-indigo-100 bg-white/70">
                    <summary className="cursor-pointer px-3 py-2 text-xs font-semibold text-indigo-950">
                      How signals are computed (§6 Steps 14–21)
                    </summary>
                    <div className="border-t border-indigo-100 p-3 text-xs text-stone-600">
                      <p>
                        Deterministic vector from work items through highlights. Uses the same inputs as P4/P5. Extension
                        slots cover scope ambiguity, churn, and contradictions. Each card is color-hinted: green favorable,
                        amber watch, rose risk.
                      </p>
                    </div>
                  </details>
                  <div className="mt-4 space-y-6" data-testid="manager-insight-signals-p6-grid">
                    <div>
                      <h3 className="text-xs font-semibold uppercase tracking-wide text-stone-500">Core signals</h3>
                      <ul
                        className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-3"
                        data-testid="manager-insight-signals-p6-core-grid"
                      >
                        {P6_SIGNAL_CORE_KEYS.map((key) => {
                          const val = formatManagerInsightSignalValue(q.data.signals, key);
                          const tone = signalCardTone(key, val);
                          return (
                            <li
                              key={key}
                              className={`rounded-lg border border-stone-100 border-l-4 px-3 py-2.5 text-xs shadow-sm ${signalCardClass(tone)}`}
                              data-testid={`manager-insight-signal-row-${key}`}
                            >
                              <p className="font-mono text-[11px] text-stone-600">{key}</p>
                              <p className="mt-1 text-lg font-bold tabular-nums text-stone-900">{val}</p>
                              <details className="mt-1.5">
                                <summary className="cursor-pointer text-[10px] font-medium text-stone-500">
                                  Why
                                </summary>
                                <p className="mt-1 text-[11px] leading-snug text-stone-600">
                                  {q.data.signals.explain[key] ?? "—"}
                                </p>
                              </details>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                    <div
                      className="rounded-xl border border-teal-200/80 bg-teal-50/50 p-4"
                      data-testid="manager-insight-signals-p6-coordination-extension"
                    >
                      <h3 className="text-xs font-semibold uppercase tracking-wide text-teal-950">
                        Coordination extension <span className="font-normal text-stone-600">(§6 Steps 19–21)</span>
                      </h3>
                      <ul
                        className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3"
                        data-testid="manager-insight-signals-p6-extension-grid"
                      >
                        {P6_SIGNAL_EXTENSION_KEYS.map((key) => {
                          const val = formatManagerInsightSignalValue(q.data.signals, key);
                          const tone = signalCardTone(key, val);
                          return (
                            <li
                              key={key}
                              className={`rounded-lg border border-teal-100/80 border-l-4 px-3 py-2.5 text-xs shadow-sm ${signalCardClass(tone)}`}
                              data-testid={`manager-insight-signal-row-${key}`}
                            >
                              <p className="font-mono text-[11px] text-teal-950">{key}</p>
                              <p className="mt-1 text-lg font-bold tabular-nums text-stone-900">{val}</p>
                              <details className="mt-1.5">
                                <summary className="cursor-pointer text-[10px] font-medium text-stone-500">
                                  Why
                                </summary>
                                <p className="mt-1 text-[11px] leading-snug text-stone-600">
                                  {q.data.signals.explain[key] ?? "—"}
                                </p>
                              </details>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  </div>
                </>
              );
            })()}
          </section>

          <section
            className="rounded-lg border border-amber-200 bg-amber-50/35 p-4 shadow-sm"
            data-testid="manager-insight-decisions-coordination"
          >
            <details className="group">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3 rounded-md px-1 py-1 text-sm font-semibold text-stone-900 marker:content-none [&::-webkit-details-marker]:hidden">
                <span>
                  Coordination decisions <span className="font-normal text-stone-600">(gap → actions)</span>{" "}
                  <span className="font-normal text-stone-500">§6 Steps 24–29 — not {PIPELINE.p7} narrative</span>
                </span>
                <span className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">
                  <span
                    className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-bold tabular-nums text-amber-950 ring-1 ring-amber-200/80"
                    title="Engine DecisionBundle row count (all gaps)"
                    data-testid="manager-insight-p7-engine-count-badge"
                  >
                    {engineDecisionCount(q.data)}
                  </span>
                  {(() => {
                    const prioBadge = p7PrioritizedSurfaceBadge(q.data);
                    if (prioBadge === null) {
                      return null;
                    }
                    return (
                      <span
                        className="rounded-full bg-teal-100 px-2.5 py-0.5 text-[11px] font-semibold tabular-nums text-teal-950 ring-1 ring-teal-200/90"
                        title="§6 Step 29 — prioritized rows after Step 27–28 cap (N = surfaced, denominator = full sort length)"
                        data-testid="manager-insight-p7-prioritized-surface-badge"
                      >
                        {prioBadge}
                      </span>
                    );
                  })()}
                  <span className="text-xs font-normal text-stone-500 group-open:hidden">Expand</span>
                  <span className="hidden text-xs font-normal text-stone-500 group-open:inline">Collapse</span>
                </span>
              </summary>
              <div className="mt-3 border-t border-amber-100 pt-3 text-sm text-stone-700">
                <p className="text-xs text-stone-600">
                  After {PIPELINE.p6} signals, <span className="font-mono">compute_decisions</span> maps each gap to a{" "}
                  <span className="font-mono">DecisionItem</span> with a <span className="font-medium">default_action</span>{" "}
                  payload. Engine <span className="font-mono">decisions</span> is the full bundle;{" "}
                  <span className="font-mono">decisions_prioritized</span> is the §6 Step 27–28 capped surface. Use the copy
                  buttons to paste JSON into issues or chat.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <CopyJsonButton
                    label="Copy decisions JSON"
                    value={q.data.decisions}
                    data-testid="manager-insight-copy-decisions-json"
                  />
                  <CopyJsonButton
                    label="Copy decisions_prioritized JSON"
                    value={q.data.decisions_prioritized}
                    data-testid="manager-insight-copy-decisions-prioritized-json"
                  />
                </div>
                <p className="mt-3 text-xs text-stone-600">
                  Row JSON expands <span className="font-mono">decision_debug</span> /{" "}
                  <span className="font-mono">decision_emission_debug</span> (e.g. §6 Step 26 <span className="font-mono">HOLD_START</span>{" "}
                  guards).
                </p>
                {engineDecisionCount(q.data) === 0 ? (
                  <p className="mt-3 rounded-md border border-dashed border-amber-200/80 bg-white/80 px-3 py-4 text-sm text-stone-600">
                    No engine decisions for this run — <span className="font-mono">compute_decisions</span> returned zero
                    items (usually no gaps in <span className="font-mono">gaps.gaps</span>). Check{" "}
                    <span className="font-mono">{PIPELINE.p5} Gaps</span> above.
                  </p>
                ) : q.data.decisions !== null ? (
                  <>
                    <CoordinationDecisionsTable items={q.data.decisions.items} />
                    {q.data.decisions_prioritized !== null && q.data.decisions_prioritized.length > 0 ? (
                      <PrioritizedDecisionsSurfaceTable items={q.data.decisions_prioritized} />
                    ) : null}
                  </>
                ) : null}
                <div className="mt-4 rounded-md border border-amber-100 bg-white/90 p-3" data-testid="manager-insight-persisted-decision-ids">
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-amber-950">
                    persisted_decision_ids <span className="font-normal text-amber-800">(§6 Step 32)</span>
                  </h3>
                  <p className="mt-1 text-xs text-stone-600">
                    PostgreSQL PKs when the request included <code className="text-[11px]">persist_decisions=1</code>.
                  </p>
                  {q.data.persisted_decision_ids.length === 0 ? (
                    <p className="mt-2 text-xs text-stone-500">[]</p>
                  ) : (
                    <ul className="mt-2 max-h-48 list-inside list-decimal space-y-1 overflow-auto rounded-md border border-amber-100 bg-white p-3 font-mono text-[11px] text-stone-800">
                      {q.data.persisted_decision_ids.map((id) => (
                        <li key={id} className="break-all">
                          {id}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </details>
          </section>

          <details
            className="rounded-lg border border-dashed border-stone-300 bg-stone-50/80 p-3 shadow-sm"
            data-testid="manager-insight-legacy-narrative-p7-p8"
          >
            <summary className="cursor-pointer text-sm font-semibold text-stone-800 marker:text-stone-600">
              Legacy narrative — {PIPELINE.p7} / {PIPELINE.p8}{" "}
              <span className="font-normal text-stone-500">(report-style; deterministic / skippable on this route)</span>
            </summary>
            <div className="mt-4 space-y-4 border-t border-stone-200 pt-4">
          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-stone-900">
              <span className="font-mono font-normal text-stone-500">{PIPELINE.p7}</span> Interpretations
            </h2>
            <p className="mt-1 text-xs text-stone-500">
              Count: {q.data.interpretations.items.length} · generated_via{" "}
              {q.data.interpretations.generated_via}
              {q.data.interpretations.generated_via === "fallback" &&
              q.data.interpretations.fallback_reason
                ? ` (${q.data.interpretations.fallback_reason})`
                : ""}
              {q.data.interpretations.model ? ` · model ${q.data.interpretations.model}` : ""}
              {q.data.interpretations.latency_ms !== null
                ? ` · latency ${q.data.interpretations.latency_ms}ms`
                : ""}
            </p>
            {q.data.interpretations.llm_parsed_interpretation_rows !== null ? (
              <p className="mt-1 text-xs text-stone-500">
                LLM JSON rows (dict objects) parsed: {q.data.interpretations.llm_parsed_interpretation_rows} ·
                rejected rows: {q.data.interpretations.rejected_interpretations.length}
                {q.data.interpretations.llm_response_truncated ? " · llm_response_text truncated" : ""}
              </p>
            ) : null}
            {q.data.interpretations.llm_error ? (
              <p className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
                LLM issue: {q.data.interpretations.llm_error}
              </p>
            ) : null}
            {q.data.interpretations.llm_response_text ||
            q.data.interpretations.rejected_interpretations.length > 0 ? (
              <details className="mt-3 rounded-md border border-stone-200 bg-stone-50 p-3">
                <summary className="cursor-pointer text-xs font-semibold text-stone-900">
                  Rejected / raw LLM output (debug)
                </summary>
                {q.data.interpretations.rejected_interpretations.length > 0 ? (
                  <ul className="mt-3 max-h-72 space-y-2 overflow-y-auto">
                    {q.data.interpretations.rejected_interpretations.map((r) => (
                      <li key={r.index} className="rounded-md border border-stone-200 bg-white px-3 py-2 text-xs">
                        <p className="font-mono text-[10px] text-stone-500">row_index={r.index}</p>
                        <p className="mt-1 text-stone-800">{r.reason}</p>
                        <pre className="mt-2 max-h-40 overflow-auto rounded bg-stone-900/90 p-2 text-[11px] text-stone-100">
                          {JSON.stringify(r.raw, null, 2)}
                        </pre>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-xs text-stone-500">No per-row rejections recorded.</p>
                )}
                {q.data.interpretations.llm_response_text ? (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-stone-900">Raw assistant text</p>
                    <pre className="mt-2 max-h-72 overflow-auto rounded bg-stone-900/90 p-2 text-[11px] text-stone-100">
                      {q.data.interpretations.llm_response_text}
                    </pre>
                  </div>
                ) : null}
              </details>
            ) : null}
            {q.data.interpretations.items.length === 0 ? (
              <p className="mt-3 text-xs text-stone-500">No interpretations produced.</p>
            ) : (
              <ul className="mt-3 max-h-96 space-y-2 overflow-y-auto">
                {q.data.interpretations.items.map((it) => (
                  <li key={it.id} className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2 text-xs">
                    <p className="font-medium text-stone-900">
                      {it.type.replace(/_/g, " ")} · {it.confidence}
                    </p>
                    <p className="mt-1 text-stone-700">{it.description}</p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      based_on_gaps: {it.based_on_gaps.join(", ") || "—"} · based_on_blockers:{" "}
                      {it.based_on_blockers.join(", ") || "—"} · based_on_highlights:{" "}
                      {it.based_on_highlights.join(", ") || "—"}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      based_on_signals: {it.based_on_signals.join(", ") || "—"}
                    </p>
                    <ul className="mt-1 list-inside list-disc text-stone-600">
                      {it.evidence.map((ev) => (
                        <li key={ev} className="text-[11px]">
                          {ev}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
            <h2 className="text-sm font-semibold text-stone-900">
              <span className="font-mono font-normal text-stone-500">{PIPELINE.p8}</span> Insights
            </h2>
            <p className="mt-1 text-xs text-stone-500">
              Count: {q.data.insights.items.length} · generated_via {q.data.insights.generated_via}
              {q.data.insights.generated_via === "fallback" && q.data.insights.fallback_reason
                ? ` (${q.data.insights.fallback_reason})`
                : ""}
              {q.data.insights.model ? ` · model ${q.data.insights.model}` : ""}
              {q.data.insights.latency_ms !== null ? ` · latency ${q.data.insights.latency_ms}ms` : ""}
            </p>
            {q.data.insights.llm_parsed_insight_rows !== null ? (
              <p className="mt-1 text-xs text-stone-500">
                LLM JSON rows (dict objects) parsed: {q.data.insights.llm_parsed_insight_rows} · rejected
                rows: {q.data.insights.rejected_insights.length}
                {q.data.insights.llm_response_truncated ? " · llm_response_text truncated" : ""}
              </p>
            ) : null}
            {q.data.insights.llm_error ? (
              <p className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
                LLM issue: {q.data.insights.llm_error}
              </p>
            ) : null}
            {q.data.insights.llm_response_text || q.data.insights.rejected_insights.length > 0 ? (
              <details className="mt-3 rounded-md border border-stone-200 bg-stone-50 p-3">
                <summary className="cursor-pointer text-xs font-semibold text-stone-900">
                  Rejected / raw LLM output (debug)
                </summary>
                {q.data.insights.rejected_insights.length > 0 ? (
                  <ul className="mt-3 max-h-72 space-y-2 overflow-y-auto">
                    {q.data.insights.rejected_insights.map((r) => (
                      <li key={r.index} className="rounded-md border border-stone-200 bg-white px-3 py-2 text-xs">
                        <p className="font-mono text-[10px] text-stone-500">row_index={r.index}</p>
                        <p className="mt-1 text-stone-800">{r.reason}</p>
                        <pre className="mt-2 max-h-40 overflow-auto rounded bg-stone-900/90 p-2 text-[11px] text-stone-100">
                          {JSON.stringify(r.raw, null, 2)}
                        </pre>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-xs text-stone-500">No per-row rejections recorded.</p>
                )}
                {q.data.insights.llm_response_text ? (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-stone-900">Raw assistant text</p>
                    <pre className="mt-2 max-h-72 overflow-auto rounded bg-stone-900/90 p-2 text-[11px] text-stone-100">
                      {q.data.insights.llm_response_text}
                    </pre>
                  </div>
                ) : null}
              </details>
            ) : null}
            {q.data.insights.items.length === 0 ? (
              <p className="mt-3 text-xs text-stone-500">No insights produced.</p>
            ) : (
              <ul className="mt-3 max-h-96 space-y-2 overflow-y-auto">
                {q.data.insights.items.map((it) => (
                  <li key={it.id} className="rounded-md border border-stone-100 bg-stone-50 px-3 py-2 text-xs">
                    <p className="font-medium text-stone-900">
                      priority {it.priority} · confidence {it.confidence}
                    </p>
                    <p className="mt-1 text-stone-800">
                      <span className="font-semibold">Observation:</span> {it.observation}
                    </p>
                    <p className="mt-1 text-stone-700">
                      <span className="font-semibold">Interpretation:</span> {it.interpretation}
                    </p>
                    <p className="mt-1 text-stone-700">
                      <span className="font-semibold">Implication:</span> {it.implication}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      based_on_gaps: {it.based_on_gaps.join(", ") || "—"} · based_on_blockers:{" "}
                      {it.based_on_blockers.join(", ") || "—"} · based_on_highlights:{" "}
                      {it.based_on_highlights.join(", ") || "—"}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      evidence_ids: {it.evidence_ids.join(", ")}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      primary_work_item_ids: {it.primary_work_item_ids.join(", ")}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      supporting_work_item_ids: {it.supporting_work_item_ids.join(", ") || "—"}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      primary_entities:{" "}
                      {it.primary_entities.map((e) => `${e.name} (${e.kind})`).join(", ")}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      based_on_interpretations: {it.based_on_interpretations.join(", ") || "—"}
                    </p>
                    <p className="mt-1 font-mono text-[10px] text-stone-500">
                      based_on_signals: {it.based_on_signals.join(", ")}
                    </p>
                    <ul className="mt-1 list-inside list-disc text-stone-600">
                      {it.evidence.map((ev) => (
                        <li key={ev} className="text-[11px]">
                          {ev}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            )}
          </section>
            </div>
          </details>

          <details
            className="rounded-lg border border-violet-200 bg-violet-50/40 p-4 shadow-sm"
            data-testid="manager-insight-contract-reference"
          >
            <summary className="cursor-pointer text-sm font-semibold text-violet-950 marker:text-violet-700">
              Contract reference samples <span className="font-normal text-violet-800">(§6 Steps 1–2, 7–9)</span>
            </summary>
            <p className="mt-2 text-xs text-violet-950/90">
              Static JSON shapes for QA — not computed from this run&apos;s gaps. Live rows appear in coordination decisions
              and pipeline sections above.
            </p>
            <div className="mt-4 space-y-4">
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-violet-900">
                  decision_item_example (§6 Step 1)
                </h3>
                <pre className="mt-2 max-h-56 overflow-auto rounded-md border border-violet-100 bg-white p-3 text-xs text-stone-800">
                  {JSON.stringify(q.data.coordination_contracts.decision_item_example, null, 2)}
                </pre>
              </div>
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-violet-900">
                  decision_bundle_example (§6 Step 2)
                </h3>
                <p className="mt-1 text-xs text-stone-500">
                  Includes optional <span className="font-mono">decision_debug</span> on the first row only.
                </p>
                <pre className="mt-2 max-h-72 overflow-auto rounded-md border border-violet-100 bg-white p-3 text-xs text-stone-800">
                  {JSON.stringify(q.data.coordination_contracts.decision_bundle_example, null, 2)}
                </pre>
              </div>
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-violet-900">
                  outcome_item_example (§6 Step 2)
                </h3>
                <pre className="mt-2 max-h-48 overflow-auto rounded-md border border-violet-100 bg-white p-3 text-xs text-stone-800">
                  {JSON.stringify(q.data.coordination_contracts.outcome_item_example, null, 2)}
                </pre>
              </div>
              <div data-testid="manager-insight-perception-row-example">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-violet-900">
                  perception_row_example (§6 Step 7)
                </h3>
                <p className="mt-1 text-xs text-stone-500">
                  Sample contradiction row with <span className="font-mono">waits_on</span>,{" "}
                  <span className="font-mono">commitment_strength</span>, and paired quotes — not from live LLM output yet.
                </p>
                <pre className="mt-2 max-h-72 overflow-auto rounded-md border border-violet-100 bg-white p-3 text-xs text-stone-800">
                  {JSON.stringify(q.data.coordination_contracts.perception_row_example, null, 2)}
                </pre>
              </div>
              <div data-testid="manager-insight-perception-validation-demo">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-violet-900">
                  perception_validation_demo (§6 Step 8)
                </h3>
                <p className="mt-1 text-xs text-stone-500">
                  Deterministic output of <span className="font-mono">validate_perception_rows</span> — compare{" "}
                  <span className="font-mono">accepted</span> vs <span className="font-mono">rejected</span> reasons.
                </p>
                <pre className="mt-2 max-h-96 overflow-auto rounded-md border border-violet-100 bg-white p-3 text-xs text-stone-800">
                  {JSON.stringify(q.data.coordination_contracts.perception_validation_demo, null, 2)}
                </pre>
              </div>
              <div data-testid="manager-insight-perception-execution-state-demo">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-violet-900">
                  perception_execution_state_demo (§6 Step 9)
                </h3>
                <p className="mt-1 text-xs text-stone-500">
                  Stub Chat Completions response parsed into <span className="font-mono">rows</span>; optional{" "}
                  <span className="font-mono">skipped_reason</span> when demo cannot run.
                </p>
                <pre className="mt-2 max-h-96 overflow-auto rounded-md border border-violet-100 bg-white p-3 text-xs text-stone-800">
                  {JSON.stringify(q.data.coordination_contracts.perception_execution_state_demo, null, 2)}
                </pre>
              </div>
            </div>
          </details>
                  </div>
                ) : null}
              </div>
            </div>
          </details>
        </div>
      ) : null}
    </div>
  );
}
