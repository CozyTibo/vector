"""Operator admin v2 contracts — separate from legacy admin.py cortex payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OperatorStatusBanner(BaseModel):
    lease_status: str | None = None
    fsm_state: str | None = None
    phase_cursor: str | None = None
    block_reason_code: str | None = None
    block_detail: str | None = None
    obligation_epoch: int | None = None
    target_epoch: int | None = None
    pipeline_run_id: str | None = None
    last_transition_at: datetime | None = None
    last_transition_trigger: str | None = None
    last_transition_from_state: str | None = None
    last_transition_to_state: str | None = None


class OperatorContinuityFact(BaseModel):
    key: Literal["ingestion", "execution", "graph", "retrieval", "synthesis"]
    text: str
    inspect_lens: str | None = None


class OperatorRecentEvent(BaseModel):
    kind: Literal["ingestion_run", "execution_transition"]
    at: datetime
    summary: str
    detail: dict[str, Any] | None = None


class OperatorPhaseReceiptSummary(BaseModel):
    phase_id: str
    status: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_detail: str | None = None
    receipt_digest: str | None = None
    output_summary: dict[str, Any] = Field(default_factory=dict)


class OperatorQueueCounts(BaseModel):
    deferral_retry_ready: int = 0
    synthesis_failed: int = 0
    tcre_queued: int = 0


class OperatorContinuitySnapshotRead(BaseModel):
    available: bool = False
    captured_at_utc: datetime | None = None
    graph_summary: dict[str, Any] | None = None
    retrieval_summary: dict[str, Any] | None = None
    synthesis_summary: dict[str, Any] | None = None


class OperatorConnectorRow(BaseModel):
    connector: str
    connection_id: str | None = None
    connection_status: str | None = None
    cortex_routed: bool = False
    checkpoint_last_incremental_at: str | None = None
    latest_run: dict[str, Any] | None = None


class OperatorSchedulerState(BaseModel):
    env_scheduler_enabled: bool = False
    paused_via_redis: bool = False
    operator_mode_label: str | None = None
    beat_interval_seconds: int = 1800
    min_gap_seconds: int = 120


class OperatorOverviewResponse(BaseModel):
    surface_kind: Literal["operator_overview_v1"] = "operator_overview_v1"
    tenant_id: str
    generated_at_utc: datetime
    status_banner: OperatorStatusBanner
    continuity_facts: list[OperatorContinuityFact]
    recent_events: list[OperatorRecentEvent]
    connectors: list[OperatorConnectorRow]
    phase_receipts: dict[str, OperatorPhaseReceiptSummary]
    queue_counts: OperatorQueueCounts
    continuity_snapshot: OperatorContinuitySnapshotRead
    scheduler: OperatorSchedulerState
    runnable_connectors: list[str] = Field(default_factory=list)
    query_groups_used: int = Field(
        description="Bounded query groups executed (target cap 8 for operator overview)."
    )


class AdminBuildInfoResponse(BaseModel):
    surface_kind: Literal["admin_build_info"] = "admin_build_info"
    git_sha: str | None = None
    git_sha_short: str | None = None
    cortex_admin_v2_enabled: bool = False
    env: str = "development"


class OperatorRuntimeLease(BaseModel):
    status: str | None = None
    fsm_state: str | None = None
    phase_cursor: str | None = None
    obligation_epoch: int | None = None
    target_epoch: int | None = None
    pipeline_run_id: str | None = None
    block_reason_code: str | None = None
    block_detail: Any | None = None
    last_error: str | None = None
    canonical_lane_status: str | None = None
    execution_lane_status: str | None = None


class OperatorRuntimeTransition(BaseModel):
    from_state: str
    to_state: str
    trigger: str
    gate_result: str | None = None
    receipt_hash: str | None = None
    pipeline_run_id: str | None = None
    created_at: datetime
    detail_json: dict[str, Any] = Field(default_factory=dict)


class OperatorRuntimeResponse(BaseModel):
    surface_kind: Literal["operator_runtime_v1"] = "operator_runtime_v1"
    tenant_id: str
    generated_at_utc: datetime
    lease: OperatorRuntimeLease | None = None
    dual_lane: dict[str, Any] = Field(default_factory=dict)
    progression: dict[str, Any] = Field(default_factory=dict)
    transitions: list[OperatorRuntimeTransition]
    transition_total: int
    transition_limit: int
    transition_offset: int
    queue_counts: OperatorQueueCounts


OperatorActionKind = Literal[
    "run_from_ingestion",
    "run_from_phase",
    "restart_execution",
    "clear_derived",
    "flush_derived",
    "flush_all",
    "rebuild_retrieval_index",
    "p0_recover",
]


class OperatorActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: OperatorActionKind
    start_phase: Literal[
        "canonical",
        "identity",
        "graph",
        "reconstruction",
        "retrieval",
        "synthesis",
    ] | None = None
    from_phase: str | None = None
    confirmation: str | None = None
    force: bool = False
    break_glass: bool = False
    scope: str | None = None
    pipeline_run_id: UUID | None = None
    p0_strategy: Literal["new_run", "recover_in_place"] = "new_run"
    source_pipeline_run_id: UUID | None = None


class OperatorActionResponse(BaseModel):
    surface_kind: Literal["operator_action_v1"] = "operator_action_v1"
    action: OperatorActionKind
    tenant_id: str
    result: dict[str, Any] = Field(default_factory=dict)


class OperatorGraphSnapshotResponse(BaseModel):
    surface_kind: Literal["operator_graph_snapshot_v1"] = "operator_graph_snapshot_v1"
    tenant_id: str
    available: bool = False
    captured_at_utc: datetime | None = None
    stale: bool = False
    stale_after_minutes: int = 15
    graph_summary: dict[str, Any] | None = None
    identity_summary: dict[str, Any] | None = None
    component_snapshot: dict[str, Any] = Field(default_factory=dict)
    prose_summary: str = ""


class OperatorGraphComponentRefreshResponse(BaseModel):
    surface_kind: Literal["operator_graph_component_refresh_v1"] = "operator_graph_component_refresh_v1"
    tenant_id: str
    enqueued: bool
    job_status: str
    hint: str | None = None


OperatorQueueTab = Literal["synthesis_failed", "tcre_queued", "deferrals", "ingestion_failed"]


class OperatorQueueCounts(BaseModel):
    synthesis_failed: int = 0
    tcre_queued: int = 0
    deferrals: int = 0
    ingestion_failed: int = 0


class OperatorQueuesResponse(BaseModel):
    surface_kind: Literal["operator_queues_v1"] = "operator_queues_v1"
    tenant_id: str
    tab: OperatorQueueTab
    items: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
    counts: OperatorQueueCounts
    generated_at_utc: datetime


class OperatorEdgeProvenanceRow(BaseModel):
    model_config = ConfigDict(extra="allow")

    link_id: str | None = None
    link_type: str | None = None
    source_entity_id: str | None = None
    target_entity_id: str | None = None
    rule_id: str | None = None
    link_authority: str | None = None
    promoted_from_candidate_id: str | None = None
    promotion_batch_id: Any | None = None
    created_at: str | None = None
    revoked_at: str | None = None
    evidence_raw_record_ids: list[int] = Field(default_factory=list)


class OperatorEdgeProvenanceResponse(BaseModel):
    surface_kind: Literal["operator_edge_provenance_v1"] = "operator_edge_provenance_v1"
    tenant_id: str
    query: dict[str, Any] = Field(default_factory=dict)
    edges: list[dict[str, Any]]
    total: int


class OperatorIslandRow(BaseModel):
    model_config = ConfigDict(extra="allow")

    island_scope_id: str
    entity_count: int = 0
    authoritative_edge_count: int = 0
    last_walk_at: str | None = None
    last_retrieval_epoch: str | None = None


class OperatorIslandsListResponse(BaseModel):
    surface_kind: Literal["operator_islands_list_v1"] = "operator_islands_list_v1"
    tenant_id: str
    island_count: int
    islands: list[dict[str, Any]]
