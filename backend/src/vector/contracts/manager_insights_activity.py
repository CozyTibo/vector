"""Contracts for Manager insights debug pipeline artifacts (Steps 1–8)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

ManagerInsightConnector = Literal["slack", "github", "linear", "notion", "calls"]

DataReliabilityTier = Literal["high", "medium", "low"]
WorkItemType = Literal["issue", "pull_request", "document", "call", "message_thread"]
EvidenceKind = Literal["action_item", "blocker", "decision"]
LinkType = Literal["semantic_match", "shared_reference"]
LinkConfidence = Literal["high", "medium", "low"]
GapType = Literal[
    "expected_not_executed",
    "discussed_not_linked_to_work",
    "blocker_not_tracked",
    "doc_not_connected_to_execution",
]

CoordinationDecisionType = Literal[
    "LINK_OR_CLOSE_COMMITMENT",
    "THREAD_TO_TRACKING_LINK",
    "BLOCKER_ESCALATION",
    "DOC_EXECUTION_BRIDGE",
    "HOLD_START",
    "CLARIFY_SPEC",
    "RECENTER",
    "PAUSE_INVESTMENT",
]

DecisionLifecycleStatus = Literal["proposed", "accepted", "dismissed", "completed", "failed"]

OutcomeType = Literal[
    "applied_success",
    "applied_partial",
    "apply_failed",
    "dismissed",
    "ignored",
    "superseded",
]
SignalDeliveryStrength = Literal["low", "moderate", "high"]
SignalExpectationCoverage = Literal["high", "partial", "low"]
SignalFollowThrough = Literal["strong", "partial", "weak"]
SignalBlockerVisibility = Literal["visible", "partial", "not_visible"]
SignalExecutionMomentum = Literal["accelerating", "steady", "slowing"]
SignalDocumentationLinkage = Literal["linked", "partially_linked", "not_linked"]
SignalFocus = Literal["focused", "moderate", "fragmented"]
SignalCollaborationIntensity = Literal["low", "moderate", "high"]
SignalSupportPattern = Literal["gives_help", "asks_for_help", "balanced"]
SignalFeedbackReception = Literal["proactive", "neutral", "defensive"]
SignalCoordinationRole = Literal["driving", "contributing", "peripheral"]
SignalInteractionFriction = Literal["present", "unclear", "absent"]
InterpretationType = Literal[
    "ownership",
    "follow_through",
    "execution_friction",
    "prioritization",
    "collaboration_pattern",
    "autonomy",
    "support_dependency",
    "coordination_quality",
    "leverage",
]
InterpretationConfidence = Literal["high", "medium", "low"]
InsightConfidence = Literal["high", "medium", "low"]
InsightPriority = Literal["critical", "high", "medium", "low"]
InsightPrimaryEntityKind = Literal["project", "feature", "system"]

PerceptionRowKind = Literal["action_item", "blocker", "decision", "risk", "ambiguity", "ownership_hint"]
ExecutionStatePerception = Literal["not_started", "in_progress", "blocked", "waiting", "done"]
PerceptionCommitmentStrength = Literal["weak", "medium", "strong"]
AmbiguityClass = Literal["unclear_scope", "discussion_loop", "contradiction"]


class ConnectorCoverageStats(BaseModel):
    """Per-connector source coverage counters used by Step 0.5 thresholds."""

    model_config = ConfigDict(from_attributes=False)

    configured_sources: int = Field(default=0, ge=0)
    successful_sources: int = Field(default=0, ge=0)
    critical_configured_sources: int = Field(default=0, ge=0)
    critical_successful_sources: int = Field(default=0, ge=0)


class ConnectorCompletenessStats(BaseModel):
    """Per-connector completeness counters (caps/truncation/empty expectations)."""

    model_config = ConfigDict(from_attributes=False)

    successful_sources: int = Field(default=0, ge=0)
    capped_sources: int = Field(default=0, ge=0)
    expected_non_empty_sources: int = Field(default=0, ge=0)
    observed_non_empty_sources: int = Field(default=0, ge=0)


class ConnectorFetchResult(BaseModel):
    """One connector's raw fetch outcome (Step 1)."""

    model_config = ConfigDict(from_attributes=False)

    connector: ManagerInsightConnector
    status: Literal["ok", "error", "not_configured", "not_built", "global_disabled"] = Field(
        description="ok=HTTP/API success; not_configured=no tenant link; "
        "not_built=Notion/Gemini not wired in V0 yet; global_disabled=GitHub app env missing",
    )
    fetched_at: datetime | None = None
    window_start: datetime
    window_end: datetime
    caps_applied: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    coverage: ConnectorCoverageStats = Field(default_factory=ConnectorCoverageStats)
    completeness: ConnectorCompletenessStats = Field(default_factory=ConnectorCompletenessStats)
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Redacted connector-native JSON (no tokens or secrets).",
    )


class FetchActivityBundle(BaseModel):
    """Full Step 1 bundle for one tenant run."""

    model_config = ConfigDict(from_attributes=False)

    run_id: uuid.UUID
    tenant_id: uuid.UUID
    window_days: int = Field(ge=1, le=366)
    connectors: dict[str, ConnectorFetchResult] = Field(
        description="Keys: slack, github, linear, notion, calls",
    )


class ConnectorReliabilityDetail(BaseModel):
    """Per-connector tier + auditable reasons (Step 0.5)."""

    model_config = ConfigDict(from_attributes=False)

    tier: DataReliabilityTier
    reasons: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)


class DataReliabilityReport(BaseModel):
    """Step 0.5 output."""

    model_config = ConfigDict(from_attributes=False)

    slack: ConnectorReliabilityDetail
    github: ConnectorReliabilityDetail
    linear: ConnectorReliabilityDetail
    notion: ConnectorReliabilityDetail
    calls: ConnectorReliabilityDetail
    overall_confidence: DataReliabilityTier


class WorkItem(BaseModel):
    """Step 2 normalized work item consumed by downstream pipeline steps."""

    model_config = ConfigDict(from_attributes=False)

    id: str
    source: ManagerInsightConnector
    type: WorkItemType
    title: str
    summary: str | None = None
    status: str | None = None
    url: str | None = None
    project: str | None = None
    owner: str | None = None
    participants: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    closed_at: datetime | None = None
    source_ref: dict[str, str] = Field(default_factory=dict)


class WorkItemBundle(BaseModel):
    """Step 2 output for one run."""

    model_config = ConfigDict(from_attributes=False)

    run_id: uuid.UUID
    tenant_id: uuid.UUID
    window_days: int = Field(ge=1, le=366)
    items: list[WorkItem] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    """Step 3 extracted evidence item with strict citation fields."""

    model_config = ConfigDict(from_attributes=False)

    id: str
    kind: EvidenceKind
    statement: str
    evidence: str
    source_work_item_id: str
    source_connector: ManagerInsightConnector
    source_type: WorkItemType
    source_ref: dict[str, str] = Field(default_factory=dict)
    linked_work_items: list[str] = Field(default_factory=list)


class EvidenceBundle(BaseModel):
    """Step 3 output from evidence extraction."""

    model_config = ConfigDict(from_attributes=False)

    run_id: uuid.UUID
    tenant_id: uuid.UUID
    window_days: int = Field(ge=1, le=366)
    action_items: list[EvidenceItem] = Field(default_factory=list)
    blockers: list[EvidenceItem] = Field(default_factory=list)
    decisions: list[EvidenceItem] = Field(default_factory=list)
    discarded_without_evidence: int = Field(default=0, ge=0)


class WorkItemLink(BaseModel):
    """Step 4: hypothesis edge between two work items (best-effort, not ground truth)."""

    model_config = ConfigDict(from_attributes=False)

    id: str
    from_work_item_id: str
    to_work_item_id: str
    link_type: LinkType
    confidence: LinkConfidence
    similarity: float = Field(ge=0.0, le=1.0, description="Deterministic 0-1 token overlap score")
    method: str = Field(default="token_jaccard", description="Scoring method for audits")
    evidence: str = Field(
        description="Why we think these relate (overlaps + short snippets, citeable in QA)",
    )


class LinkBundle(BaseModel):
    """Step 4 output: semantic / reference links for one run."""

    model_config = ConfigDict(from_attributes=False)

    run_id: uuid.UUID
    tenant_id: uuid.UUID
    window_days: int = Field(ge=1, le=366)
    links: list[WorkItemLink] = Field(default_factory=list)
    work_items_capped: int = Field(
        default=0,
        ge=0,
        description="If >0, work item list was truncated to this count before O(n^2) linking",
    )
    perception_rows_used_for_linking: int = Field(
        default=0,
        ge=0,
        description="§6 Step 12 — count of validated PerceptionRow merged into link scoring text.",
    )


ExecutionGraphNodeKind = Literal["issue", "pr", "doc", "thread"]
ExecutionGraphEdgeRelation = Literal["depends_on", "blocks", "references"]


class ExecutionNode(BaseModel):
    """§6 Step 15 / coordination Step 4.5 — one node per tracked work item in the ephemeral graph."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    id: str = Field(min_length=1, description="Same as WorkItem.id.")
    kind: ExecutionGraphNodeKind = Field(
        description="Normalized from WorkItem.type (issue, pr, doc, thread).",
    )
    execution_state: ExecutionStatePerception | None = Field(
        default=None,
        description="From validated perception when present; else derived from WorkItem fields only.",
    )
    owner_hint: str | None = Field(
        default=None,
        description="Optional span or role from validated PerceptionRow.ownership_inferred.",
    )


class ExecutionEdge(BaseModel):
    """Directed edge in the ephemeral execution graph (no persistence)."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    id: str = Field(min_length=1, description="Deterministic id for stable JSON / dedupe.")
    from_id: str = Field(min_length=1)
    to_id: str = Field(min_length=1)
    relation: ExecutionGraphEdgeRelation


class ExecutionGraph(BaseModel):
    """§6 Step 15 — in-memory execution graph for one run (not stored in DB)."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    run_id: uuid.UUID
    tenant_id: uuid.UUID
    window_days: int = Field(ge=1, le=366)
    nodes: list[ExecutionNode] = Field(default_factory=list)
    edges: list[ExecutionEdge] = Field(default_factory=list)
    unresolved_dependency_refs: list[str] = Field(
        default_factory=list,
        description="Dependency mentions that did not resolve to a WorkItem id; never emitted as edges.",
    )


class GapItem(BaseModel):
    """Step 5 deterministic gap entry with evidence pointers to Step 2–4 artifacts."""

    model_config = ConfigDict(from_attributes=False)

    id: str
    type: GapType
    description: str
    evidence_pointers: dict[str, list[str]] = Field(default_factory=dict)


class GapBundle(BaseModel):
    """Step 5 output: computed gaps for one run."""

    model_config = ConfigDict(from_attributes=False)

    run_id: uuid.UUID
    tenant_id: uuid.UUID
    window_days: int = Field(ge=1, le=366)
    gaps: list[GapItem] = Field(default_factory=list)
    gaps_debug: str | None = Field(
        default=None,
        description="§6 Step 18 — one-line QA when gaps_use_graph merges execution-graph adjacency.",
    )


class DecisionDefaultAction(BaseModel):
    """Planned connector action for coordination apply (Step 8); not executed at contract time."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    kind: str = Field(min_length=1, description="Action discriminator for apply layer.")
    connector: ManagerInsightConnector | None = None
    payload_template: dict[str, Any] = Field(default_factory=dict)


class DecisionItem(BaseModel):
    """One coordination decision (rule engine Step 7); deterministic templates only, no LLM."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    id: str = Field(min_length=1, description="Stable id; becomes DB primary key after persist.")
    gap_id: str = Field(min_length=1, description="Source gap id; required in V1.")
    gap_type: GapType
    decision_type: CoordinationDecisionType
    title: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    default_action: DecisionDefaultAction
    required_inputs: dict[str, Any] = Field(
        default_factory=dict,
        description="Human/API fields still needed before apply (shape varies by decision_type).",
    )
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="EvidenceItem ids and/or work item ids supporting the decision.",
    )
    signal_refs: list[str] = Field(
        default_factory=list,
        description="SignalsV0 / extension keys that influenced ordering only.",
    )
    created_at: datetime
    run_id: uuid.UUID
    status: DecisionLifecycleStatus | None = Field(
        default=None,
        description="Lifecycle after persist (10.5); omit for engine-only / in-memory rows.",
    )


class DecisionRuleTraceDebug(BaseModel):
    """Admin-only rule trace for one decision row (fetch-debug; not required for Slack payloads)."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    gap_id: str = Field(min_length=1)
    matched_rule: str = Field(
        min_length=1,
        description="Rule id or label from deterministic tables.",
    )
    conditions_met: dict[str, bool] = Field(default_factory=dict)


class DecisionEmissionTraceDebug(BaseModel):
    """§6 Step 26 — HOLD_START guard evaluation (admin QA; fetch-debug only)."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    evaluated: bool = Field(
        default=False,
        description="True when scope-high extension path was evaluated for this gap.",
    )
    inputs_complete: bool = Field(
        default=False,
        description="work_items, links, evidence, coordination_input were all provided for cluster math.",
    )
    ambiguity_signal_high: bool = False
    cluster_hops_used: int = Field(default=0, ge=0, le=8)
    seed_work_item_ids: list[str] = Field(default_factory=list)
    cluster_work_item_ids: list[str] = Field(default_factory=list)
    open_execution_work_item_ids: list[str] = Field(default_factory=list)
    open_execution_count: int = Field(default=0, ge=0)
    affected_wi_threshold: int = Field(
        default=2,
        ge=0,
        description="HOLD_START only if open_execution_count > this value (strict inequality).",
    )
    decision_evidence_ids_in_cluster: list[str] = Field(default_factory=list)
    guard_ambiguity_ok: bool = False
    guard_no_decision_evidence_in_cluster_ok: bool = False
    guard_open_execution_count_ok: bool = False
    hold_start_emitted: bool = False
    reason: str = Field(
        default="",
        description="Deterministic one-line explanation for admin QA.",
    )


class DecisionBundleItem(BaseModel):
    """One decision plus optional per-row debug."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    decision: DecisionItem
    decision_debug: DecisionRuleTraceDebug | None = None
    decision_emission_debug: DecisionEmissionTraceDebug | None = Field(
        default=None,
        description="§6 Step 26 — HOLD_START three-guard trace when scope extension is evaluated.",
    )


class DecisionBundle(BaseModel):
    """Rule engine output for one run (coordination Step 7); no LLM."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    run_id: uuid.UUID
    tenant_id: uuid.UUID
    window_days: int = Field(ge=1, le=366)
    items: list[DecisionBundleItem] = Field(default_factory=list)


class OutcomeItem(BaseModel):
    """Learn-loop outcome row (coordination 10.6); deterministic evaluation only, no ML."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    id: uuid.UUID
    decision_id: str = Field(min_length=1)
    tenant_id: uuid.UUID
    observed_at: datetime
    outcome_type: OutcomeType
    user_attribution: str | None = None
    receipt: dict[str, Any] | None = Field(
        default=None,
        description="Connector ids, HTTP status, or short error from apply layer.",
    )
    false_positive: bool | None = None
    ground_truth: dict[str, Any] = Field(
        default_factory=dict,
        description="Deterministic flags from replay / subsequent runs (booleans or id checks).",
    )


class PerceptionStateTransition(BaseModel):
    """Quote-backed execution state movement (coordination plan §2.1)."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    from_state: ExecutionStatePerception | None = None
    to_state: ExecutionStatePerception
    quote: str = Field(min_length=1)


class PerceptionOwnershipInferred(BaseModel):
    """Owner inference allowed only when tied to a verbatim span in the same work item (§2.1)."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    text_span: str = Field(min_length=1)
    role_guess: str | None = None


class PerceptionRow(BaseModel):
    """Execution-state perception row from the LLM path; kept separate from regex `EvidenceItem` (architecture lock)."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    id: str = Field(min_length=1)
    work_item_id: str = Field(min_length=1)
    kind: PerceptionRowKind
    statement: str = Field(
        min_length=1,
        description="Claim summarizing the perceived execution fact; Step 8 checks grounding in parent text.",
    )
    quote: str = Field(
        min_length=1,
        description="Primary contiguous quote from the parent work item (title/body/thread slice).",
    )
    execution_state: ExecutionStatePerception | None = None
    state_transition: PerceptionStateTransition | None = None
    waits_on: list[str] = Field(
        default_factory=list,
        description="Dependency mentions grounded in source text (e.g. “waiting on @legal”).",
    )
    blocked_by: list[str] = Field(default_factory=list)
    commitment_strength: PerceptionCommitmentStrength | None = None
    ambiguity_class: AmbiguityClass | None = None
    ambiguity_quote: str | None = Field(
        default=None,
        description="Extra verbatim slice for ambiguity rows; required when ambiguity_class is contradiction.",
    )
    contradiction_pair_id: str | None = Field(
        default=None,
        description="Machine-checkable pair id when two conflicting quotes are cited (contradiction only).",
    )
    ownership_inferred: PerceptionOwnershipInferred | None = None

    @model_validator(mode="after")
    def _contradiction_invariants(self) -> Self:
        if self.ambiguity_class == "contradiction":
            if not (self.ambiguity_quote and self.ambiguity_quote.strip()):
                raise ValueError("ambiguity_quote is required when ambiguity_class is contradiction")
            if not (self.contradiction_pair_id and self.contradiction_pair_id.strip()):
                raise ValueError("contradiction_pair_id is required when ambiguity_class is contradiction")
        return self


class CoordinationLinkInputBundle(BaseModel):
    """§6 Step 12 — validated perception rows + Step-3 evidence; sole extra input to ``link_work_items``."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    evidence: EvidenceBundle
    perception_rows: list[PerceptionRow] = Field(
        default_factory=list,
        description="Validated PerceptionRow list for this run; empty when perception_llm is off.",
    )


class CoordinationContractsDebug(BaseModel):
    """Validated coordination DTO samples for admin QA until live pipeline fields land."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    decision_item_example: DecisionItem = Field(
        description="Round-trips DecisionItem; same run_id as fetch; static sample — live rows match this schema from compute_decisions.",
    )
    decision_bundle_example: DecisionBundle = Field(
        description="Sample DecisionBundle with optional decision_debug on one row.",
    )
    outcome_item_example: OutcomeItem = Field(
        description="Stub OutcomeItem shape for apply / dismiss flows (§6 Step 40+).",
    )
    perception_row_example: PerceptionRow = Field(
        description="Sample PerceptionRow for QA; live rows come from perceive_execution_state (§6 Step 9+).",
    )
    perception_validation_demo: PerceptionValidationDemoDebug = Field(
        description="§6 Step 8 — deterministic validate_perception_rows outcome for admin QA.",
    )
    perception_execution_state_demo: PerceptionExecutionStateLlmDebug = Field(
        description="§6 Step 9 — stub-LLM parse demo (no network); live path is perceive_execution_state.",
    )


class KeyAchievementItem(BaseModel):
    """Step 5.5: one closed/merged, attributable win (deterministic, no LLM)."""

    model_config = ConfigDict(from_attributes=False)

    id: str
    title: str
    linked_items: list[str] = Field(default_factory=list, min_length=1)
    evidence: list[str] = Field(
        default_factory=list,
        min_length=1,
        description="Citable strings: work_item id, optional link/reinforcement refs",
    )
    sort_at: datetime | None = None


class KeyAchievementsBundleDebug(BaseModel):
    """Step 5.5 bundle aligned with admin debug and UserReportContext.key_achievements."""

    model_config = ConfigDict(from_attributes=False)

    run_id: uuid.UUID
    tenant_id: uuid.UUID
    window_days: int = Field(ge=1, le=366)
    items: list[KeyAchievementItem] = Field(default_factory=list)


class RawHighlightItem(BaseModel):
    """Step 5.6: factual line + sources (work_item ids, gap ids, etc.)."""

    model_config = ConfigDict(from_attributes=False)

    id: str
    text: str
    sources: list[str] = Field(default_factory=list, min_length=1)


class RawHighlightsBundleDebug(BaseModel):
    """Step 5.6 bundle for admin debug and UserReportContext.raw_highlights."""

    model_config = ConfigDict(from_attributes=False)

    run_id: uuid.UUID
    tenant_id: uuid.UUID
    window_days: int = Field(ge=1, le=366)
    items: list[RawHighlightItem] = Field(default_factory=list)


class SignalsV0Debug(BaseModel):
    """Step 6 deterministic signal vector plus explainable reasons.

    §6 Step 19 adds coordination extension slots (defaults when omitted); §6 Step 20 implements predicates + explain text in ``compute_signals``.
    """

    model_config = ConfigDict(from_attributes=False)

    delivery_strength: SignalDeliveryStrength
    urgent_pressure: SignalDeliveryStrength
    expectation_coverage: SignalExpectationCoverage
    follow_through: SignalFollowThrough
    blocker_visibility: SignalBlockerVisibility
    repeated_discussion_present: bool
    execution_momentum: SignalExecutionMomentum
    documentation_linkage: SignalDocumentationLinkage
    focus: SignalFocus
    collaboration_intensity: SignalCollaborationIntensity
    support_pattern: SignalSupportPattern
    feedback_reception: SignalFeedbackReception
    coordination_role: SignalCoordinationRole
    interaction_friction: SignalInteractionFriction
    scope_ambiguity: SignalDeliveryStrength = Field(
        default="low",
        description="§6 Steps 19–20 — scope ambiguity signal (low/moderate/high); Step 20 computes in compute_signals.",
    )
    discussion_churn: SignalDeliveryStrength = Field(
        default="low",
        description="§6 Steps 19–20 — discussion churn signal; Step 20 computes in compute_signals.",
    )
    contradiction_density: SignalDeliveryStrength = Field(
        default="low",
        description="§6 Steps 19–20 — contradiction density signal; Step 20 computes in compute_signals.",
    )
    explain: dict[str, str] = Field(default_factory=dict)


class InterpretationItemDebug(BaseModel):
    """Step 7 interpretation item (LLM output validated against schema + citations)."""

    model_config = ConfigDict(from_attributes=False)

    id: str
    type: InterpretationType
    description: str
    based_on_signals: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list, min_length=1)
    confidence: InterpretationConfidence
    based_on_gaps: list[str] = Field(default_factory=list)
    based_on_blockers: list[str] = Field(default_factory=list)
    based_on_highlights: list[str] = Field(default_factory=list)


class RejectedInterpretationDebug(BaseModel):
    """LLM row that did not pass schema/citation checks (admin QA only)."""

    model_config = ConfigDict(from_attributes=False)

    index: int = Field(ge=0, description="0-based index in the model's interpretations[] list")
    reason: str
    raw: dict[str, Any] = Field(default_factory=dict)


class RejectedPerceptionRowDebug(BaseModel):
    """Perception LLM row rejected by Step 3 validation (admin QA only)."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    index: int = Field(ge=0, description="0-based index in the model perception[] list")
    reason: str
    raw: dict[str, Any] = Field(default_factory=dict)


class PerceptionValidationDemoDebug(BaseModel):
    """§6 Step 8 — deterministic validate_perception_rows demo bundled with fetch-debug QA."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    demo_work_item_id: str = Field(min_length=1)
    input_row_count: int = Field(ge=0)
    accepted: list[PerceptionRow] = Field(default_factory=list)
    rejected: list[RejectedPerceptionRowDebug] = Field(default_factory=list)


class PerceptionExecutionStateLlmDebug(BaseModel):
    """§6 Step 9 — raw Chat Completions parse for execution-state perception (before Step 8 validation)."""

    model_config = ConfigDict(from_attributes=False, extra="forbid")

    rows: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Objects from assistant JSON `perception_rows` (not yet passed through validate_perception_rows).",
    )
    raw_assistant_text: str | None = None
    raw_assistant_truncated: bool = False
    parse_error: str | None = Field(default=None, description="JSON/object shape failure.")
    response_level_error: str | None = Field(
        default=None,
        description="Assistant empty, missing perception_rows key, or non-list.",
    )
    model: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    skipped_reason: str | None = Field(
        default=None,
        description="missing_api_key | no_work_items when LLM was not invoked.",
    )


class InterpretationBundleDebug(BaseModel):
    """Step 7 bundle for admin debug; includes generation metadata for QA."""

    model_config = ConfigDict(from_attributes=False)

    run_id: uuid.UUID
    tenant_id: uuid.UUID
    window_days: int = Field(ge=1, le=366)
    items: list[InterpretationItemDebug] = Field(default_factory=list)
    generated_via: Literal["llm", "fallback"]
    fallback_reason: str | None = None
    model: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    llm_response_text: str | None = Field(
        default=None,
        description="Raw assistant text (may be truncated for very large responses).",
    )
    llm_response_truncated: bool = False
    llm_parsed_interpretation_rows: int | None = Field(
        default=None,
        ge=0,
        description="Count of object rows parsed from the model JSON (before validation).",
    )
    rejected_interpretations: list[RejectedInterpretationDebug] = Field(default_factory=list)
    llm_error: str | None = Field(
        default=None,
        description="If OpenAI failed, a short admin QA error string (not a stack trace).",
    )


class InsightPrimaryEntityItem(BaseModel):
    """Named execution surface (project / feature / system) for admin QA."""

    model_config = ConfigDict(from_attributes=False)

    name: str
    kind: InsightPrimaryEntityKind


class InsightItemDebug(BaseModel):
    """Step 8 insight item (LLM output validated against schema + grounding checks)."""

    model_config = ConfigDict(from_attributes=False)

    id: str
    observation: str
    interpretation: str
    implication: str
    evidence: list[str] = Field(default_factory=list, min_length=1)
    evidence_ids: list[str] = Field(default_factory=list, min_length=1)
    based_on_interpretations: list[str] = Field(default_factory=list)
    based_on_signals: list[str] = Field(default_factory=list)
    primary_work_item_ids: list[str] = Field(default_factory=list, min_length=1)
    supporting_work_item_ids: list[str] = Field(default_factory=list)
    primary_entities: list[InsightPrimaryEntityItem] = Field(default_factory=list, min_length=1)
    based_on_gaps: list[str] = Field(default_factory=list)
    based_on_blockers: list[str] = Field(default_factory=list)
    based_on_highlights: list[str] = Field(default_factory=list)
    confidence: InsightConfidence
    priority: InsightPriority


class RejectedInsightDebug(BaseModel):
    """LLM insight row that did not pass schema/grounding checks (admin QA only)."""

    model_config = ConfigDict(from_attributes=False)

    index: int = Field(ge=0, description="0-based index in the model's insights[] list")
    reason: str
    raw: dict[str, Any] = Field(default_factory=dict)


class ManagerInsightPerceptionQaDebug(BaseModel):
    """§6 Step 11 — admin QA labels for regex evidence vs LLM perception path."""

    model_config = ConfigDict(from_attributes=False)

    evidence_path: Literal["regex_evidence_only", "llm_perception_plus_regex_evidence"] = Field(
        default="regex_evidence_only",
        description="Derived from VECTOR_MANAGER_INSIGHTS_PERCEPTION_LLM at run time.",
    )
    query_perception_regex: bool = Field(
        default=False,
        description="True when fetch-debug was called with ?perception=regex (hint only; does not change pipeline).",
    )
    query_include_execution_graph: bool = Field(
        default=False,
        description="True when fetch-debug was called with ?include_execution_graph=1 (§6 Step 16; attaches execution_graph JSON).",
    )
    query_master_plan_debug: bool = Field(
        default=False,
        description=(
            "True when fetch-debug used ?master_plan_debug=1 — request-scoped coordination path: perception LLM on, "
            "execution_graph attached, gaps_use_graph for this run."
        ),
    )
    query_max_decisions: int | None = Field(
        default=None,
        description="§6 Step 28: set when fetch-debug included ?max_decisions=N; else null (env default applies).",
    )
    max_decisions_cap_applied: int = Field(
        default=3,
        ge=1,
        le=50,
        description="§6 Step 28: integer cap applied to `decisions_prioritized` after Step 27 sort.",
    )
    decisions_prioritized_full_count: int = Field(
        default=0,
        ge=0,
        description="§6 Step 28: length of the full prioritized list before truncation.",
    )
    query_persist_decisions: bool = Field(
        default=False,
        description="§6 Step 32: true when fetch-debug used ?persist_decisions=1 (writes surfaced rows to DB).",
    )
    step42_gap_demotion_by_gap_type: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "§6 Step 42: per coordination gap_type integer demotion applied after Step 27 tuple "
            "(empty when all zeros / no aggregates)."
        ),
    )


class ManagerInsightsCoordinationSettingsDebug(BaseModel):
    """§6 Step 6 — env-driven coordination flags echoed on fetch-debug for admin QA."""

    model_config = ConfigDict(from_attributes=False)

    perception_llm: bool = Field(default=False, description="VECTOR_MANAGER_INSIGHTS_PERCEPTION_LLM")
    include_execution_graph: bool = Field(
        default=False,
        description="VECTOR_MANAGER_INSIGHTS_INCLUDE_EXECUTION_GRAPH",
    )
    skip_narrative_steps: bool = Field(
        default=False,
        description="VECTOR_MANAGER_INSIGHTS_SKIP_NARRATIVE_STEPS",
    )
    gaps_use_graph: bool = Field(
        default=False,
        description="VECTOR_MANAGER_INSIGHTS_GAPS_USE_GRAPH (§6 Step 18).",
    )
    hold_start_affected_wi_threshold: int = Field(
        default=2,
        ge=0,
        description=(
            "VECTOR_MANAGER_INSIGHTS_HOLD_START_AFFECTED_WI_THRESHOLD (§6 Step 26). "
            "Emit HOLD_START only when open execution count in cluster > this value."
        ),
    )
    max_decisions_surfaced: int = Field(
        default=3,
        ge=1,
        le=50,
        description="VECTOR_MANAGER_INSIGHTS_MAX_DECISIONS_SURFACED (§6 Step 28) — default cap before optional ?max_decisions=.",
    )


class InsightBundleDebug(BaseModel):
    """Step 8 bundle for admin debug; includes generation metadata for QA."""

    model_config = ConfigDict(from_attributes=False)

    run_id: uuid.UUID
    tenant_id: uuid.UUID
    window_days: int = Field(ge=1, le=366)
    items: list[InsightItemDebug] = Field(default_factory=list)
    generated_via: Literal["llm", "fallback"]
    fallback_reason: str | None = None
    model: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    llm_response_text: str | None = Field(
        default=None,
        description="Raw assistant text (may be truncated for very large responses).",
    )
    llm_response_truncated: bool = False
    llm_parsed_insight_rows: int | None = Field(
        default=None,
        ge=0,
        description="Count of object rows parsed from the model JSON (before validation).",
    )
    rejected_insights: list[RejectedInsightDebug] = Field(default_factory=list)
    llm_error: str | None = Field(
        default=None,
        description="If OpenAI failed, a short admin QA error string (not a stack trace).",
    )


class ManagerInsightFetchDebugResponse(BaseModel):
    """Admin fetch-debug payload through capped decisions (excludes V0 narrative bundles)."""

    model_config = ConfigDict(from_attributes=False)

    fetch: FetchActivityBundle
    data_reliability: DataReliabilityReport
    work_items: WorkItemBundle
    evidence: EvidenceBundle
    links: LinkBundle
    gaps: GapBundle
    key_achievements: KeyAchievementsBundleDebug
    raw_highlights: RawHighlightsBundleDebug
    signals: SignalsV0Debug
    decisions: DecisionBundle | None = Field(
        default=None,
        description=(
            "Rule-engine decisions from compute_decisions (§6 Steps 22–23); omitted or null in older payloads — "
            "fetch-debug sets a DecisionBundle (possibly zero items when gaps are empty)."
        ),
    )
    decisions_prioritized: list[DecisionBundleItem] | None = Field(
        default=None,
        description=(
            "§6 Step 27: ``prioritize_decisions`` full sort, then §6 Step 28 truncates to "
            "``min(len, max_decisions_cap)`` (default from VECTOR_MANAGER_INSIGHTS_MAX_DECISIONS_SURFACED, usually 3; "
            "override with ``?max_decisions=``). Kept rows still include ``decision_debug`` / ``decision_emission_debug``."
        ),
    )
    rejected_perception_rows: list[RejectedPerceptionRowDebug] = Field(
        default_factory=list,
        description="Rejected perception LLM rows after validation (Step 3).",
    )
    execution_graph: dict[str, Any] | None = Field(
        default=None,
        description="Ephemeral graph JSON from build_execution_graph (§6 Step 15); null unless §6 Step 16 query or env enables attachment.",
    )
    perception: dict[str, Any] | None = Field(
        default=None,
        description="Validated perception bundle / metadata (§6 Step 7–10); null until wired.",
    )
    coordination_settings: ManagerInsightsCoordinationSettingsDebug = Field(
        default_factory=ManagerInsightsCoordinationSettingsDebug,
        description="§6 Step 6 — coordination feature flags from process env (echoed for QA).",
    )
    perception_qa: ManagerInsightPerceptionQaDebug = Field(
        default_factory=ManagerInsightPerceptionQaDebug,
        description="§6 Step 11 — evidence-path label + optional ?perception=regex echo for admin QA.",
    )
    persisted_decision_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description=(
            "§6 Step 32: UUID primary keys written to ``manager_insight_decisions`` when ``?persist_decisions=1`` — "
            "one per **capped** ``decisions_prioritized`` row (same order as that list)."
        ),
    )
    coordination_contracts: CoordinationContractsDebug
