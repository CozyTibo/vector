"""Operator admin v2 contracts — separate from legacy admin.py cortex payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


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
