"""Admin (internal) API payloads."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TenantListItem(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: uuid.UUID
    company_name: str
    created_at: datetime
    onboarding_status: str | None = None
    onboarding_current_step: str | None = None
    connected_connectors: list[str] = Field(default_factory=list)


class TenantListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    items: list[TenantListItem]


class OnboardingAdminSnapshot(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    status: str
    current_step: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    abandoned_at: datetime | None = None
    tools_interest: list[str] = Field(default_factory=list)
    company_domain: str | None = Field(
        default=None,
        description="From onboarding answers_json if provided.",
    )
    tools_stack: dict[str, Any] | None = Field(
        default=None,
        description="Product research: tools by category from answers_json.tools_stack.",
    )


class TenantAdminDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: uuid.UUID
    company_name: str
    created_at: datetime
    onboarding: OnboardingAdminSnapshot | None = None
    connected_connectors: list[str] = Field(default_factory=list)


class TenantConnectionAdminItem(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: uuid.UUID
    provider: str
    status: str
    created_at: datetime


class AdminConnectionsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    items: list[TenantConnectionAdminItem]


class RawIngestionAdminItem(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: int = Field(description="raw_ingestion_records.id")
    replay_sequence: int
    resource_type: str
    external_id: str
    fetched_at: datetime
    http_status: int


class RawIngestionAdminPage(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    total: int
    limit: int
    offset: int
    items: list[RawIngestionAdminItem]
