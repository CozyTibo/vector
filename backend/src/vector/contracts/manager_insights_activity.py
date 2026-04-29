"""Contracts for Manager insights debug pipeline artifacts (Steps 1–8)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

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
    """Step 6 deterministic signal vector plus explainable reasons."""

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
        description="If the OpenAI call failed, a short error string for admin QA (not a stack trace).",
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
        description="If the OpenAI call failed, a short error string for admin QA (not a stack trace).",
    )


class ManagerInsightFetchDebugResponse(BaseModel):
    """Admin (and internal) debug payload through Step 8 (Insights)."""

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
    interpretations: InterpretationBundleDebug
    insights: InsightBundleDebug
