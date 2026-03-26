"""HTTP contracts for /debug/canonical."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[dict[str, Any]]


class CanonicalStatusResponse(BaseModel):
    tenant_id: uuid.UUID
    connection_id: uuid.UUID
    connector: str
    step3_last_processed_replay_sequence: int = Field(
        ...,
        description="Last replay_sequence committed by Step 3 for this scope",
    )
    step3_last_processed_id: int = Field(
        ...,
        description="Tie-breaker raw record id (same ordering as Step 2)",
    )
    step3_lag_rows: int
    step3_last_processed_timestamp: datetime | None
    step2_watermark_replay_sequence: int = 0
    step2_watermark_id: int = 0


class SubgraphAnchor(BaseModel):
    type: Literal["artifact", "actor"]
    id: uuid.UUID


class SubgraphNode(BaseModel):
    id: str
    node_type: Literal["artifact", "actor"]
    artifact_kind: str | None = None
    actor_kind: str | None = None
    label: str | None = None
    status: str | None = None
    last_observed_at: datetime | None = None


class SubgraphEdge(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    target_id: uuid.UUID
    relation_kind: str
    directed: bool = True
    valid_from: datetime
    valid_to: datetime | None = None


class SubgraphResponse(BaseModel):
    anchor: SubgraphAnchor
    depth: int
    nodes: list[SubgraphNode]
    edges: list[SubgraphEdge]
    truncated: bool = False
    truncation_reason: str | None = None
