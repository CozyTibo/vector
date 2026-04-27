"""Contracts for Manager insights Step 1 (FetchActivity) + Step 0.5 (Data reliability)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ManagerInsightConnector = Literal["slack", "github", "linear", "notion", "calls"]

DataReliabilityTier = Literal["high", "medium", "low"]
WorkItemType = Literal["issue", "pull_request", "document", "call", "message_thread"]


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


class ManagerInsightFetchDebugResponse(BaseModel):
    """Admin (and internal) debug payload: Step 1 + Step 0.5 + Step 2."""

    model_config = ConfigDict(from_attributes=False)

    fetch: FetchActivityBundle
    data_reliability: DataReliabilityReport
    work_items: WorkItemBundle
