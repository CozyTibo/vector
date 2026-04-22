"""Admin (internal) API payloads."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OnboardingChatMessageItem(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class SlackStakeholdersSnapshot(BaseModel):
    """answers_json.slack_stakeholders: Slack member chosen for in-Slack onboarding handoff."""

    model_config = ConfigDict(from_attributes=False)

    raw_text: str | None = None
    slack_user_ids: list[str] = Field(default_factory=list)


class TenantListItem(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: uuid.UUID
    company_name: str
    created_at: datetime
    workspace_access_enabled: bool = False
    onboarding_status: str | None = None
    onboarding_current_step: str | None = None
    connected_connectors: list[str] = Field(default_factory=list)


class TenantListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    items: list[TenantListItem]


class AdminUserListItem(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: uuid.UUID
    email: str
    full_name: str | None = None
    created_at: datetime
    has_password: bool = Field(
        default=False,
        description="True when users.password_hash is set (email/password accounts).",
    )
    membership_count: int = Field(
        default=0,
        ge=0,
        description="Rows in tenant_memberships for this user.",
    )
    tenant_connections_as_connector_count: int = Field(
        default=0,
        ge=0,
        description="tenant_connections rows with connected_by_user_id = this user.",
    )
    orphan_eligible: bool = Field(
        default=False,
        description="True when the user can be hard-deleted (no memberships, no connector rows).",
    )


class AdminUserListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    items: list[AdminUserListItem]


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
    connect_queue: list[str] = Field(
        default_factory=list,
        description="Remaining connector OAuth queue from answers_json.connect_queue.",
    )
    connect_plan: list[str] = Field(
        default_factory=list,
        description="Original connector plan from answers_json.connect_plan (same ids as connect_queue when fresh).",
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
    company_size: str | None = Field(
        default=None,
        description="answers_json.company.size: exact headcount string, or band label (e.g. 5-15).",
    )
    user_role: str | None = Field(default=None, description="From answers_json.profile.role.")
    tools_engineering: list[str] = Field(default_factory=list)
    tools_pm: list[str] = Field(default_factory=list)
    tools_communication: list[str] = Field(default_factory=list)
    tools_calls: list[str] = Field(
        default_factory=list,
        description="Video call tool ids from answers_json.tools.calls.",
    )
    tools_calendars: list[str] = Field(
        default_factory=list,
        description="Calendar tool ids from answers_json.tools.calendars.",
    )
    tools_docs: list[str] = Field(default_factory=list)
    tools_stack: dict[str, Any] | None = Field(
        default=None,
        description="Legacy wizard: tools by category from answers_json.tools_stack.",
    )
    slack_stakeholders: SlackStakeholdersSnapshot | None = Field(
        default=None,
        description=(
            "Slack handoff: Vector user mapped to a member (answers_json.slack_stakeholders)."
        ),
    )
    chat_messages: list[OnboardingChatMessageItem] = Field(
        default_factory=list,
        description="Recent onboarding chat rows (append-only log).",
    )


class AdminToolOptionItem(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: str
    label: str


class AdminOnboardingAnswerOptionsResponse(BaseModel):
    """Allowed values for admin edits (mirrors product onboarding catalog)."""

    model_config = ConfigDict(from_attributes=False)

    profile_roles: list[str]
    tools_by_category: dict[str, list[AdminToolOptionItem]]


class AdminOnboardingCollectedDataPatch(BaseModel):
    """PATCH onboarding ``answers_json`` only — user/company/tool fields (not status, step, or timestamps)."""

    model_config = ConfigDict(extra="forbid")

    user_role: str | None = None
    company_website: str | None = None
    company_size: str | None = None
    company_domain: str | None = None
    tools_interest: list[str] | None = None
    tools_engineering: list[str] | None = None
    tools_pm: list[str] | None = None
    tools_communication: list[str] | None = None
    tools_calls: list[str] | None = None
    tools_calendars: list[str] | None = None
    tools_docs: list[str] | None = None


class AdminTenantPrimaryMemberFullNamePatchRequest(BaseModel):
    """PATCH ``users.full_name`` for the oldest membership on this tenant."""

    model_config = ConfigDict(extra="forbid")

    member_full_name: str | None = Field(
        ...,
        max_length=255,
        description="Display name; JSON null or empty string clears ``users.full_name``.",
    )


class TenantAdminDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: uuid.UUID
    company_name: str
    created_at: datetime
    workspace_access_enabled: bool = False
    onboarding: OnboardingAdminSnapshot | None = None
    member_full_name: str | None = Field(
        default=None,
        description="First membership user's full_name (users.full_name).",
    )
    member_email: str | None = Field(
        default=None,
        description="First membership user's email (users.email).",
    )
    connected_connectors: list[str] = Field(default_factory=list)
    slack_vector_paused: bool = Field(
        default=False,
        description=(
            "When true, Vector skips outbound Slack sends for this tenant "
            "(including manager onboarding DMs)."
        ),
    )


class AdminTenantWorkspaceAccessRequest(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    workspace_access_enabled: bool


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


class AdminHardDeleteTenantRequest(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    confirmation: str = Field(
        ...,
        description="Must exactly match the server phrase shown in the admin delete dialog.",
    )
    company_name_confirmation: str = Field(
        ...,
        description="Must match the tenant company name (after trim) for an extra safeguard.",
    )


class AdminResetTenantToSignupRequest(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    confirmation: str = Field(
        ...,
        description="Must exactly match RESET_TENANT_TO_SIGNUP_CONFIRMATION_PHRASE in the admin UI.",
    )
    company_name_confirmation: str = Field(
        ...,
        description="Must match the tenant company name (after trim) for an extra safeguard.",
    )


class AdminResetTenantToSignupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    tenant_id: uuid.UUID
    company_name: str
    deleted_relationships: int
    deleted_mapping_events: int
    deleted_current_mappings: int
    deleted_external_references: int
    deleted_actor_external_identities: int
    deleted_artifacts: int
    deleted_actors: int
    deleted_step3_canonical_cursors: int
    deleted_github_projection_rows: int
    deleted_linear_projection_rows: int
    deleted_connector_projection_progress_rows: int
    deleted_raw_records: int
    deleted_ingestion_runs: int
    deleted_sync_state_rows: int
    deleted_tenant_connections: int
    deleted_manager_onboarding_sessions: int


class AdminHardDeleteTenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    deleted_tenant_id: uuid.UUID
    deleted_company_name: str
    deleted_relationships: int
    deleted_mapping_events: int
    deleted_current_mappings: int
    deleted_external_references: int
    deleted_actor_external_identities: int
    deleted_artifacts: int
    deleted_actors: int
    deleted_step3_canonical_cursors: int
    deleted_github_projection_rows: int
    deleted_linear_projection_rows: int
    deleted_connector_projection_progress_rows: int
    deleted_raw_records: int
    deleted_ingestion_runs: int
    deleted_sync_state_rows: int


class AdminHardDeleteTenantBulkItem(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    tenant_id: uuid.UUID
    company_name_confirmation: str = Field(
        ...,
        description="Must match that tenant's company name (after trim).",
    )


class AdminHardDeleteTenantsBulkRequest(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    confirmation: str = Field(
        ...,
        description="Must exactly match HARD_DELETE_TENANT_CONFIRMATION_PHRASE.",
    )
    tenants: list[AdminHardDeleteTenantBulkItem] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Each tenant is validated and deleted in order within one transaction.",
    )


class AdminHardDeleteTenantsBulkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    results: list[AdminHardDeleteTenantResponse]


class AdminHardDeleteOrphanUserRequest(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    confirmation: str = Field(
        ...,
        description="Must exactly match HARD_DELETE_ORPHAN_USER_CONFIRMATION_PHRASE.",
    )
    email_confirmation: str = Field(
        ...,
        description="Must match the user's email (after trim).",
    )


class AdminHardDeleteOrphanUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    deleted_user_id: uuid.UUID
    deleted_email: str
