"""API contracts — debug projection viewer."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectionRowsResponse(BaseModel):
    connector: str
    connection_id: UUID
    entity: str
    total: int
    limit: int
    offset: int
    items: list[dict[str, Any]] = Field(default_factory=list)


class RawIngestionRecordDebugItem(BaseModel):
    id: int
    replay_sequence: int
    connection_id: UUID
    connector: str
    resource_type: str
    external_id: str
    http_status: int
    fetched_at: str
    run_id: UUID
    payload_body: dict[str, Any]


class RawIngestionRecordDebugResponse(BaseModel):
    item: RawIngestionRecordDebugItem
