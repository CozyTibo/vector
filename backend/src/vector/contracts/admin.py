"""Admin (internal) API payloads."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

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


class SlackCollaboratorMemberSnapshot(BaseModel):
    """One row in ``answers_json.slack_collaborators.members``."""

    model_config = ConfigDict(from_attributes=False)

    slack_user_id: str
    username: str
    label: str


class SlackCollaboratorsSnapshot(BaseModel):
    """answers_json.slack_collaborators: managers / leads the user works with in Slack."""

    model_config = ConfigDict(from_attributes=False)

    members: list[SlackCollaboratorMemberSnapshot] = Field(default_factory=list)


class SlackWatchChannelSnapshot(BaseModel):
    """One row in ``answers_json.slack_watch_channels.channels``."""

    model_config = ConfigDict(from_attributes=False)

    channel_id: str
    name: str


class SlackWatchChannelsSnapshot(BaseModel):
    """answers_json.slack_watch_channels: public channels to watch for the team."""

    model_config = ConfigDict(from_attributes=False)

    channels: list[SlackWatchChannelSnapshot] = Field(default_factory=list)


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
    slack_collaborators: SlackCollaboratorsSnapshot | None = Field(
        default=None,
        description="Slack collaborator picks from product onboarding (answers_json.slack_collaborators).",
    )
    slack_team_members: SlackCollaboratorsSnapshot | None = Field(
        default=None,
        description="Teammates (non-managers) from answers_json.slack_team_members (same member shape).",
    )
    slack_watch_channels: SlackWatchChannelsSnapshot | None = Field(
        default=None,
        description="Slack channels to watch from answers_json.slack_watch_channels.",
    )
    slack_introduce_managers_consent: str | None = Field(
        default=None,
        description=(
            "Product wrap-up: whether Vector may introduce itself in Slack to other managers "
            "(``yes`` | ``later`` | ``not_applicable``)."
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
        description="When true, Vector skips outbound Slack sends for this tenant.",
    )


class AdminTenantWorkspaceAccessRequest(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    workspace_access_enabled: bool


class AdminTenantSlackDeliveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slack_vector_paused: bool


class TenantConnectionAdminItem(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: uuid.UUID
    provider: str
    status: str
    created_at: datetime


class AdminConnectionsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    items: list[TenantConnectionAdminItem]


class AdminConnectorConnectLinkResponse(BaseModel):
    """Admin-generated URL to run a tenant-scoped OAuth connect flow."""

    model_config = ConfigDict(from_attributes=False)

    provider: Literal["slack", "github", "linear", "notion", "calls"]
    connect_url: str
    tenant_id: uuid.UUID
    user_id: uuid.UUID


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


CortexIngestionConnectorId = Literal["calls", "github", "linear", "notion", "slack"]


class AdminCortexIngestionRunSummary(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    run_id: uuid.UUID
    status: str
    replay_mode: bool
    sync_mode: str
    source_trigger: str
    started_at: datetime
    finished_at: datetime | None
    error_summary: str | None = None
    raw_rows_written: int | None = None


class AdminCortexConnectorIngestionRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    connector: str
    connection_id: uuid.UUID | None = None
    connection_status: str | None = None
    cortex_routed: bool
    queue_lane_live: str = Field(default="cortex_live")
    queue_lane_replay: str = Field(default="cortex_replay")
    checkpoint_last_incremental_at: str | None = None
    latest_run: AdminCortexIngestionRunSummary | None = None


class AdminCortexGlobalScheduler(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    env_scheduler_enabled: bool
    beat_interval_seconds: int
    min_gap_seconds: int
    verify_after_sync: bool
    redis_url_configured: bool
    paused_via_redis: bool
    operator_mode_label: Literal[
        "Active",
        "Off (env)",
        "Paused (operator)",
        "Off (env) + paused (operator)",
    ]


class AdminCortexWorkerTelemetry(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    status: Literal["ok", "no_workers", "unavailable", "error"]
    worker_count: int
    live_queue_workers: int
    replay_queue_workers: int
    worker_names: list[str]
    detail: str | None = None


class AdminCortexDuplicatePreventionMetric(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    status: Literal["ok", "warn", "unavailable"]
    ratio_percent: float | None = None
    live_rows_examined: int
    duplicate_groups: int
    duplicate_rows_excess: int
    detail: str | None = None


class AdminCortexIngestionDigest(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    objective: str
    bottleneck_hint: str
    confidence_note: str
    recommended_actions: list[str]


class AdminCortexIngestionOverviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    tenant_id: uuid.UUID
    company_name: str
    global_scheduler: AdminCortexGlobalScheduler
    worker_telemetry: AdminCortexWorkerTelemetry
    duplicate_prevention: AdminCortexDuplicatePreventionMetric
    digest: AdminCortexIngestionDigest
    connectors: list[AdminCortexConnectorIngestionRow]


class AdminCortexIngestionTriggerSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector: CortexIngestionConnectorId
    connection_id: uuid.UUID | None = None
    sync_mode: Literal["incremental", "backfill"] = "incremental"
    confirmation: str = Field(
        ...,
        description="Must exactly match the server phrase for manual Cortex sync (see admin UI).",
    )


class AdminCortexIngestionTriggerSyncResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    enqueued: bool = True
    queue: Literal["cortex_live"] = "cortex_live"
    connector: str
    connection_id: uuid.UUID
    tenant_id: uuid.UUID
    sync_mode: Literal["incremental", "backfill"] = "incremental"
    source_trigger: str = "manual_admin"


class AdminCortexIngestionTriggerReplayRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector: CortexIngestionConnectorId
    connection_id: uuid.UUID | None = None
    replay_version: int = Field(default=1, ge=1, le=1000)
    confirmation: str = Field(
        ...,
        description="Must exactly match the server phrase for Cortex replay (see admin UI).",
    )


class AdminCortexIngestionTriggerReplayResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    replay_job_id: uuid.UUID
    queue: Literal["cortex_replay"] = "cortex_replay"
    connector: str
    connection_id: uuid.UUID
    tenant_id: uuid.UUID
    replay_version: int


class AdminCortexSchedulerPauseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paused: bool
    confirmation: str = Field(
        ...,
        description="Must match PAUSE or RESUME phrase from admin UI depending on paused flag.",
    )


class AdminCortexSchedulerPauseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    paused_via_redis: bool


class AdminCortexIngestionVerificationResponse(BaseModel):
    """Structured output of :func:`verify_tenant_ingestion_invariants` for operators."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    passed: bool
    runs_examined: int
    run_reports: list[dict[str, Any]]
    checkpoint_report: dict[str, Any]
    exhaust_depth: dict[str, Any] | None = None
    runtime_correctness: dict[str, Any] | None = None


class AdminCortexIngestionRecentRunItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: uuid.UUID
    connector: str
    status: str
    source_trigger: str
    replay_mode: bool
    started_at: datetime
    finished_at: datetime | None = None
    error_summary: str | None = None
    raw_rows_written: int | None = None
    connection_id: uuid.UUID | None = None
    sync_mode: str | None = None
    replay_job_id: uuid.UUID | None = None
    replay_version: int | None = None


class AdminCortexIngestionRecentRunsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AdminCortexIngestionRecentRunItem]


class AdminCortexConnectorRawRecordItem(BaseModel):
    """One raw ingestion row for a connector (append-only store)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    run_id: uuid.UUID
    resource_type: str
    external_id: str
    api_endpoint: str
    query_params: dict[str, Any]
    payload_body: dict[str, Any]
    http_status: int
    fetched_at: datetime
    idempotency_key: str | None = None
    source_identity_key: str | None = None
    source_revision_key: str | None = None
    replay_job_id: uuid.UUID | None = None
    replay_version: int | None = None


class AdminCortexConnectorRawRecordsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: uuid.UUID
    connector: str
    items: list[AdminCortexConnectorRawRecordItem]
    total_count: int
    offset: int
    limit: int
    truncated: bool


class AdminCortexRawIngestionResourceStat(BaseModel):
    """Aggregated raw row counts from ``raw_ingestion_records`` (observed tenant reality)."""

    model_config = ConfigDict(extra="forbid")

    connector: str
    resource_type: str
    row_count: int
    oldest_fetched_at: datetime | None = None
    newest_fetched_at: datetime | None = None


class AdminCortexConnectorRawRollup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector: str
    row_count: int
    oldest_fetched_at: datetime | None = None
    newest_fetched_at: datetime | None = None
    resource_types: list[dict[str, Any]] = Field(default_factory=list)


class AdminCortexRawIngestionStatsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: uuid.UUID
    resources: list[AdminCortexRawIngestionResourceStat]
    connector_rollups: list[AdminCortexConnectorRawRollup] = Field(default_factory=list)


ExhaustCoverageMaturity = Literal["none", "partial", "full"]
ExhaustHistoricalMaturity = Literal["none", "partial", "full", "n/a"]
ExhaustReplayMaturity = Literal["no", "partial", "yes"]
ExhaustCanonMaturity = Literal["none", "partial", "full"]
ExhaustRowStatus = Literal["missing", "in_progress", "active"]


class AdminCortexExhaustResourceCoverageRow(BaseModel):
    """One resource-type row from :mod:`vector.domains.cortex.ingestion.exhaust_coverage_registry`."""

    model_config = ConfigDict(extra="forbid")

    resource_type: str
    coverage: ExhaustCoverageMaturity
    historical: ExhaustHistoricalMaturity
    replay: ExhaustReplayMaturity
    canonicalization: ExhaustCanonMaturity
    status: ExhaustRowStatus
    notes: str | None = None


class AdminCortexExhaustConnectorCoverage(BaseModel):
    """Per-connector exhaust depth for admin visibility (mirrors the exhaust matrix doc)."""

    model_config = ConfigDict(extra="forbid")

    connector: CortexIngestionConnectorId
    maturity_level: int = Field(ge=0, le=6)
    maturity_level_title: str
    historical_backfill_summary: str
    replay_compatibility_summary: str
    canonicalization_summary: str
    missing_resource_types: list[str]
    resources: list[AdminCortexExhaustResourceCoverageRow]


class AdminCortexIngestionExhaustCoverageResponse(BaseModel):
    """Organizational exhaust coverage — static registry aligned with Cortex docs."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: uuid.UUID
    connector_exhaust_matrix_doc: str
    ingestion_depth_model_doc: str
    organizational_exhaust_definition_doc: str
    real_ingestion_definition_doc: str
    connector_expansion_roadmap_doc: str
    connectors: list[AdminCortexExhaustConnectorCoverage]

