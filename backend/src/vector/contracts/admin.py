"""Admin (internal) API payloads."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OnboardingChatMessageItem(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    role: str
    content: str
    created_at: datetime


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
    profile_phase: str | None = Field(
        default=None,
        description="Chat profile sub-step from answers_json.profile_phase.",
    )
    tools_interest: list[str] = Field(default_factory=list)
    company_domain: str | None = Field(
        default=None,
        description="From onboarding answers_json if provided.",
    )
    company_website: str | None = Field(
        default=None,
        description="From answers_json.company.website (or legacy company_domain).",
    )
    company_size: str | None = Field(default=None, description="From answers_json.company.size.")
    user_role: str | None = Field(default=None, description="From answers_json.profile.role.")
    tools_engineering: list[str] = Field(default_factory=list)
    tools_pm: list[str] = Field(default_factory=list)
    tools_communication: list[str] = Field(default_factory=list)
    tools_docs: list[str] = Field(default_factory=list)
    tools_stack: dict[str, Any] | None = Field(
        default=None,
        description="Legacy wizard: tools by category from answers_json.tools_stack.",
    )
    chat_messages: list[OnboardingChatMessageItem] = Field(
        default_factory=list,
        description="Recent onboarding chat rows (append-only log).",
    )


class TenantAdminDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: uuid.UUID
    company_name: str
    created_at: datetime
    onboarding: OnboardingAdminSnapshot | None = None
    member_full_name: str | None = Field(
        default=None,
        description="First membership user's full_name (users.full_name).",
    )
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
    connector: str = Field(description="github | linear | …")
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


class RawIngestionAdminDetail(BaseModel):
    """Single Step 1 envelope for admin inspection (full payload + request metadata)."""

    model_config = ConfigDict(from_attributes=False)

    id: int
    connection_id: uuid.UUID
    run_id: uuid.UUID
    connector: str
    source_trigger: str
    replay_sequence: int
    resource_type: str
    external_id: str
    api_endpoint: str
    query_params: dict[str, Any]
    payload_hash: str
    http_status: int
    fetched_at: datetime
    payload_body: dict[str, Any]


class RawIngestionAdminDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    item: RawIngestionAdminDetail


class AdminStep1RawResetRequest(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    confirmation: str = Field(
        ...,
        description=(
            "Must exactly match the server phrase (see admin Step1 UI). "
            "Prevents accidental destructive resets."
        ),
    )


class AdminStep1RawResetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    deleted_raw_records: int
    deleted_ingestion_runs: int
    deleted_sync_state_rows: int


class AdminStep2ProjectionsResetRequest(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    confirmation: str = Field(
        ...,
        description=(
            "Must exactly match the server phrase (see admin Step2 UI). "
            "Prevents accidental destructive resets."
        ),
    )


class AdminStep2ProjectionsResetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    deleted_github_projection_rows: int
    deleted_linear_projection_rows: int
    deleted_connector_projection_progress_rows: int


class AdminStep3CanonicalResetRequest(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    confirmation: str = Field(
        ...,
        description=(
            "Must exactly match the server phrase (see admin Step3 UI). "
            "Prevents accidental destructive resets."
        ),
    )


class AdminStep3CanonicalResetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    deleted_relationships: int
    deleted_mapping_events: int
    deleted_current_mappings: int
    deleted_external_references: int
    deleted_actor_external_identities: int
    deleted_artifacts: int
    deleted_actors: int
    deleted_step3_canonical_cursors: int
