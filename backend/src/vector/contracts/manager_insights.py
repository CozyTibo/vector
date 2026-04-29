"""Step 0 canonical contracts for Manager Insights (V0)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vector.contracts.manager_insights_activity import DataReliabilityReport

SourceSystem = Literal["slack", "github", "linear", "notion", "calls"]
WorkItemType = Literal["issue", "pull_request", "document", "call", "message_thread"]
WorkItemStatus = Literal["open", "in_progress", "merged", "closed", "active", "unknown"]

LinkType = Literal["semantic_match", "shared_reference"]
LinkConfidence = Literal["high", "medium", "low"]
EvidenceConfidence = Literal["high", "medium", "low"]

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
InsightPriority = Literal["critical", "high", "medium", "low"]
InsightConfidence = Literal["high", "medium", "low"]
InsightPrimaryEntityKind = Literal["project", "feature", "system"]
ArbitrationDropReason = Literal[
    "below_priority_band",
    "insufficient_grounding",
    "duplicate_observation",
    "lower_evidence_strength",
    "capped_by_supporting_limit",
]


class _StrictModel(BaseModel):
    model_config = ConfigDict(from_attributes=False, extra="forbid")


class WorkItem(_StrictModel):
    id: str
    type: WorkItemType
    source: SourceSystem
    title: str
    summary: str | None = None
    status: WorkItemStatus | None = None
    project: str | None = None
    owner: str | None = None
    participants: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    closed_at: datetime | None = None
    source_ref: dict[str, str] = Field(default_factory=dict)


class Link(_StrictModel):
    id: str
    from_work_item_id: str
    to_work_item_id: str
    type: LinkType
    confidence: LinkConfidence
    evidence: list[str] = Field(default_factory=list, min_length=1)
    similarity: float = Field(ge=0.0, le=1.0)
    method: str


class ActionItem(_StrictModel):
    id: str
    text: str
    source: str
    evidence: str
    linked_work_items: list[str] = Field(default_factory=list)
    confidence: EvidenceConfidence


class Blocker(_StrictModel):
    id: str
    text: str
    source: str
    evidence: str
    linked_work_items: list[str] = Field(default_factory=list)
    confidence: EvidenceConfidence


class Decision(_StrictModel):
    id: str
    text: str
    source: str
    evidence: str
    linked_work_items: list[str] = Field(default_factory=list)
    confidence: EvidenceConfidence


class ExpectedWork(_StrictModel):
    action_item_id: str
    linked_work_items: list[str] = Field(default_factory=list)


class ActualWork(_StrictModel):
    issue_ids: list[str] = Field(default_factory=list)
    pull_request_ids: list[str] = Field(default_factory=list)


class Gap(_StrictModel):
    id: str
    type: GapType
    description: str
    evidence_pointers: dict[str, list[str] | str] = Field(default_factory=dict)


class DeliveryMetrics(_StrictModel):
    issues_completed: int = Field(ge=0)
    prs_merged_count: int = Field(ge=0)
    active_projects: int = Field(ge=0)
    open_urgent_items: int = Field(ge=0)


class KeyAchievement(_StrictModel):
    id: str
    title: str
    linked_items: list[str] = Field(default_factory=list, min_length=1)
    evidence: list[str] = Field(default_factory=list, min_length=1)
    created_at: datetime | None = None


class KeyAchievementsBundle(_StrictModel):
    items: list[KeyAchievement] = Field(default_factory=list)


class RawHighlight(_StrictModel):
    id: str
    text: str
    sources: list[str] = Field(default_factory=list, min_length=1)


class RawHighlightsBundle(_StrictModel):
    items: list[RawHighlight] = Field(default_factory=list)


class SignalsV0(_StrictModel):
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


class InterpretationV0(_StrictModel):
    id: str
    type: InterpretationType
    description: str
    based_on_signals: list[str] = Field(
        default_factory=list,
        description="Optional supporting signal ids; execution grounding uses gaps/blockers/highlights.",
    )
    evidence: list[str] = Field(default_factory=list, min_length=1)
    confidence: InterpretationConfidence
    based_on_gaps: list[str] = Field(
        default_factory=list,
        description="Step-5 gap ids this interpretation is anchored to.",
    )
    based_on_blockers: list[str] = Field(
        default_factory=list,
        description="Step-3 evidence item ids (kind=blocker) cited by this interpretation.",
    )
    based_on_highlights: list[str] = Field(
        default_factory=list,
        description="Step-5.6 raw highlight ids cited by this interpretation.",
    )

    @model_validator(mode="after")
    def _interpretation_has_execution_grounding(self) -> Self:
        if not (self.based_on_gaps or self.based_on_blockers or self.based_on_highlights):
            raise ValueError(
                "interpretation must cite at least one of based_on_gaps, based_on_blockers, "
                "or based_on_highlights"
            )
        return self


class InsightPrimaryEntity(_StrictModel):
    """Named execution surface the insight is anchored to (project / feature / system)."""

    name: str = Field(min_length=1)
    kind: InsightPrimaryEntityKind


class InsightV0(_StrictModel):
    id: str
    observation: str
    interpretation: str
    implication: str
    evidence: list[str] = Field(default_factory=list, min_length=1)
    evidence_ids: list[str] = Field(
        default_factory=list,
        min_length=1,
        description="Step-3 evidence item ids (action_item / blocker / decision) backing the insight.",
    )
    based_on_interpretations: list[str] = Field(default_factory=list)
    based_on_signals: list[str] = Field(default_factory=list)
    primary_work_item_ids: list[str] = Field(
        default_factory=list,
        min_length=1,
        description="Primary Step-2 work item ids this insight is about.",
    )
    supporting_work_item_ids: list[str] = Field(
        default_factory=list,
        description="Additional related Step-2 work item ids (may be empty).",
    )
    primary_entities: list[InsightPrimaryEntity] = Field(
        default_factory=list,
        min_length=1,
        description="At least one concrete project/feature/system anchor.",
    )
    based_on_gaps: list[str] = Field(default_factory=list, description="Step-5 gap ids tied to this insight.")
    based_on_blockers: list[str] = Field(
        default_factory=list,
        description="Step-3 evidence item ids (kind=blocker) tied to this insight.",
    )
    based_on_highlights: list[str] = Field(
        default_factory=list,
        description="Step-5.6 raw highlight ids tied to this insight.",
    )
    confidence: InsightConfidence
    priority: InsightPriority

    @model_validator(mode="after")
    def _insight_has_execution_grounding(self) -> Self:
        if not (self.based_on_gaps or self.based_on_blockers or self.based_on_highlights):
            raise ValueError(
                "insight must cite at least one of based_on_gaps, based_on_blockers, or based_on_highlights"
            )
        return self


class DroppedInsight(_StrictModel):
    insight_id: str
    drop_reason: ArbitrationDropReason
    evidence_pointers: list[str] = Field(default_factory=list, min_length=1)


class InsightArbitrationResult(_StrictModel):
    primary_issue_id: str | None = None
    supporting_issue_ids: list[str] = Field(default_factory=list, max_length=2)
    dropped_insights: list[DroppedInsight] = Field(default_factory=list)


class ReportV0(_StrictModel):
    summary: str
    key_risks_ranked: list[str] = Field(default_factory=list)
    delivery_pulse: str
    recent_wins: list[str] = Field(default_factory=list)
    collaboration_and_ways_of_working: list[str] = Field(default_factory=list)
    development_signals: list[str] = Field(default_factory=list)
    open_action_items: list[str] = Field(default_factory=list)
    coaching_questions: list[str] = Field(default_factory=list, max_length=4)
    one_priority: str
    final_markdown: str


class UserReportContext(_StrictModel):
    run_id: str
    tenant_id: str
    subject_user_id: str
    window_days: int = Field(ge=1, le=366)
    generated_at: datetime
    data_reliability: DataReliabilityReport
    delivery_metrics: DeliveryMetrics
    work_items: list[WorkItem] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    blockers: list[Blocker] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    expected_work: list[ExpectedWork] = Field(default_factory=list)
    actual_work: ActualWork
    gaps: list[Gap] = Field(default_factory=list)
    key_achievements: KeyAchievementsBundle = Field(default_factory=KeyAchievementsBundle)
    raw_highlights: RawHighlightsBundle = Field(default_factory=RawHighlightsBundle)
    signals: SignalsV0
    interpretations: list[InterpretationV0] = Field(default_factory=list)
    insights: list[InsightV0] = Field(default_factory=list)
    arbitration: InsightArbitrationResult

