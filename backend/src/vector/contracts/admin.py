"""Admin (internal) API payloads."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class AdminConnectionPermissionReport(BaseModel):
    """Requested vs granted OAuth / app permissions for operator diagnostics."""

    model_config = ConfigDict(from_attributes=False)

    permission_model: Literal[
        "oauth_scopes",
        "github_app",
        "notion_integration",
        "oauth_scope_single",
        "google_oauth",
    ]
    requested: list[str]
    granted: list[str] | None = None
    recommended_for_ingestion: list[str] | None = None
    missing_requested: list[str] = Field(default_factory=list)
    missing_recommended: list[str] = Field(default_factory=list)
    extra_granted: list[str] = Field(default_factory=list)
    ingest_health: Literal["ok", "warn", "unknown", "not_connected"] = "unknown"
    notes: str | None = None


class TenantConnectionAdminItem(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: uuid.UUID
    provider: str
    status: str
    created_at: datetime
    permissions: AdminConnectionPermissionReport | None = None


class AdminConnectionsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    items: list[TenantConnectionAdminItem]
    permissions_by_provider: dict[str, AdminConnectionPermissionReport] = Field(
        default_factory=dict,
        description=(
            "Permission diagnostics for each supported connector id, "
            "including providers not yet connected (ingest_health=not_connected)."
        ),
    )


class AdminConnectorConnectLinkResponse(BaseModel):
    """Admin-generated URL to run a tenant-scoped OAuth connect flow."""

    model_config = ConfigDict(from_attributes=False)

    provider: Literal["slack", "github", "linear", "notion", "calls"]
    connect_url: str
    tenant_id: uuid.UUID
    user_id: uuid.UUID


class AdminSlackChannelIngestItem(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    channel_id: str
    name: str
    is_private: bool = False
    is_member: bool = False
    selected_for_ingest: bool = False
    can_bot_join: bool = True


class AdminSlackChannelsIngestListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    connected: bool
    team_id: str | None = None
    team_name: str | None = None
    saved_channel_ids: list[str] = Field(default_factory=list)
    channels: list[AdminSlackChannelIngestItem] = Field(default_factory=list)
    catalog_stale: bool = False
    catalog_fetched_at: str | None = None


class AdminSlackChannelsIngestApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel_ids: list[str] = Field(
        default_factory=list,
        description="Slack channel IDs to watch for ingest; bot joins public channels on apply.",
    )


class AdminSlackChannelJoinResult(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    channel_id: str
    joined: bool
    error: str | None = None
    already_member: bool | None = None


class AdminSlackChannelsIngestApplyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    saved_channels: list[dict[str, str]] = Field(default_factory=list)
    join_results: list[AdminSlackChannelJoinResult] = Field(default_factory=list)
    joined_count: int = 0
    failed_count: int = 0
    message: str = ""


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


class AdminCortexCheckpointStreamSummary(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    stream_key: str
    cursor_owner: str | None = None
    next_cursor: str | None = None
    backfill_complete: bool = False
    introduced_at: str | None = None
    last_ok_at: str | None = None
    pages_fetched_last_run: int | None = None
    rows_seen_last_run: int | None = None
    connector_exhaust_depth: str | None = None


class AdminCortexConnectorRawResourceStat(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    resource_type: str
    row_count: int
    oldest_fetched_at: datetime | None = None
    newest_fetched_at: datetime | None = None


class AdminCortexConnectorIngestionRow(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    connector: str
    connection_id: uuid.UUID | None = None
    connection_status: str | None = None
    cortex_routed: bool
    queue_lane_live: str = Field(default="cortex_live")
    queue_lane_replay: str = Field(default="cortex_replay")
    checkpoint_last_incremental_at: str | None = None
    checkpoint_exhaust_depth: str | None = None
    checkpoint_streams: list[AdminCortexCheckpointStreamSummary] = Field(default_factory=list)
    raw_resource_stats: list[AdminCortexConnectorRawResourceStat] = Field(default_factory=list)
    ingested_row_count: int = 0
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

    status: Literal["ok", "warn", "unavailable", "deferred"]
    ratio_percent: float | None = None
    live_rows_examined: int
    duplicate_groups: int
    duplicate_rows_excess: int
    detail: str | None = None


class AdminCortexSlackUserEmailPresence(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    sampled_rows: int = 0
    with_email: int = 0
    email_presence_pct: float | None = None
    capped_sample: bool = False


class AdminCortexIngestionDigest(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    objective: str
    bottleneck_hint: str
    confidence_note: str
    recommended_actions: list[str]
    slack_user_email_presence: AdminCortexSlackUserEmailPresence | None = None


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


class AdminCortexIngestionResetStreamRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connector: CortexIngestionConnectorId
    connection_id: uuid.UUID | None = None
    stream_key: str = Field(..., min_length=1, max_length=128)
    confirmation: str = Field(
        ...,
        description="Must exactly match the server phrase for stream checkpoint reset.",
    )


class AdminCortexIngestionResetStreamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    tenant_id: uuid.UUID
    connector: str
    connection_id: uuid.UUID
    stream_key: str
    reset_applied: bool


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
    enforcement: dict[str, Any] | None = None


class AdminCortexFlushAndRerunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation: str = Field(
        ...,
        description="Must exactly match the server phrase for flush + rerun through Phase 07 (see admin UI).",
    )
    canonical_batch_limit: int = Field(
        default=500,
        ge=1,
        le=5000,
        description=(
            "Batch size for canonical backlog drain inside the flush+rerun orchestrator "
            "(before identity refresh, graph export, TCRE reconstruction, and retrieval index bootstrap)."
        ),
    )


class AdminCortexFlushAndRerunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    accepted: bool = True
    tenant_id: uuid.UUID
    enqueued_connectors: list[str]
    canonical_backlog_task_id: str | None = Field(
        default=None,
        description=(
            "Celery id for the orchestrator task (ingestion syncs + canonical drain + identity substrate + "
            "graph export, TCRE reconstruction, and retrieval index bootstrap)."
        ),
    )
    canonical_batch_limit: int
    deleted_rows_total: int
    deleted_rows_by_table: dict[str, int]


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
    raw_memory_contracts: dict[str, Any] | None = None
    raw_memory_persistence: dict[str, Any] | None = None
    raw_memory_temporal: dict[str, Any] | None = None
    raw_memory_replay: dict[str, Any] | None = None
    raw_memory_replay_hardening: dict[str, Any] | None = None
    raw_memory_query: dict[str, Any] | None = None
    raw_memory_storage: dict[str, Any] | None = None
    raw_memory_failure_recovery: dict[str, Any] | None = None
    raw_memory_trust: dict[str, Any] | None = None
    raw_memory_trust_signal: dict[str, Any] | None = None
    raw_memory_critical_integrity: dict[str, Any] | None = None
    raw_memory_operational_trust_proof: dict[str, Any] | None = None
    raw_memory_control_plane: dict[str, Any] | None = None
    raw_memory_phase_closure: dict[str, Any] | None = None
    raw_memory_enforcement: dict[str, Any] | None = None
    enforcement_mode: str | None = None
    phase02_verification_truth: dict[str, Any] | None = None
    raw_memory_verification_step12: dict[str, Any] | None = None


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
    total_count: int
    offset: int
    limit: int


class AdminCortexIngestionSchedulerBeatResourceStat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    resource_type: str
    count: int


class AdminCortexIngestionSchedulerBeatConnectorDebrief(BaseModel):
    """Per-connector outcome for one ingestion-only Beat tick."""

    model_config = ConfigDict(extra="forbid")

    connector: str
    enqueued: bool
    run_id: uuid.UUID | None = None
    status: str
    records_written: int | None = None
    resource_breakdown: list[AdminCortexIngestionSchedulerBeatResourceStat]
    error_summary: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class AdminCortexIngestionSchedulerBeatItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tick_id: uuid.UUID
    started_at: datetime
    completed_at: datetime | None = None
    outcome: str
    beat_interval_seconds: int
    skip_reason: str | None = None
    global_enqueued_count: int
    global_candidate_count: int
    tenant_enqueued_count: int
    connectors: list[AdminCortexIngestionSchedulerBeatConnectorDebrief]


class AdminCortexIngestionSchedulerBeatsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: uuid.UUID
    items: list[AdminCortexIngestionSchedulerBeatItem]
    limit: int


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


RawMemoryQueryMode = Literal["source", "replay", "audit", "provenance", "temporal"]
RawMemoryTemporalSubmode = Literal["as_of_t", "latest_before_t", "revision_chain"]
RawMemoryQueryIntent = Literal[
    "evidence_retrieval",
    "lineage_retrieval",
    "temporal_retrieval",
    "replay_diagnostics",
    "audit_retrieval",
]


class AdminCortexRawMemoryQueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: RawMemoryQueryMode
    intent: RawMemoryQueryIntent = "evidence_retrieval"
    query_text: str | None = None
    connector: str | None = None
    resource_type: str | None = None
    source_identity_key: str | None = None
    source_revision_key: str | None = None
    replay_job_id: uuid.UUID | None = None
    run_id: uuid.UUID | None = None
    provenance_chain_id: str | None = None
    fetched_after: datetime | None = None
    fetched_before: datetime | None = None
    temporal_submode: RawMemoryTemporalSubmode = "revision_chain"
    as_of: datetime | None = None
    limit: int = Field(default=100, ge=1, le=200)
    offset: int = Field(default=0, ge=0, le=50_000)


class AdminCortexRawMemoryQueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: uuid.UUID
    mode: RawMemoryQueryMode
    items: list[AdminCortexConnectorRawRecordItem]
    total_count: int
    offset: int
    limit: int
    truncated: bool
    enforcement: dict[str, Any] | None = None


class AdminCortexRawMemoryRetentionApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dry_run: bool = True
    archive_after_days: int = Field(default=30, ge=1, le=3650)
    delete_after_days: int = Field(default=365, ge=1, le=36500)
    allow_delete: bool = False
    confirmation: str | None = None


class AdminCortexRawMemoryRetentionApplyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: uuid.UUID
    dry_run: bool
    archive_after_days: int
    delete_after_days: int
    archive_candidate_count: int
    delete_candidate_count: int
    archive_candidate_ids: list[int]
    delete_candidate_ids: list[int]
    deletes_executed: bool


class AdminCortexRawMemoryRecoveryValidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    apply_repairs: bool = True


class AdminCortexRawMemoryRecoveryValidateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: uuid.UUID
    status: str
    apply_repairs: bool
    active_failures: int
    unresolved_recoverable: int
    detail: dict[str, Any]


class AdminCortexRawMemoryFailuresResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: uuid.UUID
    active_failure_count: int
    active_failure_classes: dict[str, int]
    sync: dict[str, Any]


class AdminCortexRawMemoryTrustStateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: uuid.UUID
    trust_state: str
    severity: str
    state_reason_codes: list[str]
    replay: dict[str, Any]
    reconstruction: dict[str, Any]
    provenance: dict[str, Any]
    blocking: dict[str, bool]
    continuity_gaps: list[dict[str, Any]]
    verification: dict[str, Any]


class AdminCortexRawMemoryControlPlaneResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    health_overview: dict[str, Any]
    inspectors: dict[str, Any]
    verification_checklist: dict[str, Any]
    phase_closure: dict[str, Any] | None = None
    verification_truth: dict[str, Any] | None = None
    enforcement: dict[str, Any] | None = None
    actions: list[dict[str, Any]]
    warnings: dict[str, Any]


class AdminCortexReasoningControlPlaneSurfaceItem(BaseModel):
    """One mandatory operator surface from ``reasoning-admin-control-plane-spec.md`` §1."""

    model_config = ConfigDict(extra="forbid")

    surface_id: str
    title: str
    operator_purpose: str


class AdminCortexReasoningControlPlaneResponse(BaseModel):
    """Phase 06 Step 32 — **reasoning_control_plane_catalog_v1** (substrate surface catalog)."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    reasoning_control_plane_runtime_schema_version: int
    reasoning_control_plane_surface_version: int
    reasoning_control_plane_contract: str
    surfaces: list[AdminCortexReasoningControlPlaneSurfaceItem]
    doctrine_anchors: list[str]
    dangerous_action_doctrine_ref: str
    rbac_substrate_alignment_literal: str


class AdminCortexReasoningRuntimeLegalityPredicateItem(BaseModel):
    """One **R‑LEG‑** production gate row (``reasoning-runtime-legality-matrix.md``)."""

    model_config = ConfigDict(extra="forbid")

    predicate_id: str
    required_evidence: str


class AdminCortexReasoningRuntimeLegalityForbiddenItem(BaseModel):
    """Normative forbidden deployment bullet (reasoning matrix §Forbidden deployments)."""

    model_config = ConfigDict(extra="forbid")

    forbidden_id: str
    description: str


class AdminCortexReasoningRuntimeLegalityMatrixResponse(BaseModel):
    """Phase 06 Step 33 — **reasoning_runtime_legality_matrix_catalog_v1** (read-only v1)."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    reasoning_runtime_legality_matrix_runtime_schema_version: int
    reasoning_runtime_legality_matrix_surface_version: int
    reasoning_runtime_legality_matrix_contract: str
    predicates: list[AdminCortexReasoningRuntimeLegalityPredicateItem]
    forbidden_deployments: list[AdminCortexReasoningRuntimeLegalityForbiddenItem]
    doctrine_anchors: list[str]
    waiver_yaml_future_path: str


class AdminCortexReasoningTenantVerificationSliceResponse(BaseModel):
    """Phase 06 Step 34 — **org_graph_reasoning** tenant verification aggregate (integer-only)."""

    model_config = ConfigDict(extra="forbid")

    golden_corpus_case_count: int
    last_reasoning_gate_bundle_sha256: str
    org_graph_reasoning_slice_schema_version: int
    phase06_program_freeze_version: int
    reasoning_gp06_gate_bundle_queue_depth_proxy: int
    tenant_id: str
    verification_run_id: str | None = None


class AdminCortexReasoningEconomicsStatsV1(BaseModel):
    """Integer stats embedded in **reasoning_readiness_economics** receipt hash."""

    model_config = ConfigDict(extra="forbid")

    golden_corpus_case_count: int
    reasoning_economics_threshold_max_cases: int
    reasoning_economics_threshold_table_version: int
    reasoning_eco_violation_count: int


class AdminCortexReasoningReadinessEconomicsResponse(BaseModel):
    """Phase 06 Step 34 — readiness / economics receipt (golden-thread manifest; read-only)."""

    model_config = ConfigDict(extra="forbid")

    economics_receipt_hash: str
    economics_stats: AdminCortexReasoningEconomicsStatsV1
    economics_violations: list[str]
    probe_profile: str
    reasoning_readiness_economics_contract: str
    reasoning_readiness_economics_schema_version: int
    tenant_id: str


class AdminCortexReasoningCertificationPackSnapshotResponse(BaseModel):
    """Phase 06 Step 35 — TCRE certification pack snapshot (gzip + digests; read-only)."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    reasoning_certification_pack_runtime_schema_version: int
    tcre_cert_pack_format: str
    closure_passed: bool
    closure_detail: dict[str, Any]
    whole_file_sha256: str | None = None
    pack_gzip_base64: str | None = None
    pack_byte_length: int | None = None


class AdminCortexRetrievalCertificationPackSnapshotResponse(BaseModel):
    """Phase 07 Step 28 — RETRIEVAL-CERT-PACK-1 snapshot (gzip + digests; read-only)."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    retrieval_certification_pack_runtime_schema_version: int
    retrieval_cert_pack_format: str
    closure_passed: bool
    closure_detail: dict[str, Any]
    whole_file_sha256: str | None = None
    pack_gzip_base64: str | None = None
    pack_byte_length: int | None = None


class AdminCortexRetrievalProgramClosureCompletionCriterionRow(BaseModel):
    """One Phase 07 program completion criterion (C01–C10)."""

    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    label: str
    passed: bool
    errors: list[str]
    detail: dict[str, Any] = Field(default_factory=dict)


class AdminCortexRetrievalProgramClosureOperatorChecklistRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_id: str
    label: str
    detail: str
    passed: bool


class AdminCortexRetrievalProgramClosureResponse(BaseModel):
    """Phase 07 Step 30 — program closure + FF-P07-5 operator snapshot."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    retrieval_program_closure_runtime_schema_version: int
    retrieval_program_freeze_version: int
    freeze_bundle_id: str
    spec_ref: str
    program_closure_passed: bool
    completion_criteria: list[AdminCortexRetrievalProgramClosureCompletionCriterionRow]
    operator_checklist: list[AdminCortexRetrievalProgramClosureOperatorChecklistRow]
    control_plane_surfaces_wired: int
    control_plane_surfaces_total: int
    certification_pack: dict[str, Any]
    normative_program: dict[str, Any]
    rd_topology_check: dict[str, Any] | None = None


class AdminCortexSynthesisFreezeBannerV1(BaseModel):
    """Phase 08 Step 35 — program freeze banner (operator UI)."""

    model_config = ConfigDict(extra="forbid")

    status: str
    bundle_id: str
    headline: str
    detail: str


class AdminCortexSynthesisProgramCatalogResponse(BaseModel):
    """Phase 08 Step 01 — synthesis program freeze doctrine catalog (global, not tenant-scoped)."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    synthesis_program_catalog_runtime_schema_version: int
    spec_ref: str
    phase08_program_freeze_version: int
    step_program_count: int
    freeze_bundle_ids: list[str]
    normative_program: dict[str, Any]
    replay_law: dict[str, Any]
    degradation_registry: dict[str, Any]
    constitutional_freeze_bundle: str
    doctrine_freeze_status: str
    freeze_banner: AdminCortexSynthesisFreezeBannerV1


class AdminCortexOperationalRuntimeProgramCatalogResponse(BaseModel):
    """Phase 08.5 Step 01 — CESP program freeze doctrine catalog (global, not tenant-scoped)."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    operational_runtime_program_catalog_runtime_schema_version: int
    spec_ref: str
    program_id: str
    phase085_program_freeze_version: int
    step_program_count: int
    freeze_bundle_ids: list[str]
    normative_program: dict[str, Any]
    continuity_law: dict[str, Any]
    density_law: dict[str, Any]
    endgoal_law: dict[str, Any]
    phase_boundary_law: dict[str, Any]
    gap_matrix_law: dict[str, Any]
    vocabulary_law: dict[str, Any]
    phase09_readiness: dict[str, Any]
    executive_brief_ref: str
    gap_matrix_ref: str
    runtime_architecture_ref: str
    hard_upstream_gate: str
    gate_ids: list[str]


class AdminCortexOperationalRuntimePhaseBoundariesRuleRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str


class AdminCortexOperationalRuntimeVocabularyTermRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    term_id: str
    label: str
    definition: str


class AdminCortexOperationalRuntimeVocabularyCatalogResponse(BaseModel):
    """Phase 08.5 Step 04 — CESP closed vocabulary catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    phase085_vocabulary_runtime_schema_version: int
    spec_ref: str
    term_ids: list[str]
    terms: list[AdminCortexOperationalRuntimeVocabularyTermRow]
    term_count: int


class AdminCortexOperationalRuntimeGapMatrixCatalogResponse(BaseModel):
    """Phase 08.5 Step 04 — CESP spec gap matrix catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    phase085_gap_matrix_runtime_schema_version: int
    spec_ref: str
    gap_matrix_fixture_digest_sha256: str
    baseline_gap_ids: list[str]
    parsed_gap_ids: list[str]
    promotion_rules: list[str]
    summary: dict[str, Any]
    active_p0: list[dict[str, Any]]
    active_p1: list[dict[str, Any]]
    partially_shipped: list[dict[str, Any]]
    blocks_step_36_freeze: bool
    blocks_slice_frozen_runtime: bool


class AdminCortexOperationalRuntimePhaseBoundariesCatalogResponse(BaseModel):
    """Phase 08.5 Step 03 — CESP phase boundary doctrine catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    phase085_boundaries_runtime_schema_version: int
    spec_ref: str
    runtime_package: str
    rule_ids: list[str]
    acyclic_pipeline: list[str]
    hard_downstream_gate: str
    synthesis_artifact_schema_rel_path: str
    synthesis_artifact_schema_digest_sha256: str
    cesp_allowed_extension_importers: list[str]
    forbidden_forward_import_prefixes: list[str]
    cesp_owned_runtime_artifacts: list[str]
    admin_route_prefixes: list[str]
    rules: list[AdminCortexOperationalRuntimePhaseBoundariesRuleRow]
    phase085_owns: list[str]
    phase085_does_not_own: list[str]


class AdminCortexSynthesisAntiGoalsCatalogResponse(BaseModel):
    """Phase 08 Step 02 — synthesis anti-goals / forbidden keys doctrine catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    synthesis_anti_goals_catalog_runtime_schema_version: int
    spec_ref: str
    synthesis_forbidden_legality_class: str
    gate_ids: list[str]
    job_envelope_forbidden_keys: list[str]
    artifact_forbidden_top_level_keys: list[str]
    banned_import_roots: list[str]
    forbidden_law_import_modules: list[str]
    authoritative_job_envelope_top_level_keys: list[str]
    authoritative_artifact_top_level_keys: list[str]
    synthesis_prompt_overrides_rule: str


class AdminCortexSynthesisPhaseBoundariesRuleRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str


class AdminCortexSynthesisPhaseBoundariesCatalogResponse(BaseModel):
    """Phase 08 Step 03 — synthesis phase boundary doctrine catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    phase08_boundaries_runtime_schema_version: int
    rule_ids: list[str]
    acyclic_pipeline: list[str]
    upstream_replay_identity_field: str
    synthesis_replay_identity_field: str
    rd_to_sd_map: dict[str, str]
    sd_upstream_rd: str
    forbidden_retrieval_bypass_keys: list[str]
    phase09_forbidden_field_keys: list[str]
    rules: list[AdminCortexSynthesisPhaseBoundariesRuleRow]
    phase08_owns: list[str]
    phase08_does_not_own: list[str]


class AdminCortexSynthesisIngressLawRuleRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str


class AdminCortexSynthesisIngressLawCatalogResponse(BaseModel):
    """Phase 08 Step 04 — synthesis retrieval ingress law catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    phase08_ingress_runtime_schema_version: int
    retrieval_evidence_ingress_schema_version: int
    spec_ref: str
    gate_ids: list[str]
    gp08_ingress_gate_id: str
    authoritative_retrieval_legality_classes: list[str]
    exploration_retrieval_legality_classes: list[str]
    retrieval_legality_copy_fields: list[str]
    ingress_reject_metrics: list[str]
    sd_upstream_legality_code: str
    rules: list[AdminCortexSynthesisIngressLawRuleRow]


class AdminCortexSynthesisIngressInspectorResponse(BaseModel):
    """Phase 08 Step 04 — ingress inspector preview for a retrieval response."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    ingress_passed: bool
    gate_id: str
    gate_results: list[dict[str, Any]]
    violations: list[str]
    retrieval_evidence_ingress: dict[str, Any] | None = None
    inspector_fields: dict[str, Any]


class AdminCortexSynthesisWorkloadClassRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    synthesis_workload_class: str
    purpose: str
    retrieval_plan_profile: str
    primary_artifact_kind: str
    allowed_intents: list[str]
    default_selection_policy: dict[str, int]


class AdminCortexSynthesisIntentClassRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    synthesis_intent: str
    meaning: str
    llm_allowed: str


class AdminCortexSynthesisJobContractCatalogResponse(BaseModel):
    """Phase 08 Step 05 — synthesis workload + intent taxonomy catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    phase08_synthesis_job_contract_runtime_schema_version: int
    envelope_schema_version: int
    default_synthesis_policy_pack_id: str
    gp08_schema_gate_id: str
    synthesis_workload_classes: list[AdminCortexSynthesisWorkloadClassRow]
    synthesis_intent_classes: list[AdminCortexSynthesisIntentClassRow]
    replay_identity_fields: dict[str, str]
    jobs_by_workload_metric: str


class AdminCortexSynthesisJobRunResponse(BaseModel):
    """Phase 08 Step 06 — synthesis job FSM run result with execution trace."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    phase08_synthesis_orchestrator_runtime_schema_version: int
    job_id: str
    tenant_id: str
    status: str
    synthesis_workload_class: str
    synthesis_intent: str
    execution_partition: str
    synthesis_legality_class: str
    synthesis_legality_posture: dict[str, Any] = {}
    synthesis_job_replay_identity: str
    retrieval_ingress_digest: str | None = None
    synthesis_orchestrator_build_id: str
    execution_trace: list[dict[str, Any]]
    synthesis_job_receipt: dict[str, Any]
    claims: list[dict[str, Any]] = []
    synthesis_citation_envelope: dict[str, Any] = {}
    retrieval_subqueries: list[dict[str, Any]] = []
    llm_invocations: list[dict[str, Any]] = []
    llm_trace_refs: list[dict[str, Any]] = []
    prompt_assemblies: list[dict[str, Any]] = []
    prompt_hashes: list[str] = []
    idempotent_replay: bool = False
    execution_phases: list[str]
    celery_task_id: str | None = None
    artifact_id: str | None = None
    artifact_digest: str | None = None
    synthesis_intelligence_artifact: dict[str, Any] | None = None
    replay_equivalence_twin: dict[str, Any] = {}
    gp08_replay_proof_passed: bool | None = None
    synthesis_job_log: dict[str, Any] | None = None
    synthesis_observability_metrics: dict[str, Any] | None = None


class AdminCortexSynthesisArtifactExplorerResponse(BaseModel):
    """Phase 08 Step 14 — synthesis artifact explorer catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    catalog_id: str
    phase08_synthesis_artifact_materialization_runtime_schema_version: int
    gate_id: str
    spec_ref: str
    artifact_schema_path: str
    artifact_kinds: list[str]
    publish_barrier_legality_classes: list[str]
    publication_epoch_deferred_step: int
    recent_artifacts: list[dict[str, Any]] = []
    rules: list[dict[str, Any]]


class AdminCortexSynthesisArtifactDetailResponse(BaseModel):
    """Phase 08 Step 14 — persisted synthesis intelligence artifact."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    phase08_synthesis_artifact_materialization_runtime_schema_version: int
    artifact_id: str
    tenant_id: str
    job_id: str
    artifact_kind: str
    artifact_digest: str
    synthesis_legality_class: str
    published: bool
    synthesis_publication_epoch: str | None = None
    created_at: str | None = None
    synthesis_intelligence_artifact: dict[str, Any]
    claim_count: int = 0
    citation_count: int = 0
    binding_panel: dict[str, Any] = {}
    lineage_panel: dict[str, Any] = {}


class AdminCortexSynthesisArtifactListResponse(BaseModel):
    """Phase 08 Step 20 — tenant artifact list with lookup / epoch filters."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    phase08_synthesis_artifact_query_runtime_schema_version: int
    tenant_id: str
    filters_applied: dict[str, Any]
    artifact_count: int
    artifacts: list[dict[str, Any]]


class AdminCortexSynthesisArtifactQueryCatalogResponse(BaseModel):
    """Phase 08 Step 20 — artifact query law catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    catalog_id: str
    phase08_synthesis_artifact_query_runtime_schema_version: int
    gate_id: str
    spec_ref: str
    artifact_materialization_schema_version: int
    supported_filters: list[str]
    index_columns: list[str]
    rules: list[str]


class AdminCortexSynthesisObservabilityCatalogResponse(BaseModel):
    """Phase 08 Step 21 — synthesis observability law catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    catalog_id: str
    synthesis_observability_runtime_schema_version: int
    gate_id: str
    spec_ref: str
    rules: list[dict[str, Any]]
    metric_names: list[str]
    default_thresholds: dict[str, int]
    engine_build_ref: str


class AdminCortexSynthesisRuntimeHealthResponse(BaseModel):
    """Phase 08 Step 21 — tenant synthesis runtime health."""

    model_config = ConfigDict(extra="allow")

    schema_version: int
    tenant_id: str
    substrate_state: str | None = None
    substrate_health_state: str | None = None
    replay_posture: str | None = None
    publication_epoch: str | None = None
    synthesis_completeness_percent: int = 0
    sd_critical_count: int = 0
    publication_lag_epochs: int = 0
    active_alerts: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    s_leg_health: dict[str, Any] = {}


class AdminCortexSynthesisBindingsCatalogResponse(BaseModel):
    """Phase 08 Step 15 — synthesis binding copy law catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    catalog_id: str
    phase08_synthesis_bindings_runtime_schema_version: int
    gate_id: str
    spec_ref: str
    rules: list[dict[str, Any]]
    artifact_binding_fields: list[str]
    sd_upstream_binding_gap: str


class AdminCortexSynthesisLineageCatalogResponse(BaseModel):
    """Phase 08 Step 16 — synthesis artifact lineage law catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    catalog_id: str
    phase08_synthesis_lineage_runtime_schema_version: int
    gate_id: str
    spec_ref: str
    terminal_artifact_kind: str
    edge_kinds: list[str]
    sd_lineage_gap: str
    upstream_rd_lineage_gap: str
    rules: list[dict[str, Any]]


class AdminCortexSynthesisLegalityPredicateRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    predicate_id: str
    description: str
    failure_class: str


class AdminCortexSynthesisLegalityMatrixCatalogResponse(BaseModel):
    """Phase 08 Step 07 — synthesis legality matrix catalog + tenant histogram."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    tenant_id: str
    phase08_synthesis_legality_matrix_runtime_schema_version: int
    synthesis_legality_matrix_contract: str
    synthesis_policy_pack_digest: str
    gp08_legality_gate_id: str
    legality_classes: list[dict[str, Any]]
    predicates: list[AdminCortexSynthesisLegalityPredicateRow]
    s_leg_failure_class_map: dict[str, str]
    retrieval_to_synthesis_upstream_floor: dict[str, str]
    spec_ref: str
    synthesis_jobs_by_legality: dict[str, int] = {}


class AdminCortexSynthesisJobDetailResponse(BaseModel):
    """Phase 08 Step 06 — persisted synthesis job detail."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    job_id: str
    tenant_id: str
    status: str
    synthesis_workload_class: str
    synthesis_intent: str
    execution_partition: str
    envelope_json: dict[str, Any]
    envelope_digest: str
    retrieval_ingress_digest: str | None = None
    synthesis_job_replay_identity: str | None = None
    synthesis_legality_class: str | None = None
    receipt_digest: str | None = None
    execution_trace: list[dict[str, Any]]
    synthesis_job_receipt: dict[str, Any]
    error_detail: str | None = None
    celery_task_id: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    retrieval_subqueries: list[dict[str, Any]] = []


class AdminCortexSynthesisRetrievalPlanCatalogResponse(BaseModel):
    """Phase 08 Step 10 — synthesis PLAN+RETRIEVE catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    catalog_id: str
    phase08_synthesis_query_plan_runtime_schema_version: int
    gate_id: str
    spec_ref: str
    synthesis_to_primary_retrieval_workload: dict[str, str]
    retrieval_fanout_rules: list[dict[str, Any]]
    max_retrieval_subqueries_default: int
    sd_cap_retrieval: str


class AdminCortexSynthesisRetrievalPlanPreviewResponse(BaseModel):
    """Phase 08 Step 10 — retrieval plan preview for a job envelope."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    gate_id: str
    retrieval_plan_count: int
    retrieval_plan: list[dict[str, Any]]
    retrieval_query_envelopes: list[dict[str, Any]]
    cap_violations: list[dict[str, Any]] = []


class AdminCortexSynthesisLlmModelRouteCatalogResponse(BaseModel):
    """Phase 08 Step 11 — LLM model route registry catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    catalog_id: str
    phase08_synthesis_llm_router_runtime_schema_version: int
    gate_id: str
    spec_ref: str
    model_routes: list[dict[str, Any]]
    max_llm_tokens_default: int
    sd_llm_codes: list[str]
    adapter_id: str
    response_format_required: str


class AdminCortexSynthesisLlmRoutePreviewResponse(BaseModel):
    """Phase 08 Step 11 — LLM route preview for a synthesis job envelope."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    gate_id: str
    llm_would_skip: bool
    llm_skip_reason: str
    selected_model_route_ids: list[str]
    route_previews: list[dict[str, Any]]


class AdminCortexSynthesisPromptTemplateCatalogResponse(BaseModel):
    """Phase 08 Step 12 — synthesis prompt template registry catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    catalog_id: str
    phase08_synthesis_prompt_assembly_runtime_schema_version: int
    gate_id: str
    spec_ref: str
    syn_prm_rules: list[str]
    prompt_templates: list[dict[str, Any]]
    model_route_template_bindings: list[dict[str, Any]]


class AdminCortexSynthesisDegradationTopologyResponse(BaseModel):
    """Phase 08 Step 18 — synthesis degradation topology (RD→SD propagation)."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    tenant_id: str
    phase08_synthesis_degradation_runtime_schema_version: int
    gate_ids: list[str]
    synthesis_policy_pack_id: str | None = None
    synthesis_policy_pack_digest: str
    sd_codes_registry: list[str]
    rd_to_sd_propagation_matrix: list[dict[str, str]]
    rd_to_sd_primary_map: dict[str, str]
    policy_pack_rd_to_sd: list[dict[str, Any]]
    substrate_health_states: list[str]
    degradation_postures: list[str]
    omission_histogram: dict[str, int]
    rules: list[dict[str, Any]]
    doctrine_anchors: list[str]


class AdminCortexSynthesisSdOmissionExplorerResponse(BaseModel):
    """Phase 08 Step 13 — SD-* omission explorer catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    catalog_id: str
    phase08_synthesis_bounded_caps_runtime_schema_version: int
    gate_id: str
    spec_ref: str
    synthesis_policy_pack_id: str | None = None
    default_caps: dict[str, int]
    sd_codes_registry: list[str]
    omission_semantics_by_sd: dict[str, str]
    substrate_health_states: list[str]
    degradation_postures: list[str]
    omission_histogram: dict[str, int]
    rd_to_sd_propagation: list[dict[str, Any]]
    rules: list[dict[str, Any]]
    http_behaviors: dict[str, int]


class AdminCortexSynthesisPromptAssemblyPreviewResponse(BaseModel):
    """Phase 08 Step 12 — prompt assembly preview for a synthesis job envelope."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    gate_id: str
    prompt_assembly_count: int
    prompt_assemblies: list[dict[str, Any]]
    prompt_hashes: list[str]


class AdminCortexSynthesisCitationLawCatalogResponse(BaseModel):
    """Phase 08 Step 09 — synthesis cite-or-omit + citation schema catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    catalog_id: str
    phase08_synthesis_evidence_binding_runtime_schema_version: int
    gate_id: str
    syn_law_rule: str
    synthesis_citation_schema_version: int
    claim_kinds: list[str]
    citation_required_fields: list[str]
    sd_codes: list[str]
    cite_or_omit_law: str
    spec_ref: str


class AdminCortexSynthesisCitationBindingInspectorResponse(BaseModel):
    """Phase 08 Step 09 — citation binding preview for hits + claim plan."""

    model_config = ConfigDict(extra="allow")

    surface_kind: str
    gate_id: str
    passed: bool
    binding: dict[str, Any]


class AdminCortexSynthesisReplayExplorerResponse(BaseModel):
    """Phase 08 Step 08/17 — synthesis replay explorer catalog."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    tenant_id: str
    phase08_synthesis_replay_equivalence_runtime_schema_version: int
    gate_ids: list[str]
    replay_identity_field: str
    upstream_replay_identity_field: str
    replay_pin_fields: list[str]
    syn_rep_rules: list[str]
    sd_replay_codes: list[str]
    canonical_identity_vector_fields: list[str]
    synthesis_replay_divergence_total: int
    doctrine_anchor: str
    twin_modes: list[str]
    recent_jobs: list[dict[str, Any]] = []
    phase08_synthesis_replay_equivalence_proofs_runtime_schema_version: int = 1
    sd_replay_twin: str = "SD-REPLAY-TWIN"
    doctrine_anchors: list[str] = []
    twin_diff_fields: list[str] = []
    harness: dict[str, Any] = {}
    operator_replay_prove_route: str = ""
    gp08_replay_02_gate_id: str = "G-P08-REPLAY-02"


class AdminCortexSynthesisOperatorReplayProveResponse(BaseModel):
    """Phase 08 Step 17 — operator replay prove (twin vs stored job)."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    tenant_id: str
    job_id: str
    gate_id: str
    gp08_replay_proof_passed: bool
    replay_equivalence_twin: dict[str, Any]
    stored_synthesis_job_replay_identity: str = ""
    replay_synthesis_job_replay_identity: str | None = None


class AdminCortexSynthesisJobReplayInspectorResponse(BaseModel):
    """Phase 08 Step 08 — per-job synthesis replay inspector."""

    model_config = ConfigDict(extra="forbid")

    surface_kind: str
    tenant_id: str
    job_id: str
    gate_id: str
    synthesis_job_replay_identity: str
    expected_synthesis_job_replay_identity: str | None = None
    receipt_digest: str | None = None
    retrieval_receipt_embed: dict[str, Any] | None = None
    retrieval_subqueries: list[dict[str, Any]] = []
    synthesis_job_replay_identity_vector: dict[str, Any] | None = None
    upstream_retrieval_query_replay_identity: str | None = None
    execution_trace: list[dict[str, Any]] = []
    replay_equivalence_twin: dict[str, Any] = {}
    gp08_replay_proof_passed: bool | None = None


class AdminCortexSynthesisCertificationPackSnapshotResponse(BaseModel):
    """Phase 08 Step 30 — SYNTHESIS-CERT-PACK-1 snapshot (gzip + digests; read-only)."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    synthesis_certification_pack_runtime_schema_version: int
    synthesis_cert_pack_format: str
    closure_passed: bool
    closure_detail: dict[str, Any]
    whole_file_sha256: str | None = None
    pack_gzip_base64: str | None = None
    pack_byte_length: int | None = None


class AdminCortexSynthesisProgramClosureCompletionCriterionRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    label: str
    passed: bool
    errors: list[str]
    detail: dict[str, Any] = Field(default_factory=dict)


class AdminCortexSynthesisProgramClosureOperatorChecklistRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_id: str
    label: str
    detail: str
    passed: bool


class AdminCortexSynthesisProgramClosureResponse(BaseModel):
    """Phase 08 Step 30 — program closure + FF-P08-5 operator snapshot."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    synthesis_program_closure_runtime_schema_version: int
    phase08_program_freeze_version: int
    freeze_bundle_id: str
    spec_ref: str
    program_closure_passed: bool
    completion_criteria: list[AdminCortexSynthesisProgramClosureCompletionCriterionRow]
    operator_checklist: list[AdminCortexSynthesisProgramClosureOperatorChecklistRow]
    control_plane_surfaces_wired: int
    control_plane_surfaces_total: int
    certification_pack: dict[str, Any]
    normative_program: dict[str, Any]
    phase09_handoff_check: dict[str, Any] | None = None


class AdminCortexSynthesisCertificationArchiveItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    tenant_id: str
    synthesis_certification_pack_schema_version: int
    passed: bool
    created_at: datetime


class AdminCortexSynthesisCertificationArchiveListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    archives: list[AdminCortexSynthesisCertificationArchiveItem]


class AdminCortexSynthesisCertificationArchiveDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    archive: AdminCortexSynthesisCertificationArchiveItem
    pack_json: dict[str, Any]


class AdminCortexReasoningRuntimeHealthResponse(BaseModel):
    """Phase 06 RUNTIME-01/02 — live reconstruction health strip."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    tcre_runtime_schema_version: int
    operator_projection_version: int = 1
    engine_build_ref: str
    active_tcre_policy_bundle_digest: str
    active_reasoning_rule_pack_id: str
    canonical_materialization_count: int
    job_status_counts: dict[str, int]
    queue_depth_proxy: int
    failed_job_count: int = 0
    last_successful_job: dict[str, Any] | None = None
    last_replay_twin_job: dict[str, Any] | None = None
    last_replay_result: bool | None = None
    last_replay_divergence_at: str | None = None
    last_successful_replay_twin_passed: bool | None = None
    degraded_chronology_percent: float = 0.0
    degraded_edge_percent: float = 0.0
    avg_reconstruction_duration_seconds: float | None = None
    replay_equivalence_status: str
    runtime_legality: dict[str, Any]


class AdminCortexReasoningReconstructionJobItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    tenant_id: str
    job_kind: str
    status: str
    dry_run: bool
    scope_json: dict[str, Any]
    summary_json: dict[str, Any]
    tcre_policy_bundle_digest: str
    reasoning_rule_pack_id: str
    parent_job_id: str | None = None
    engine_build_ref: str
    error_detail: str | None = None
    celery_task_id: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class AdminCortexReasoningReconstructionArtifactItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: int
    artifact_kind: str
    artifact_key: str
    artifact_digest: str
    body_json: dict[str, Any]
    created_at: str | None = None


class AdminCortexReasoningReconstructionJobDetailResponse(AdminCortexReasoningReconstructionJobItem):
    artifacts: list[AdminCortexReasoningReconstructionArtifactItem] = Field(default_factory=list)


class AdminCortexReasoningReconstructionEnqueueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    materialization_limit: int | None = None
    bundle_id: str | None = None
    octs_walk_id: str | None = None
    octs_strict_binding: bool = False
    dry_run: bool = False
    run_sync: bool = False


class AdminCortexReasoningReconstructionEnqueueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: str
    celery_task_id: str | None = None
    sync: bool | None = None


class AdminCortexReasoningReplayTwinResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    twin_job_id: str
    source_job_id: str
    replay_equivalence_passed: bool
    double_run_digest_a: str
    double_run_digest_b: str
    changed_fields: list[str]
    materialization_count: int
    equivalence_receipt: dict[str, Any]
    replay_diff: dict[str, Any] | None = None


class AdminCortexReasoningJobOperatorViewResponse(BaseModel):
    """Phase 06 RUNTIME-02 — human-debuggable reconstruction operator view."""

    model_config = ConfigDict(extra="forbid")

    operator_view_schema_version: int
    tcre_runtime_schema_version: int
    job_id: str
    tenant_id: str
    job_kind: str
    status: str
    octs_binding: dict[str, Any] | None = None
    reconstruction_summary: dict[str, Any]
    chronology_explanations: list[dict[str, Any]]
    edge_explanations: list[dict[str, Any]]
    chain_timeline: dict[str, Any]
    degradation_explanations: list[dict[str, Any]]
    replay_diff: dict[str, Any] | None = None
    retrieval_refs: dict[str, Any]


class AdminCortexReasoningReplayDiffResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    replay_equivalence_passed: bool
    double_run_digest_a: str
    double_run_digest_b: str
    changed_fields: list[str]
    materialization_count: int
    replay_diff: dict[str, Any]


class AdminSubstrateCompletenessLedgerResponse(BaseModel):
    """Substrate completeness pipeline — bounded visible incompleteness per tenant."""

    model_config = ConfigDict(extra="forbid")

    substrate_completeness_ledger_schema_version: int
    tenant_id: str
    substrate_state: str
    substrate_replay_posture: str
    pipeline_stages: list[dict[str, Any]]
    degradation_propagation: dict[str, Any]
    aggregate: dict[str, Any]
    ledger_digest: str


class AdminCortexCanonicalControlPlaneResponse(BaseModel):
    """Phase 03 Step 16 — tenant canonical operator control-plane aggregate."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    canonical_control_plane_schema_version: int
    health_overview: dict[str, Any]
    inspectors: dict[str, Any]
    verification_checklist: dict[str, Any]
    verification_truth: dict[str, Any] | None = None
    logical_information_architecture: dict[str, Any]
    actions: list[dict[str, Any]]
    warnings: dict[str, Any]


class AdminCortexCanonicalCoverageMatrixSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matrix_row_count: int
    routable_pair_count: int
    ingest_only_pair_count: int
    transform_only_or_unlisted_exhaust_count: int
    unsupported_ingest_raw_row_count: int = 0
    routable_unmaterialized_raw_row_count: int = 0
    orphan_dependency_ref_count: int = 0
    replay_dependency_cycle_detected: bool = False
    replay_dependency_edge_count: int = 0
    determinism_drift_events: int = 0
    dead_route_pair_count: int = 0
    dormant_route_pair_count: int = 0
    replay_active_pair_count: int = 0
    topology_active_pair_count: int = 0
    orphan_backlog_pressure: int = 0
    orphan_recovery_rate_proxy: float | None = None
    never_ingested_pair_count: int = 0
    never_materialized_pair_count: int = 0
    never_replayed_pair_count: int = 0
    historically_active_pair_count: int = 0
    stale_pair_count: int = 0
    inactive_by_design_pair_count: int = 0
    connector_disabled_pair_count: int = 0
    awaiting_ingestion_support_pair_count: int = 0


class AdminCortexCanonicalCoverageMatrixRow(BaseModel):
    """One row: ingest exhaust inventory merged with transform routing registry + tenant counts."""

    model_config = ConfigDict(extra="forbid")

    connector: str
    resource_type: str
    emitted: bool = False
    ingest_supported: bool
    exhaust_row_status: str
    routable: bool
    materializable: bool
    logical_keys: bool
    provenance: bool
    replay: bool
    oracle_coverage: str
    verification_coverage: str
    ambiguity_support: str
    dependency_safe: bool = False
    replay_safe: bool = False
    hierarchy_safe: bool = False
    invariant_verified: bool = False
    oracle_certified: bool = False
    orphan_free: bool = False
    replay_localizable: bool = False
    dormant: bool = False
    dormant_reason: str | None = None
    inactive_by_design: bool = False
    awaiting_ingestion_support: bool = False
    connector_disabled: bool = False
    never_ingested: bool = False
    never_materialized: bool = False
    never_replayed: bool = False
    historically_active: bool = False
    stale: bool = False
    dead_route: bool = False
    active: bool = False
    replay_active: bool = False
    topology_active: bool = False
    replayed: bool = False
    replay_converged: bool = False
    topology_safe: bool = False
    deterministic: bool = False
    drift_free: bool = False
    replay_count: int = 0
    replay_failure_count: int = 0
    deferred_dependency_count: int = 0
    topology_edge_count: int = 0
    topology_cycle_count: int = 0
    determinism_drift_events: int = 0
    first_seen_at: str | None = None
    last_materialized_at: str | None = None
    production_trusted: bool = False
    maturity_level: str
    transform_routing_rule_base: str | None = None
    canonical_object_kind: str | None = None
    oracle_fixture_id: str | None = None
    tenant_raw_row_count: int
    tenant_materialized_row_count: int
    tenant_materialization_pct_of_raw: float | None = None
    orphan_count: int = 0
    replay_dependency_failures: int = 0
    unresolved_parent_refs: int = 0
    deterministic_replay_drift: int = 0
    unsupported_execution_rows: int = 0
    notes: str | None = None


class AdminCortexCanonicalCoverageMatrixResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_coverage_matrix_schema_version: int
    transform_routing_registry_version: int
    tenant_id: str
    summary: AdminCortexCanonicalCoverageMatrixSummary
    rows: list[AdminCortexCanonicalCoverageMatrixRow]
    phase03_exit_audit: list[dict[str, Any]] = Field(default_factory=list)
    # Operator rollups from ``build_canonical_coverage_matrix`` (Health uses control-plane mirror).
    connector_rollups: list[dict[str, Any]] = Field(default_factory=list)
    totals: dict[str, Any] = Field(default_factory=dict)


class AdminCortexCanonicalKindInvariantItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind_id: str
    lifecycle_state: str
    identity_invariants: list[str]
    temporal_invariants: list[str]
    provenance_invariants: list[str]
    structural_invariants: list[str]
    ambiguity_invariants: list[str]
    anti_goals: list[str]


class AdminCortexCanonicalKindInvariantsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_kind_invariants_schema_version: int
    kinds: list[AdminCortexCanonicalKindInvariantItem]


class AdminCortexStabilizationProofRunRequest(BaseModel):
    """Phase 03 Step 17 — optional persistence of stabilization proof snapshot."""

    model_config = ConfigDict(extra="forbid")

    persist: bool = False


class AdminCortexStabilizationProofRunResponse(BaseModel):
    """Phase 03 Step 17 — stabilization / economics proof pass output."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    stabilization_proof_schema_version: int
    overall_passed: bool
    hard_fail_passed: bool
    warn_only_all_passed: bool
    proof_checklist: list[dict[str, Any]]
    substrate_scale: dict[str, Any]
    replay_economics: dict[str, Any]
    verification_continuity: dict[str, Any]
    ambiguity_pressure: dict[str, Any]
    mapping_governance: dict[str, Any]
    reconstruction_slice: dict[str, Any]
    doctrine_anchors: list[str]
    warnings: dict[str, Any]
    persisted_run_id: int | None = None


class AdminCortexStabilizationProofRunItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    tenant_id: str
    proof_schema_version: int
    passed: bool
    probes_json: dict[str, Any]
    created_at: datetime


class AdminCortexStabilizationProofRunsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stabilization_proof_schema_version: int
    tenant_id: str
    runs: list[AdminCortexStabilizationProofRunItem]


class AdminCortexCanonicalCertificationPackClosureGateRow(BaseModel):
    """Phase 03 Step 18 — one closure / operator-visibility gate row (G-P03-14–G-P03-21)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    passed: bool
    severity: str
    detail: dict[str, Any]


class AdminCortexCanonicalCertificationPackResponse(BaseModel):
    """Phase 03 Step 18 — deterministic certification evidence pack + closure matrix."""

    model_config = ConfigDict(extra="forbid")

    certification_pack_schema_version: int
    tenant_id: str
    built_at_clock: str
    verification_matrix_excerpt: dict[str, Any]
    stabilization_proof_excerpt: dict[str, Any]
    control_plane_excerpt: dict[str, Any]
    replay_jobs_excerpt: dict[str, Any]
    ambiguity_excerpt: dict[str, Any]
    mapping_registry_excerpt: dict[str, Any]
    lineage_operator_sample_excerpt: dict[str, Any]
    doctrine_notes: dict[str, Any]
    closure_gate_matrix: list[AdminCortexCanonicalCertificationPackClosureGateRow]
    certification_pack_contract: dict[str, Any]


class AdminCortexCanonicalCertificationArchiveResponse(BaseModel):
    """Result of attempting to persist a certification pack (requires full closure PASS)."""

    model_config = ConfigDict(extra="forbid")

    persisted: bool
    passed: bool
    archive_id: int | None
    certification_pack_schema_version: int
    tenant_id: str
    pack: dict[str, Any]


class AdminCortexCanonicalCertificationArchiveItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    tenant_id: str
    certification_pack_schema_version: int
    passed: bool
    created_at: datetime


class AdminCortexCanonicalCertificationArchivesListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    certification_pack_schema_version: int
    tenant_id: str
    archives: list[AdminCortexCanonicalCertificationArchiveItem]


class AdminCortexCanonicalCertificationArchiveDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    tenant_id: str
    certification_pack_schema_version: int
    passed: bool
    created_at: datetime
    pack: dict[str, Any]


class AdminCortexCanonicalCertificationArchiveRequest(BaseModel):
    """Phase 03 Step 18 — optional tuning for certification materialization sampling."""

    model_config = ConfigDict(extra="forbid")

    materialization_sample_limit: int = 50


class AdminCortexRawMemoryPhaseClosureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    passed: bool
    phase_status: str
    checks: list[dict[str, Any]]
    gate_results: dict[str, dict[str, Any]]
    summary: dict[str, Any]


class AdminCortexCanonicalOntologyObjectKindItem(BaseModel):
    """Phase 03 — one frozen structural object kind (Steps 1–2 enrich with taxonomy fields)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    layer: str
    taxonomy_family: str
    structural_role: str
    structural_examples: list[str]
    description: str


class AdminCortexCanonicalOntologyTaxonomyFamilyItem(BaseModel):
    """Phase 03 Step 2 — one taxonomy family boundary (maps to `CanonicalLayerKind`)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    boundary_definition: str


class AdminCortexCanonicalOntologyKindTaxonomyItem(BaseModel):
    """Phase 03 Step 2 — per-kind taxonomy row (aligned with `object_kinds`)."""

    model_config = ConfigDict(extra="forbid")

    object_kind_id: str
    taxonomy_family: str
    structural_role: str
    structural_examples: list[str]


class AdminCortexCanonicalOntologyArcItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_kind: str
    edge_kind: str
    to_kind: str


class AdminCortexCanonicalLogicalKeyKindItem(BaseModel):
    """Phase 03 Step 3 — ordered idempotency tuple fields for one canonical object kind."""

    model_config = ConfigDict(extra="forbid")

    canonical_object_kind: str
    idempotency_tuple_fields: list[str]
    tie_break_notes: str | None = None


class AdminCortexMappingEvidenceGradeItem(BaseModel):
    """Phase 03 Step 4 — E0/E1 evidence posture for emitted canonical fields."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    definition: str


class AdminCortexMappingAllowedOpItem(BaseModel):
    """Phase 03 Step 4 — allowed deterministic mapping operation category."""

    model_config = ConfigDict(extra="forbid")

    id: str
    description: str


class AdminCortexMappingTableColumnItem(BaseModel):
    """Phase 03 Step 4 — one column in the frozen mapping-table row authoring schema."""

    model_config = ConfigDict(extra="forbid")

    column: str
    value_type: str
    required: bool
    description: str


class AdminCortexCanonicalOntologyResponse(BaseModel):
    """Frozen Phase 03 ontology + taxonomy + logical keys + mapping contracts + class graph (read-only)."""

    model_config = ConfigDict(extra="forbid")

    ontology_schema_version: int
    phase: str
    implementation_step: int
    completed_implementation_steps: list[int]
    name: str
    tenant_id: str | None = None
    layers: list[str]
    object_kinds: list[AdminCortexCanonicalOntologyObjectKindItem]
    structural_arcs: list[AdminCortexCanonicalOntologyArcItem]
    taxonomy_families: list[AdminCortexCanonicalOntologyTaxonomyFamilyItem]
    kind_taxonomy: list[AdminCortexCanonicalOntologyKindTaxonomyItem]
    taxonomy_hard_rules: list[str]
    logical_key_profile_version: int
    logical_key_global_rules: list[str]
    logical_keys_by_kind: list[AdminCortexCanonicalLogicalKeyKindItem]
    logical_key_doctrine_anchors: list[str]
    mapping_contract_schema_version: int
    evidence_grades: list[AdminCortexMappingEvidenceGradeItem]
    determinism_criteria: list[str]
    structural_extraction_definition: str
    semantic_inference_forbidden_definition: str
    allowed_deterministic_operations: list[AdminCortexMappingAllowedOpItem]
    forbidden_operations: list[str]
    field_emission_posture_rules: list[str]
    mapping_versioning_rules: list[str]
    mapping_table_row_shape: list[AdminCortexMappingTableColumnItem]
    mapping_contract_doctrine_anchors: list[str]
    mapping_registry_surface_version: int
    mapping_registry_admin_route: str
    mapping_registry_doctrine_anchors: list[str]
    transform_runtime_surface_version: int
    transform_materialize_route: str
    transform_lineage_route: str
    transform_lineage_includes_confidence: bool
    transform_supports_replay_job_link: bool
    transform_emits_provenance_record: bool
    transform_persists_temporal_ordering: bool
    transform_runtime_doctrine_anchors: list[str]
    replay_runtime_surface_version: int
    replay_jobs_list_route: str
    replay_job_detail_route: str
    replay_job_run_route: str
    replay_divergence_taxonomy: list[dict[str, Any]]
    replay_runtime_doctrine_anchors: list[str]
    provenance_runtime_surface_version: int
    provenance_by_raw_record_route: str
    provenance_by_materialization_route: str
    provenance_evidence_shapes_documented: list[str]
    provenance_runtime_doctrine_anchors: list[str]
    temporal_runtime_surface_version: int
    temporal_supersessions_list_route: str
    temporal_rebuild_preview_route: str
    temporal_ordering_precedence: list[str]
    temporal_runtime_doctrine_anchors: list[str]
    canonical_query_surface_version: int
    canonical_query_route: str
    canonical_query_classes: list[str]
    canonical_query_doctrine_anchors: list[str]
    failure_remediation_surface_version: int
    canonical_failures_route: str
    canonical_remediation_validate_route: str
    failure_degradation_taxonomy: list[str]
    failure_classes_documented: list[str]
    remediation_classes_documented: list[str]
    failure_remediation_doctrine_anchors: list[str]
    verification_engine_surface_version: int
    canonical_verification_run_route: str
    canonical_verification_repair_determinism_route: str
    canonical_verification_runs_list_route: str
    verification_engine_gate_ids: list[str]
    verification_engine_doctrine_anchors: list[str]
    canonical_control_plane_surface_version: int
    canonical_control_plane_route: str
    canonical_control_plane_doctrine_anchors: list[str]
    stabilization_proof_surface_version: int
    canonical_stabilization_proof_route: str
    canonical_stabilization_proof_run_route: str
    canonical_stabilization_proof_runs_route: str
    stabilization_proof_doctrine_anchors: list[str]
    certification_pack_surface_version: int
    canonical_certification_pack_route: str
    canonical_certification_pack_archive_route: str
    canonical_certification_pack_archives_route: str
    certification_pack_doctrine_anchors: list[str]
    confidence_propagation_surface_version: int
    confidence_propagation_schema_version: int
    confidence_non_ranking_semantics: str
    confidence_allowed_classes: list[dict[str, Any]]
    confidence_forbidden_classes: list[dict[str, Any]]
    confidence_summary_admin_route: str
    confidence_propagation_doctrine_anchors: list[str]
    ambiguity_runtime_surface_version: int
    ambiguity_list_route: str
    ambiguity_open_route: str
    ambiguity_detail_route: str
    ambiguity_lifecycle_route: str
    ambiguity_runtime_doctrine_anchors: list[str]
    identity_runtime_surface_version: int
    identity_anchors_list_route: str
    identity_anchor_detail_route: str
    identity_runtime_doctrine_anchors: list[str]
    org_entity_runtime_surface_version: int
    org_entity_list_route: str
    org_entity_detail_route: str
    org_handle_explorer_list_route: str
    org_handle_explorer_detail_route: str
    org_entity_runtime_doctrine_anchors: list[str]
    link_ledger_runtime_surface_version: int
    link_ledger_list_route: str
    link_ledger_detail_route: str
    link_ledger_revoke_route: str
    link_candidate_queue_route: str
    celery_task_regenerate_link_candidates: str
    celery_task_replay_authoritative_links: str
    link_ledger_runtime_doctrine_anchors: list[str]
    link_hint_bucket_route: str
    link_temporal_timeline_route: str
    merge_governance_runtime_surface_version: int
    merge_ledger_list_route: str
    merge_ledger_append_route: str
    merge_queue_list_route: str
    merge_queue_detail_route: str
    merge_governance_runtime_doctrine_anchors: list[str]
    bundle_equivalence_runtime_surface_version: int
    bundle_equivalence_list_route: str
    bundle_equivalence_append_route: str
    bundle_equivalence_runtime_doctrine_anchors: list[str]
    org_link_replay_runtime_surface_version: int
    org_link_replay_jobs_list_route: str
    org_link_replay_job_detail_route: str
    org_link_replay_job_run_route: str
    org_link_replay_job_enqueue_route: str
    identity_worker_task_status_route: str
    org_link_replay_drift_taxonomy: list[dict[str, Any]]
    celery_task_run_org_link_replay_job: str
    org_link_replay_runtime_doctrine_anchors: list[str]
    link_rule_version_runtime_surface_version: int
    link_rule_versions_list_route: str
    link_rule_version_append_route: str
    link_rule_version_detail_route: str
    link_rule_version_runtime_doctrine_anchors: list[str]
    execution_primitive_persistence_surface_version: int
    org_primitive_instances_list_route: str
    org_primitive_explorer_list_route: str
    org_primitive_explorer_detail_route: str
    org_primitive_instance_detail_route: str
    org_primitive_instance_append_route: str
    execution_primitive_persistence_doctrine_anchors: list[str]
    org_graph_projection_export_surface_version: int
    org_graph_projection_export_route: str
    org_graph_projection_preview_route: str
    org_graph_projection_export_async_run_route: str
    org_graph_projection_export_doctrine_anchors: list[str]
    org_ambiguity_runtime_surface_version: int
    org_ambiguities_list_route: str
    org_ambiguity_detail_route: str
    org_ambiguity_queue_list_route: str
    org_ambiguity_queue_detail_route: str
    org_ambiguity_append_route: str
    org_ambiguity_runtime_doctrine_anchors: list[str]
    org_identity_verification_engine_schema_version: int
    org_identity_verification_run_route: str
    org_identity_verification_runs_list_route: str
    org_identity_verification_doctrine_anchors: list[str]
    org_identity_backfill_surface_version: int
    org_identity_backfill_schema_version: int
    org_identity_backfill_from_anchors_route: str
    org_identity_backfill_runs_route: str
    org_identity_backfill_doctrine_anchors: list[str]
    org_failure_remediation_surface_version: int
    org_failures_route: str
    org_remediation_validate_route: str
    org_failure_classes_documented: list[str]
    org_remediation_classes_documented: list[str]
    org_failure_remediation_doctrine_anchors: list[str]
    identity_control_plane_surface_version: int
    identity_control_plane_route: str
    identity_control_plane_contract: str
    identity_operator_console_surface_version: int
    identity_operator_console_http_routes: list[str]
    identity_control_plane_doctrine_anchors: list[str]
    identity_readiness_economics_surface_version: int
    identity_readiness_economics_schema_version: int
    identity_readiness_economics_route: str
    identity_readiness_economics_contract: str
    identity_readiness_economics_doctrine_anchors: list[str]
    org_identity_certification_pack_surface_version: int
    org_identity_certification_pack_route: str
    org_identity_certification_pack_archive_route: str
    org_identity_certification_pack_archives_route: str
    org_identity_certification_pack_archive_detail_route: str
    org_identity_certification_pack_doctrine_anchors: list[str]
    doctrine_anchors: list[str]


class AdminCortexMappingBundleRow(BaseModel):
    """Phase 03 Step 5 — one mapping bundle inventory row."""

    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    lifecycle_state: str
    manifest_hash: str
    owner_team: str
    title: str | None = None
    notes: str | None = None
    predecessor_bundle_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminCortexMappingCompatibilityEdgeRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_bundle_id: str
    to_bundle_id: str
    edge_kind: str
    is_breaking: bool
    rationale: str | None = None
    declared_at: datetime | None = None


class AdminCortexMappingBundlePinRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pin_id: uuid.UUID
    tenant_id: uuid.UUID
    bundle_id: str
    scope_kind: str
    scope_marker: str
    effective_from: datetime | None = None
    policy_reference: str | None = None
    created_at: datetime | None = None


class AdminCortexMappingBundleChangelogRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    sequence_number: int
    summary: str
    breaking_classification: str
    artifact_delta: dict[str, Any]
    oracle_vector_refs: list[Any]
    compatibility_edges_delta: dict[str, Any]
    invalidation_scope: dict[str, Any]
    ci_report_refs: list[Any]
    created_at: datetime | None = None


class AdminCortexMappingRegistryResponse(BaseModel):
    """Phase 03 Step 5 — mapping bundle registry snapshot (read-only)."""

    model_config = ConfigDict(extra="forbid")

    registry_schema_version: int
    mapping_registry_surface_version: int
    phase: str
    implementation_step: int
    completed_implementation_steps: list[int]
    name: str
    tenant_id: str
    bundles: list[AdminCortexMappingBundleRow]
    compatibility_edges: list[AdminCortexMappingCompatibilityEdgeRow]
    pins_for_tenant: list[AdminCortexMappingBundlePinRow]
    changelog_entries: list[AdminCortexMappingBundleChangelogRow]
    doctrine_anchors: list[str]


class AdminCortexCanonicalFieldLineageItem(BaseModel):
    """Phase 03 Steps 6–8 — one field-level lineage receipt + confidence metadata."""

    model_config = ConfigDict(extra="forbid")

    field_path: str
    rule_id: str
    evidence_grade: str
    confidence_class: str
    confidence_metadata: dict[str, Any]
    source_paths: list[Any]
    value_snapshot: Any | None = None


class AdminCortexCanonicalTransformMaterializationItem(BaseModel):
    """Phase 03 Steps 6–12 — materialization summary + lineage + confidence + identity + replay + temporal hooks."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    bundle_id: str
    raw_record_id: int
    last_replay_job_id: uuid.UUID | None = None
    canonical_entity_id: uuid.UUID
    phase04_boundary: dict[str, Any]
    canonical_object_kind: str
    logical_key_json: dict[str, Any]
    logical_key_hash: str
    emitted_snapshot_json: dict[str, Any]
    emitted_snapshot_hash: str
    engine_build_ref: str
    occurred_at: datetime | None = None
    observed_at: datetime | None = None
    canonical_processed_at: datetime | None = None
    source_revision_key: str | None = None
    temporal_ordering_key: str | None = None
    created_at: datetime | None = None
    confidence_rollup: dict[str, Any]
    field_lineage: list[AdminCortexCanonicalFieldLineageItem]


class AdminCortexTemporalRebuildPreviewRequest(BaseModel):
    """Phase 03 Step 12 — deterministic rebuild ordering preview for raw ids (no writes)."""

    model_config = ConfigDict(extra="forbid")

    raw_record_ids: list[int] = Field(min_length=1, max_length=500)


class AdminCortexTemporalRebuildPreviewRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_record_id: int
    temporal_ordering_key: str
    occurred_at: str
    source_revision_key: str
    replay_sequence: int
    replay_topology_order_index: int = 0


class AdminCortexTemporalRebuildPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temporal_runtime_schema_version: int
    tenant_id: str
    ordered: list[AdminCortexTemporalRebuildPreviewRow]


class AdminCortexTemporalSupersessionItem(BaseModel):
    """Phase 03 Step 12 — one append-only supersession ledger row."""

    model_config = ConfigDict(extra="forbid")

    id: int
    tenant_id: uuid.UUID
    bundle_id: str
    predecessor_materialization_id: uuid.UUID
    predecessor_logical_key_hash: str
    successor_materialization_id: uuid.UUID | None
    causing_raw_record_id: int
    engine_build_ref: str
    created_at: datetime | None = None


class AdminCortexTemporalSupersessionsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temporal_runtime_schema_version: int
    tenant_id: str
    items: list[AdminCortexTemporalSupersessionItem]


CanonicalQueryClass = Literal[
    "point_lookup_materialization",
    "point_lookup_identity_anchor",
    "evidence_backtrace",
    "forward_trace",
    "timeline_slice",
    "graph_neighborhood",
    "replay_debug_snapshot",
]
CanonicalQueryIntent = Literal[
    "evidence_retrieval",
    "point_lookup",
    "evidence_backtrace",
    "forward_trace",
    "timeline_retrieval",
    "neighborhood_retrieval",
    "replay_debug",
]


class AdminCortexCanonicalQueryRequest(BaseModel):
    """Phase 03 Step 13 — bounded canonical query (class + params); anti-goals enforced server-side."""

    model_config = ConfigDict(extra="forbid")

    query_class: CanonicalQueryClass
    intent: CanonicalQueryIntent = "evidence_retrieval"
    query_text: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=50, ge=1, le=200)


class AdminCortexCanonicalQueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_query_runtime_schema_version: int
    tenant_id: str
    query_class: str
    result_kind: str
    payload: dict[str, Any]
    truncation: dict[str, Any] | None = None


CanonicalRemediationClass = Literal["scoped_rebuild", "ambiguity_triage_ack"]


class AdminCortexCanonicalFailureCaseItem(BaseModel):
    """Phase 03 Step 14 — one active (or listed) canonical failure / degradation case."""

    model_config = ConfigDict(extra="forbid")

    gap_id: str
    tenant_id: str
    failure_class: str
    degradation_state: str
    scope_kind: str
    scope_json: dict[str, Any]
    detail_json: dict[str, Any]
    source: str
    active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminCortexCanonicalRemediationValidationItem(BaseModel):
    """Phase 03 Step 14 — auditable remediation validation ledger row."""

    model_config = ConfigDict(extra="forbid")

    id: int
    tenant_id: str
    failure_case_gap_id: str | None = None
    remediation_class: str
    dry_run: bool
    confirm_execution: bool
    payload_json: dict[str, Any]
    result_status: str
    result_detail_json: dict[str, Any]
    created_at: datetime | None = None


class AdminCortexCanonicalFailuresResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    failure_remediation_runtime_schema_version: int
    tenant_id: str
    active_failure_count: int
    active_failure_classes: dict[str, int]
    cases: list[AdminCortexCanonicalFailureCaseItem]
    recent_remediation_validations: list[AdminCortexCanonicalRemediationValidationItem]


class AdminCortexCanonicalRemediationValidateRequest(BaseModel):
    """Phase 03 Step 14 — policy-gated remediation (scoped rebuild or ambiguity triage ack)."""

    model_config = ConfigDict(extra="forbid")

    remediation_class: CanonicalRemediationClass
    dry_run: bool = True
    confirm_execution: bool = False
    failure_case_gap_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class AdminCortexCanonicalRemediationValidateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    remediation_class: str
    validation: AdminCortexCanonicalRemediationValidationItem


class AdminCortexCanonicalVerificationGateResult(BaseModel):
    """Phase 03 Step 15 — one gate outcome from the canonical verification engine."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    passed: bool
    severity: str = "hard_fail"
    detail: dict[str, Any] = Field(default_factory=dict)


class AdminCortexCanonicalVerificationRunRequest(BaseModel):
    """Phase 03 Step 15 — operator / CI verification sweep parameters."""

    model_config = ConfigDict(extra="forbid")

    persist: bool = True
    materialization_sample_limit: int = Field(default=50, ge=1, le=200)


class AdminCortexCanonicalVerificationRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_verification_engine_schema_version: int
    tenant_id: str
    passed: bool
    gates: list[AdminCortexCanonicalVerificationGateResult]
    evidence: dict[str, Any]
    persisted_run_id: int | None = None


class AdminCortexCanonicalDeterminismRepairRequest(BaseModel):
    """Re-scan materializations vs oracle and rematerialize mismatches (G-P03-01 drift repair)."""

    model_config = ConfigDict(extra="forbid")

    bundle_id: str | None = None
    scan_limit: int = Field(default=500, ge=1, le=5000)
    dry_run: bool = False


class AdminCortexCanonicalDeterminismRepairResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transform_runtime_schema_version: int
    tenant_id: str
    bundle_id_filter: str | None
    scanned_count: int
    mismatch_count: int
    resolution_failed_count: int
    repaired_count: int
    dry_run: bool
    mismatch_sample: list[dict[str, Any]]
    resolution_failed_sample: list[dict[str, Any]]


class AdminCortexCanonicalVerificationRunItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    tenant_id: str
    engine_schema_version: int
    passed: bool
    gates: list[AdminCortexCanonicalVerificationGateResult]
    evidence: dict[str, Any]
    created_at: datetime | None = None


class AdminCortexCanonicalVerificationRunsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_verification_engine_schema_version: int
    tenant_id: str
    runs: list[AdminCortexCanonicalVerificationRunItem]


class AdminCortexOrgIdentityVerificationRunRequest(BaseModel):
    """Phase 04 Step 15 — org Phase 04 gate slice; mirrors canonical verification request shape."""

    model_config = ConfigDict(extra="forbid")

    persist: bool = True
    materialization_sample_limit: int = Field(default=50, ge=1, le=200)


class AdminCortexOrgIdentityVerificationRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_identity_verification_engine_schema_version: int
    tenant_id: str
    passed: bool
    gates: list[AdminCortexCanonicalVerificationGateResult]
    evidence: dict[str, Any]
    persisted_run_id: int | None = None


class AdminCortexOrgIdentityVerificationRunItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    tenant_id: str
    engine_schema_version: int
    passed: bool
    gates: list[AdminCortexCanonicalVerificationGateResult]
    evidence: dict[str, Any]
    created_at: datetime | None = None


class AdminCortexOrgIdentityVerificationRunsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_identity_verification_engine_schema_version: int
    tenant_id: str
    runs: list[AdminCortexOrgIdentityVerificationRunItem]


OrgRemediationClass = Literal["org_ambiguity_triage_ack", "org_link_replay_retry"]


class AdminCortexOrgFailureCaseItem(BaseModel):
    """Phase 04 Step 16 — one active org linkage / continuity failure case."""

    model_config = ConfigDict(extra="forbid")

    gap_id: str
    tenant_id: str
    failure_class: str
    degradation_state: str
    scope_kind: str
    scope_json: dict[str, Any]
    detail_json: dict[str, Any]
    source: str
    active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminCortexOrgRemediationValidationItem(BaseModel):
    """Phase 04 Step 16 — org remediation validation ledger row."""

    model_config = ConfigDict(extra="forbid")

    id: int
    tenant_id: str
    failure_case_gap_id: str | None = None
    remediation_class: str
    dry_run: bool
    confirm_execution: bool
    payload_json: dict[str, Any]
    result_status: str
    result_detail_json: dict[str, Any]
    created_at: datetime | None = None


class AdminCortexOrgFailuresResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_failure_remediation_runtime_schema_version: int
    tenant_id: str
    active_failure_count: int
    active_failure_classes: dict[str, int]
    cases: list[AdminCortexOrgFailureCaseItem]
    recent_remediation_validations: list[AdminCortexOrgRemediationValidationItem]


class AdminCortexOrgRemediationValidateRequest(BaseModel):
    """Phase 04 Step 16 — policy-gated org remediation (ambiguity ack or org link replay retry)."""

    model_config = ConfigDict(extra="forbid")

    remediation_class: OrgRemediationClass
    dry_run: bool = True
    confirm_execution: bool = False
    failure_case_gap_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class AdminCortexOrgRemediationValidateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    remediation_class: str
    validation: AdminCortexOrgRemediationValidationItem


class AdminCortexIdentityControlPlaneResponse(BaseModel):
    """Phase 04 Step 17 — **identity_control_plane_v1** aggregate (Execution Continuity Operator Console)."""

    model_config = ConfigDict(extra="forbid")

    identity_control_plane_runtime_schema_version: int
    schema_version: str
    tenant_id: str
    computed_at: str
    freshness_label: Literal["fresh", "stale"]
    cards: dict[str, Any]
    last_authoritative_replay_job: dict[str, Any] | None
    last_candidate_regen_job: dict[str, Any] | None
    last_continuity_rebuild_job: dict[str, Any] | None
    verification_pointer: dict[str, Any]
    continuity_substrate: dict[str, Any] = Field(default_factory=dict)
    substrate_truth_contract: str | None = None
    substrate_truth_path: str | None = None


class AdminCortexIdentityContinuityRebuildRequest(BaseModel):
    """Operator rebuild — canonical drain → anchor backfill → candidate regen (deterministic)."""

    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    materialize_batch_limit: int = Field(default=2000, ge=1, le=2000)
    anchor_limit: int = Field(default=5000, ge=1, le=50_000)
    run_determinism_repair: bool = True
    dry_run: bool = False


class AdminCortexIdentityContinuityRebuildResponse(BaseModel):
    """Full rebuild report (nested for OpenAPI clarity)."""

    model_config = ConfigDict(extra="forbid")

    rebuild: dict[str, Any]


class AdminCortexIdentityContinuityVerifyResponse(BaseModel):
    """Fixture pressure scan + substrate counts (read-only)."""

    model_config = ConfigDict(extra="forbid")

    scenario_key: str
    substrate_counts: dict[str, int]
    fixture_pressure: dict[str, Any]


class AdminCortexIdentityContinuityEvidenceInspectResponse(BaseModel):
    """Read-only continuity evidence propagation (raw → canonical → anchor → rules), no orchestration."""

    model_config = ConfigDict(extra="forbid")

    continuity_evidence_inspect_schema_version: int
    tenant_id: str
    scenario_key: str
    anchor_scan_limit_applied: int
    substrate_counters: dict[str, Any]
    anchors_primary_skip_reason_counts: dict[str, Any]
    anchors_missing_identity_flag_counts: dict[str, Any]
    canonical_kind_counts: dict[str, int]
    org_entity_kind_counts: dict[str, int]
    identity_primitive_projection_metrics: dict[str, Any] = Field(default_factory=dict)
    github_email_extraction_metrics: dict[str, Any] = Field(default_factory=dict)
    continuity_gap_reasons: list[dict[str, Any]] = Field(default_factory=list)
    continuity_join_reason_catalog: dict[str, str] = Field(default_factory=dict)
    rule_pack_semantic: str
    current_engine_candidate_row_count: int
    candidate_pair_evidence_accumulation: dict[str, Any] = Field(default_factory=dict)
    substrate_sparse_honesty: dict[str, Any] = Field(default_factory=dict)
    sampled_rows: list[dict[str, Any]]
    fixture_survival_sample: list[dict[str, Any]]
    hostile_continuity_dry_run_trace: dict[str, Any]
    notes: list[str]


class AdminCortexIdentityContinuityHealthResponse(BaseModel):
    """Lightweight identity continuity health (execution-derived, operator truth)."""

    model_config = ConfigDict(extra="forbid")

    identity_continuity_health_schema_version: int
    tenant_id: str
    anchor_count: int
    identity_primitive_projection_metrics: dict[str, Any] = Field(default_factory=dict)
    github_email_extraction_metrics: dict[str, Any] = Field(default_factory=dict)
    continuity_gap_reasons: list[dict[str, Any]] = Field(default_factory=list)
    continuity_join_reason_catalog: dict[str, str] = Field(default_factory=dict)
    current_engine_candidate_row_count: int = 0
    substrate_counters: dict[str, Any] = Field(default_factory=dict)
    onboarding_continuity_seeds: dict[str, Any] = Field(default_factory=dict)
    actor_gap_taxonomy: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AdminCortexIdentityReadinessEconomicsResponse(BaseModel):
    """Phase 04 Step 21 — **identity_readiness_economics_v1** (storage + regen/replay cost hints)."""

    model_config = ConfigDict(extra="forbid")

    identity_readiness_economics_schema_version: int
    schema_version: str
    tenant_id: str
    computed_at: str
    counts: dict[str, Any]
    thresholds: dict[str, Any]
    storage_estimate_bytes: int
    storage_row_byte_assumptions: dict[str, int]
    regen_replay_cost_hints: dict[str, int]
    warnings: list[dict[str, Any]]
    overall_posture: Literal["ok", "warn", "critical"]


class AdminCortexOrgIdentityCertificationPackClosureGateRow(BaseModel):
    """Phase 04 Step 22 — one org closure gate row (G-P04-CLOSE-MAP-* / G-P04-CLOSE-01)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    passed: bool
    severity: str
    detail: dict[str, Any]


class AdminCortexOrgIdentityCertificationPackResponse(BaseModel):
    """Phase 04 Step 22 — org identity closure certification pack + matrix."""

    model_config = ConfigDict(extra="forbid")

    org_certification_pack_schema_version: int
    tenant_id: str
    built_at_clock: str
    canonical_verification_excerpt: dict[str, Any]
    phase04_gate_excerpt: dict[str, Any]
    identity_control_plane_excerpt: dict[str, Any]
    readiness_economics_excerpt: dict[str, Any]
    org_verification_last_excerpt: dict[str, Any]
    doctrine_notes: dict[str, Any]
    closure_gate_matrix: list[AdminCortexOrgIdentityCertificationPackClosureGateRow]
    org_identity_certification_pack_contract: dict[str, Any]


class AdminCortexOrgIdentityCertificationArchiveRequest(BaseModel):
    """Phase 04 Step 22 — optional tuning for certification sampling (canonical materialization window)."""

    model_config = ConfigDict(extra="forbid")

    materialization_sample_limit: int = 50


class AdminCortexOrgIdentityCertificationArchiveResponse(BaseModel):
    """Result of attempting to persist an org certification pack (requires full closure PASS)."""

    model_config = ConfigDict(extra="forbid")

    persisted: bool
    passed: bool
    archive_id: int | None
    org_certification_pack_schema_version: int
    tenant_id: str
    pack: dict[str, Any]


class AdminCortexOrgIdentityCertificationArchiveItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    tenant_id: str
    org_certification_pack_schema_version: int
    passed: bool
    created_at: datetime


class AdminCortexOrgIdentityCertificationArchivesListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_certification_pack_schema_version: int
    tenant_id: str
    archives: list[AdminCortexOrgIdentityCertificationArchiveItem]


class AdminCortexOrgIdentityCertificationArchiveDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    tenant_id: str
    org_certification_pack_schema_version: int
    passed: bool
    created_at: datetime
    pack: dict[str, Any]


class AdminCortexMaterializeTransformRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_record_id: int
    bundle_id: str


class AdminCortexMaterializeTransformResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    materialization: AdminCortexCanonicalTransformMaterializationItem


class AdminCortexMaterializeBacklogRequest(BaseModel):
    """Bulk stub materialization for ingested rows missing a projection for ``bundle_id``."""

    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    connector: str | None = Field(
        default=None,
        description="Optional: limit backlog scan to one connector with registered transform routes.",
    )
    resource_type: str | None = Field(
        default=None,
        description="Optional: limit backlog scan to one resource_type within selected connector.",
    )
    batch_limit: int = Field(default=200, ge=1, le=2000)
    dry_run: bool = Field(default=False, description="Plan only — counts/sample ids without writing.")


class AdminCortexMaterializeBacklogFailureItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_record_id: int
    detail: str


class AdminCortexMaterializeBacklogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transform_runtime_schema_version: int
    tenant_id: str
    bundle_id: str
    dry_run: bool
    stub_resource_pairs_selected: list[str]
    scope_connector: str | None = None
    scope_resource_type: str | None = None
    batch_limit_applied: int
    candidate_more_remain: bool
    attempted: int
    attempted_by_resource_type: dict[str, int] = Field(default_factory=dict)
    succeeded: int
    succeeded_by_resource_type: dict[str, int] = Field(default_factory=dict)
    failures: list[AdminCortexMaterializeBacklogFailureItem]
    raw_record_ids_sample: list[int]
    duration_ms: int | None = None
    throughput_rows_per_second: float | None = None


class AdminCortexMaterializeBacklogAsyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str | None = Field(
        default=None,
        description="Optional override; otherwise first tenant pin or eligible inventory bundle.",
    )
    connector: str | None = Field(default=None, description="Optional connector scope.")
    resource_type: str | None = Field(
        default=None,
        description="Optional resource_type scope (requires registered transform route).",
    )
    batch_limit: int | None = Field(
        default=None,
        ge=1,
        le=2000,
        description="Optional per-batch size override for async drain.",
    )


class AdminCortexMaterializeBacklogAsyncResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enqueued: bool
    celery_task_id: str
    tenant_id: str
    bundle_id_used: str
    scope_connector: str | None = None
    scope_resource_type: str | None = None
    batch_limit: int | None = None


class AdminCortexTransformLineageListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transform_runtime_schema_version: int
    confidence_propagation_schema_version: int
    tenant_id: str
    materializations: list[AdminCortexCanonicalTransformMaterializationItem]


class AdminCortexConfidenceSummaryResponse(BaseModel):
    """Phase 03 Step 8 — tenant-wide confidence class counts over persisted field lineage (non-ranking)."""

    model_config = ConfigDict(extra="forbid")

    confidence_propagation_schema_version: int
    tenant_id: str
    field_lineage_rows_total: int
    by_confidence_class: dict[str, int]
    confidence_non_ranking_semantics: str


class AdminCortexIdentityAnchorItem(BaseModel):
    """Phase 03 Step 9 — one stable canonical entity anchor + Phase 04 handoff metadata."""

    model_config = ConfigDict(extra="forbid")

    canonical_entity_id: uuid.UUID
    tenant_id: uuid.UUID
    bundle_id: str
    canonical_object_kind: str
    provider_identity_hash: str
    provider_identity_json: dict[str, Any]
    logical_key_hash: str
    materialization_id: uuid.UUID | None = None
    raw_record_id: int
    connector: str
    phase04_boundary: dict[str, Any]
    engine_build_ref: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminCortexIdentityAnchorListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identity_runtime_schema_version: int
    tenant_id: str
    anchors: list[AdminCortexIdentityAnchorItem]


class AdminCortexOrgEntityItem(BaseModel):
    """Phase 04 Step 3 — one tenant-scoped org handle (org entity), distinct from Phase 03 anchors."""

    model_config = ConfigDict(extra="forbid")

    org_entity_runtime_schema_version: int
    id: uuid.UUID
    tenant_id: uuid.UUID
    entity_kind: str
    lifecycle_state: str
    superseded_by_id: uuid.UUID | None
    identity_key_fingerprint: str
    metadata_json: dict[str, Any]
    engine_build_ref: str
    tombstoned_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminCortexOrgEntityListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_entity_runtime_schema_version: int
    tenant_id: str
    entities: list[AdminCortexOrgEntityItem]


class AdminCortexOrgLinkItem(BaseModel):
    """Phase 04 Step 4 — one authoritative org-meaning link row (link ledger)."""

    model_config = ConfigDict(extra="forbid")

    link_ledger_runtime_schema_version: int
    id: uuid.UUID
    tenant_id: uuid.UUID
    link_type: str
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    evidence_raw_record_ids: list[int]
    rule_id: str | None
    confidence_class: str
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    revoked_at: datetime | None = None
    supersedes_link_id: uuid.UUID | None = None
    promoted_from_candidate_id: uuid.UUID | None = None
    promotion_policy_id: uuid.UUID | None = None
    link_authority: str
    link_class: str
    metadata_json: dict[str, Any]
    engine_build_ref: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminCortexOrgLinkExplorerRowV1(BaseModel):
    """Phase 04 Step 18 — ``org_link_list_row_v1`` contract (control plane §16.2)."""

    model_config = ConfigDict(extra="forbid")

    link_id: str
    link_type: str
    source_handle_id: str
    target: str
    target_kind: str
    rule_version: str
    link_layer: str
    valid_from: str | None = None
    valid_to: str | None = None
    evidence_count: int
    replay_state: str
    drift_class: str


class AdminCortexOrgLinkListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    link_ledger_runtime_schema_version: int
    tenant_id: str
    links: list[AdminCortexOrgLinkItem]
    identity_console_schema_version: int = 1
    explorer_contract: str = "org_link_list_row_v1"
    explorer_rows: list[AdminCortexOrgLinkExplorerRowV1] = Field(default_factory=list)


class AdminCortexIdentityOperatorActionRequest(BaseModel):
    """Phase 04 Step 18 — gated POST body for merge-queue actions + link revoke."""

    model_config = ConfigDict(extra="forbid")

    confirmation_phrase: str
    operator_note: str | None = None
    command_id: str | None = Field(default=None, max_length=128)


class AdminCortexOrgHandleListRowV1(BaseModel):
    """§16.2 — ``org_handle_list_row_v1``."""

    model_config = ConfigDict(extra="forbid")

    handle_id: str
    kind: str
    created_from: str
    persona_count: int
    active_links: int
    temporal_state: str
    merge_state: str
    last_replay: str
    confidence_posture: str
    candidate_persona_touch_count: int = 0
    candidate_any_touch_count: int = 0
    open_ambiguity_touch_count: int = 0
    entity_kind_rule: str | None = None


class AdminCortexIdentityHandlesExplorerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identity_operator_console_schema_version: int = 2
    tenant_id: str
    list_contract: str = "org_handle_list_row_v1"
    rows: list[AdminCortexOrgHandleListRowV1]


class AdminCortexMergeQueueRowV1(BaseModel):
    """§16.2 — ``org_merge_queue_row_v1``."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: str
    from_handle_id: str
    to_handle_id: str
    evidence_sources: list[str]
    why_generated: str
    policy_satisfied: bool
    candidate_age: int
    ambiguity_count: int
    risk_class: str


class AdminCortexMergeQueueListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merge_governance_schema_version: int
    tenant_id: str
    queue_contract: str = "org_merge_queue_row_v1"
    proposals: list[AdminCortexMergeQueueRowV1]


class AdminCortexMergeQueueDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merge_governance_schema_version: int
    tenant_id: str
    queue_contract: str = "org_merge_queue_row_v1"
    proposal: AdminCortexMergeQueueRowV1
    merge: AdminCortexOrgMergeItem


class AdminCortexOrgAmbiguityQueueRowV1(BaseModel):
    """§16.2 — ``org_ambiguity_queue_row_v1``."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    ambiguity_id: str
    row_class: str = Field(alias="class")
    severity: str
    exemplar_handle_ids: list[str]
    evidence_sample_ids: list[int]


class AdminCortexAmbiguityQueueListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_ambiguity_schema_version: int
    tenant_id: str
    queue_contract: str = "org_ambiguity_queue_row_v1"
    rows: list[AdminCortexOrgAmbiguityQueueRowV1]


class AdminCortexOrgPrimitiveListRowV1(BaseModel):
    """§16.2 — ``org_primitive_list_row_v1`` (optional ``envelope_json`` when flagged)."""

    model_config = ConfigDict(extra="forbid")

    primitive_id: str
    primitive_kind: str
    handle_count: int
    evidence_count: int
    canonical_ref_count: int
    temporal_bounds: dict[str, Any] = Field(default_factory=dict)
    replay_lineage: str
    export_participation: bool
    envelope_json: dict[str, Any] | None = None


class AdminCortexPrimitiveExplorerListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_primitive_instance_schema_version: int
    tenant_id: str
    list_contract: str = "org_primitive_list_row_v1"
    include_raw_envelope: bool = False
    rows: list[AdminCortexOrgPrimitiveListRowV1]


class AdminCortexOrgProjectionPreviewResponse(BaseModel):
    """§14 — graph export preview (metadata only)."""

    model_config = ConfigDict(extra="forbid")

    projection_preview_schema_version: int
    projection_schema_version: int
    tenant_id: str
    engine_build_ref: str
    node_counts: dict[str, int]
    edge_counts: dict[str, Any]
    edge_class_histogram: dict[str, int]
    projection_hash: str
    generated_at: str
    replay_source: dict[str, Any]


class AdminCortexOrgLinkTemporalStripItem(BaseModel):
    """Phase 04 Step 8 — compact validity + revocation strip for one link row."""

    model_config = ConfigDict(extra="forbid")

    id: str
    link_type: str
    valid_from: str | None = None
    valid_to: str | None = None
    revoked_at: str | None = None
    org_link_temporal_schema_version: int


class AdminCortexOrgLinkTemporalTimelineResponse(BaseModel):
    """Phase 04 Step 8 — ordered timeline strip (operator visibility)."""

    model_config = ConfigDict(extra="forbid")

    org_link_temporal_schema_version: int
    link_ledger_runtime_schema_version: int
    tenant_id: str
    strips: list[AdminCortexOrgLinkTemporalStripItem]


class AdminCortexOrgLinkCandidateRow(BaseModel):
    """Phase 04 Step 5 — one persisted candidate link row."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    batch_id: uuid.UUID
    link_type: str
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    evidence_raw_record_ids: list[int]
    rule_id: str | None
    row_digest: str
    created_at: datetime | None = None


class AdminCortexOrgLinkCandidateBatchSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    rule_version: str
    candidate_set_sha256: str
    candidate_count: int
    engine_build_ref: str
    created_at: datetime | None = None
    candidates: list[AdminCortexOrgLinkCandidateRow]


class AdminCortexOrgLinkCandidateQueueResponse(BaseModel):
    """Phase 04 Step 5 — sparse candidate queue (recent batches + rows)."""

    model_config = ConfigDict(extra="forbid")

    candidate_generation_schema_version: int
    tenant_id: str
    batches: list[AdminCortexOrgLinkCandidateBatchSummary]


class AdminCortexOrgMergeCreateRequest(BaseModel):
    """Phase 04 Step 6 — append merge ledger row (minimal approval = durable insert)."""

    model_config = ConfigDict(extra="forbid")

    merge_kind: Literal["human_actor_merge", "team_merge", "service_split", "compensating_merge"]
    merge_policy_id: uuid.UUID
    source_entity_ids: list[uuid.UUID]
    target_entity_id: uuid.UUID
    evidence_raw_record_ids: list[int] = Field(default_factory=list)
    operator_user_id: uuid.UUID | None = None
    supersedes_merge_id: uuid.UUID | None = None
    metadata_json: dict[str, Any] | None = None


class AdminCortexOrgMergeItem(BaseModel):
    """Phase 04 Step 6 — one append-only org merge ledger row."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    merge_kind: str
    merge_policy_id: uuid.UUID
    source_entity_ids: list[uuid.UUID]
    target_entity_id: uuid.UUID
    evidence_raw_record_ids: list[int]
    operator_user_id: uuid.UUID | None = None
    supersedes_merge_id: uuid.UUID | None = None
    metadata_json: dict[str, Any]
    engine_build_ref: str
    created_at: datetime | None = None


class AdminCortexOrgMergeListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    merge_governance_schema_version: int
    tenant_id: str
    merges: list[AdminCortexOrgMergeItem]


class AdminCortexBundleEquivalenceDeclarationCreateRequest(BaseModel):
    """Phase 04 Step 9 — append bundle equivalence declaration."""

    model_config = ConfigDict(extra="forbid")

    bundle_id_a: str = Field(min_length=1, max_length=256)
    bundle_id_b: str = Field(min_length=1, max_length=256)
    evidence_raw_record_ids: list[int] = Field(default_factory=list)
    metadata_json: dict[str, Any] | None = None


class AdminCortexBundleEquivalenceDeclarationItem(BaseModel):
    """Phase 04 Step 9 — one equivalence declaration row."""

    model_config = ConfigDict(extra="forbid")

    bundle_equivalence_schema_version: int
    id: str
    tenant_id: str
    left_bundle_id: str
    right_bundle_id: str
    replay_ordinal: int
    evidence_raw_record_ids: list[int]
    metadata_json: dict[str, Any]
    engine_build_ref: str
    created_at: str | None = None
    revoked_at: str | None = None


class AdminCortexBundleEquivalenceDeclarationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_equivalence_schema_version: int
    tenant_id: str
    declarations: list[AdminCortexBundleEquivalenceDeclarationItem]


class AdminCortexOrgLinkReplayJobRunRequest(BaseModel):
    """Phase 04 Step 10 — run one org link continuity replay / regen job (synchronous)."""

    model_config = ConfigDict(extra="forbid")

    job_kind: Literal[
        "authoritative_replay",
        "candidate_regen",
        "graph_projection_export",
        "identity_continuity_rebuild",
    ]
    pinned_rule_version: str | None = Field(
        default=None,
        description="For candidate_regen with dry_run=false, defaults to anchor continuity semantic if omitted.",
    )
    dry_run: bool = Field(default=False)
    scope_json: dict[str, Any] | None = None


class AdminCortexOrgLinkReplayJobItem(BaseModel):
    """Phase 04 Step 10 — one org link replay job row."""

    model_config = ConfigDict(extra="forbid")

    org_link_replay_schema_version: int
    id: uuid.UUID
    tenant_id: uuid.UUID
    job_kind: str
    pinned_rule_version: str | None = None
    dry_run: bool
    status: str
    scope_json: dict[str, Any]
    summary_json: dict[str, Any]
    error_detail: str | None = None
    engine_build_ref: str
    celery_task_id: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AdminCortexOrgLinkReplayJobEnqueueRequest(BaseModel):
    """Phase 04 Step 19 — enqueue async org link replay / projection export (same shape as sync run)."""

    model_config = ConfigDict(extra="forbid")

    job_kind: Literal[
        "authoritative_replay",
        "candidate_regen",
        "graph_projection_export",
        "identity_continuity_rebuild",
    ]
    pinned_rule_version: str | None = Field(
        default=None,
        description="For candidate_regen with dry_run=false, defaults to anchor continuity semantic if omitted.",
    )
    dry_run: bool = Field(default=False)
    scope_json: dict[str, Any] | None = None


class AdminCortexOrgLinkReplayJobEnqueueResponse(BaseModel):
    """Phase 04 Step 19 — queued job row + Celery id for worker-task polling."""

    model_config = ConfigDict(extra="forbid")

    org_link_replay_schema_version: int
    tenant_id: str
    celery_task_id: str
    worker_task_status_path: str
    job: AdminCortexOrgLinkReplayJobItem


class AdminCortexOrgLinkReplayJobRunResponse(BaseModel):
    """Phase 04 Step 10 — synchronous org link replay job result."""

    model_config = ConfigDict(extra="forbid")

    org_link_replay_schema_version: int
    tenant_id: str
    job: AdminCortexOrgLinkReplayJobItem


class AdminCortexGraphDensityPromotionRunRequest(BaseModel):
    """War-room unlock — inline graph density promotion pass for a tenant."""

    model_config = ConfigDict(extra="forbid")

    force: bool = False
    trigger: str = Field(default="manual", min_length=1, max_length=128)


class AdminCortexIdentityWorkerTaskStatusResponse(BaseModel):
    """Phase 04 Step 19 — Celery AsyncResult snapshot for tenant-bound tasks only."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    celery_task_id: str
    bind_source: Literal["replay_job", "dispatch"]
    job_id: uuid.UUID | None = None
    celery_state: str
    ready: bool
    result: dict[str, Any] | None = None
    error: str | None = None


class AdminCortexIdentityLinkCandidatesRegenerateAsyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_version: str = Field(min_length=1, max_length=256)


class AdminCortexIdentityLegacyCeleryAsyncDispatchResponse(BaseModel):
    """Phase 04 Step 19 — legacy regen/replay Celery tasks with dispatch registry row."""

    model_config = ConfigDict(extra="forbid")

    identity_legacy_async_dispatch_schema_version: Literal[1] = 1
    tenant_id: str
    celery_task_id: str
    task_name: str
    worker_task_status_path: str


class AdminCortexIdentityBackfillFromAnchorsRequest(BaseModel):
    """Phase 04 Step 20 — bounded anchor scan for org handle backfill."""

    model_config = ConfigDict(extra="forbid")

    dry_run: bool = False
    anchor_limit: int = Field(default=5_000, ge=1, le=50_000)
    include_candidate_regen: bool = Field(
        default=True,
        description="When true (default), run anchor continuity candidate regen after handle backfill.",
    )


class AdminCortexIdentityBackfillFromAnchorsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_identity_backfill_schema_version: int
    tenant_id: str
    dry_run: bool
    anchors_scanned: int
    entities_upserted: int
    backfill_set_sha256: str
    run_id: str | None = None
    engine_build_ref: str
    legacy_lane_org_entities_tombstoned: int = 0
    anchors_skipped_work_object_no_primitive: int = 0
    candidate_regeneration: dict[str, Any] | None = None


class AdminCortexIdentityBackfillRunItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    dry_run: bool
    anchors_scanned: int
    entities_upserted: int
    backfill_set_sha256: str
    summary_json: dict[str, Any]
    engine_build_ref: str
    created_at: str | None = None


class AdminCortexIdentityBackfillRunsListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_identity_backfill_schema_version: int
    tenant_id: str
    runs: list[AdminCortexIdentityBackfillRunItem]


class AdminCortexOrgLinkReplayJobReceiptItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    job_id: uuid.UUID
    receipt_class: str
    detail_json: dict[str, Any]
    created_at: datetime | None = None


class AdminCortexOrgLinkReplayJobDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_link_replay_schema_version: int
    tenant_id: str
    job: AdminCortexOrgLinkReplayJobItem
    receipts: list[AdminCortexOrgLinkReplayJobReceiptItem]


class AdminCortexOrgLinkReplayJobListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_link_replay_schema_version: int
    tenant_id: str
    jobs: list[AdminCortexOrgLinkReplayJobItem]


class AdminCortexLinkRuleVersionCreateRequest(BaseModel):
    """Phase 04 Step 11 — register a frozen linkage rule manifest for a tenant."""

    model_config = ConfigDict(extra="forbid")

    semantic_version: str = Field(min_length=1, max_length=128)
    rules_manifest_json: dict[str, Any] = Field(default_factory=dict)
    lifecycle_state: Literal["active", "deprecated"] = "active"
    notes: str | None = None


class AdminCortexLinkRuleVersionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    link_rule_version_schema_version: int
    id: uuid.UUID
    tenant_id: uuid.UUID
    semantic_version: str
    rules_manifest_json: dict[str, Any]
    manifest_sha256: str
    lifecycle_state: str
    notes: str | None = None
    engine_build_ref: str
    created_at: datetime | None = None


class AdminCortexLinkRuleVersionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    link_rule_version_schema_version: int
    tenant_id: str
    versions: list[AdminCortexLinkRuleVersionItem]


class AdminCortexLinkRuleVersionDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    link_rule_version_schema_version: int
    tenant_id: str
    version: AdminCortexLinkRuleVersionItem


class AdminCortexOrgPrimitiveInstanceAppendRequest(BaseModel):
    """Phase 04 Step 12 — persist one Phase 3.5 execution primitive envelope on an org entity."""

    model_config = ConfigDict(extra="forbid")

    org_entity_id: uuid.UUID
    envelope_json: dict[str, Any]
    lifecycle_state: Literal["active", "superseded", "revoked"] = "active"


class AdminCortexOrgPrimitiveInstanceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_primitive_instance_schema_version: int
    id: uuid.UUID
    tenant_id: uuid.UUID
    org_entity_id: uuid.UUID
    primitive_kind: str
    primitive_key: str
    envelope_json: dict[str, Any]
    lifecycle_state: str
    engine_build_ref: str
    created_at: datetime | None = None


class AdminCortexOrgPrimitiveInstanceListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_primitive_instance_schema_version: int
    tenant_id: str
    instances: list[AdminCortexOrgPrimitiveInstanceItem]


class AdminCortexOrgPrimitiveInstanceDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_primitive_instance_schema_version: int
    tenant_id: str
    instance: AdminCortexOrgPrimitiveInstanceItem


class AdminOrgGraphEntityNode(BaseModel):
    """OrgGraphProjectionV1 — org handle node."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["org_entity"]
    id: str
    entity_kind: str
    identity_key_fingerprint: str
    lifecycle_state: str
    tombstoned_at: str | None = None


class AdminOrgGraphPrimitiveNode(BaseModel):
    """OrgGraphProjectionV1 — execution primitive node (structural fields only)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["org_primitive"]
    id: str
    org_entity_id: str
    primitive_kind: str
    primitive_key: str
    lifecycle_state: str


class AdminOrgGraphMeaningEdge(BaseModel):
    """OrgGraphProjectionV1 — authoritative meaning link edge."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["org_meaning_link"]
    id: str
    link_type: str
    source_entity_id: str
    target_entity_id: str
    link_class: str
    link_authority: str
    confidence_class: str
    evidence_raw_record_ids: list[int]
    rule_id: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    revoked_at: str | None = None
    supersedes_link_id: str | None = None
    promoted_from_candidate_id: str | None = None
    promotion_policy_id: str | None = None


class AdminOrgGraphProjectionPayload(BaseModel):
    """Inner OrgGraphProjectionV1 document."""

    model_config = ConfigDict(extra="forbid")

    projection_schema_version: int
    tenant_id: str
    engine_build_ref: str
    nodes: list[AdminOrgGraphEntityNode | AdminOrgGraphPrimitiveNode]
    edges: list[AdminOrgGraphMeaningEdge]


class AdminCortexOrgGraphProjectionResponse(BaseModel):
    """Phase 04 Step 13 — deterministic org graph export for Phase 05."""

    model_config = ConfigDict(extra="forbid")

    org_graph_projection_schema_version: int
    tenant_id: str
    engine_build_ref: str
    projection: AdminOrgGraphProjectionPayload
    stable_hash_sha256: str


class AdminCortexOrgAmbiguityAppendRequest(BaseModel):
    """Phase 04 Step 14 — append one org-scoped multiplicity ambiguity receipt."""

    model_config = ConfigDict(extra="forbid")

    org_ambiguity_class: str
    subject_key: str
    involved_org_entity_ids: list[uuid.UUID] = Field(min_length=2)
    status: Literal["open", "acknowledged", "superseded", "void"] = "open"
    evidence_json: dict[str, Any] = Field(default_factory=dict)
    operator_note: str | None = None


class AdminCortexOrgAmbiguityItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_ambiguity_schema_version: int
    id: uuid.UUID
    tenant_id: uuid.UUID
    org_ambiguity_class: str
    subject_key: str
    status: str
    involved_org_entity_ids: list[str]
    evidence_json: dict[str, Any]
    superseded_by_org_ambiguity_id: uuid.UUID | None = None
    operator_note: str | None = None
    engine_build_ref: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminCortexOrgAmbiguityListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_ambiguity_schema_version: int
    tenant_id: str
    records: list[AdminCortexOrgAmbiguityItem]


class AdminCortexOrgAmbiguityDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_ambiguity_schema_version: int
    tenant_id: str
    record: AdminCortexOrgAmbiguityItem


class AdminCortexReplayJobRunRequest(BaseModel):
    """Phase 03 Step 10 — pinned-bundle canonical rebuild / regeneration scope."""

    model_config = ConfigDict(extra="forbid")

    pinned_bundle_id: str
    job_kind: Literal["rebuild", "regeneration"]
    raw_record_ids: list[int] | None = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Optional explicit object scope. When omitted, connector/resource_type scoped replay is used.",
    )
    connector: str | None = Field(
        default=None,
        description="Optional connector scope for localized replay.",
    )
    resource_type: str | None = Field(
        default=None,
        description="Optional resource-type scope for localized replay.",
    )
    include_dependency_neighborhood: bool = Field(
        default=False,
        description="When true, include parent dependencies needed for deterministic parent-before-child replay.",
    )
    subtree_anchor_raw_record_id: int | None = Field(
        default=None,
        description="Localized replay: include dependency descendants of this raw id (bounded).",
    )
    parent_anchor_raw_record_id: int | None = Field(
        default=None,
        description="Localized replay: walk parent dependencies upward from this raw id (bounded).",
    )
    source_bundle_id: str | None = Field(
        default=None,
        description="For regeneration across bundles: predecessor bundle id (compatibility edge required).",
    )
    dry_run: bool = Field(
        default=False,
        description="When true, emit divergence receipts only; do not materialize.",
    )


class AdminCortexReplayJobItem(BaseModel):
    """Phase 03 Step 10 — one canonical replay job row."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    pinned_bundle_id: str
    job_kind: str
    status: str
    source_bundle_id: str | None = None
    dry_run: bool
    scope_raw_record_ids: list[int]
    resolved_pin_json: dict[str, Any]
    engine_build_ref: str
    summary_json: dict[str, Any]
    error_detail: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class AdminCortexReplayJobReceiptItem(BaseModel):
    """Phase 03 Step 10 — divergence receipt for one raw row in a replay job."""

    model_config = ConfigDict(extra="forbid")

    id: int
    job_id: uuid.UUID
    raw_record_id: int
    divergence_class: str
    detail_json: dict[str, Any]
    materialize_error: str | None = None
    created_at: datetime | None = None


class AdminCortexReplayJobDetailResponse(BaseModel):
    """Phase 03 Step 10 — replay job + receipts."""

    model_config = ConfigDict(extra="forbid")

    replay_runtime_schema_version: int
    tenant_id: str
    job: AdminCortexReplayJobItem
    receipts: list[AdminCortexReplayJobReceiptItem]


class AdminCortexReplayJobListResponse(BaseModel):
    """Phase 03 Step 10 — recent replay jobs for tenant."""

    model_config = ConfigDict(extra="forbid")

    replay_runtime_schema_version: int
    tenant_id: str
    jobs: list[AdminCortexReplayJobItem]


class AdminCortexProvenanceRecordItem(BaseModel):
    """Phase 03 Step 11 — one provenance envelope + forward-index row."""

    model_config = ConfigDict(extra="forbid")

    id: int
    materialization_id: uuid.UUID
    tenant_id: uuid.UUID
    bundle_id: str
    raw_record_id: int
    canonical_object_kind: str
    logical_key_hash: str
    evidence_shape: str
    primary_raw_record_ids: list[int]
    rule_ids_involved: list[str]
    derivation_json: dict[str, Any]
    parent_materialization_id: uuid.UUID | None = None
    created_at: datetime | None = None


class AdminCortexProvenanceByRawResponse(BaseModel):
    """Phase 03 Step 11 — forward index: canonical projections citing a raw row."""

    model_config = ConfigDict(extra="forbid")

    provenance_runtime_schema_version: int
    tenant_id: str
    raw_record_id: int
    records: list[AdminCortexProvenanceRecordItem]


class AdminCortexProvenanceByMaterializationResponse(BaseModel):
    """Phase 03 Step 11 — reverse lookup: provenance envelope for one materialization."""

    model_config = ConfigDict(extra="forbid")

    provenance_runtime_schema_version: int
    tenant_id: str
    record: AdminCortexProvenanceRecordItem


class AdminCortexAmbiguityConnectorRollupItem(BaseModel):
    """Phase 03 Step 7 — ambiguity counts grouped by denormalized raw connector + resource type."""

    model_config = ConfigDict(extra="forbid")

    connector: str
    resource_type: str
    total: int
    open_count: int


class AdminCortexAmbiguityAggregates(BaseModel):
    model_config = ConfigDict(extra="forbid")

    by_status: dict[str, int]
    by_class: dict[str, int]
    by_connector_resource: list[AdminCortexAmbiguityConnectorRollupItem]


class AdminCortexAmbiguityLifecycleEventItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    event_kind: str
    previous_status: str | None = None
    new_status: str
    payload: dict[str, Any]
    created_at: datetime | None = None


class AdminCortexAmbiguityRecordItem(BaseModel):
    """Phase 03 Step 7 — one ambiguity receipt (lifecycle_events optional on list)."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    tenant_id: uuid.UUID
    bundle_id: str
    ambiguity_class: str
    scope: str
    record_handle: str | None = None
    raw_record_ids: list[Any]
    rule_ids_involved: list[Any]
    primary_connector: str | None = None
    primary_resource_type: str | None = None
    status: str
    superseded_at: datetime | None = None
    supersession_note: str | None = None
    superseded_by_ambiguity_id: uuid.UUID | None = None
    evidence_payload: dict[str, Any]
    engine_build_ref: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    lifecycle_events: list[AdminCortexAmbiguityLifecycleEventItem] | None = None


class AdminCortexAmbiguityListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ambiguity_runtime_schema_version: int
    tenant_id: str
    aggregates: AdminCortexAmbiguityAggregates
    records: list[AdminCortexAmbiguityRecordItem]


class AdminCortexOpenAmbiguityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle_id: str
    ambiguity_class: str
    scope: str
    raw_record_ids: list[int]
    rule_ids_involved: list[str] | None = None
    record_handle: str | None = None
    evidence_payload: dict[str, Any] | None = None


class AdminCortexOpenAmbiguityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record: AdminCortexAmbiguityRecordItem


class AdminCortexAmbiguityLifecycleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_status: str
    supersession_note: str | None = None
    superseded_by_ambiguity_id: uuid.UUID | None = None


class AdminCortexAmbiguityLifecycleResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record: AdminCortexAmbiguityRecordItem


class AdminCortexOracleExpectedLogicalKeyItem(BaseModel):
    """Expected logical key tuple shape inside an oracle vector."""

    model_config = ConfigDict(extra="forbid")

    canonical_object_kind: str
    tuple_field_names: list[str]
    example_normalized_tuple: list[str]


class AdminCortexOracleVectorItem(BaseModel):
    """Single oracle regression vector (`phase-03-oracle-vectors-doctrine.md`)."""

    model_config = ConfigDict(extra="forbid")

    fixture_id: str
    coverage_tags: list[str]
    raw_snapshot_ref: str
    mapping_bundle_id: str
    mapping_manifest_hash: str
    engine_build_ref: str
    expected_logical_keys: list[AdminCortexOracleExpectedLogicalKeyItem]
    expected_ordering: list[dict[str, Any]]
    expected_ambiguity_records: list[dict[str, Any]]
    expected_provenance_edges: list[dict[str, Any]]
    allowed_divergence_classes: list[str]
    injected_fault: str | None = None


class AdminCortexOracleManifestResponse(BaseModel):
    """Phase 03 Step 3 — oracle manifest inventory + frozen vectors (read-only)."""

    model_config = ConfigDict(extra="forbid")

    oracle_manifest_schema_version: int
    phase: str
    implementation_step: int
    completed_implementation_steps: list[int]
    name: str
    tenant_id: str | None = None
    mapping_bundle_id: str
    mapping_manifest_hash: str
    engine_build_ref: str
    oracle_manifest_doctrine_anchors: list[str]
    coverage_categories_documented: list[str]
    vectors: list[AdminCortexOracleVectorItem]


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


class AdminCortexIdentityContinuityTruth(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    anchor_boundary: dict[str, Any] = Field(default_factory=dict)
    candidate_rows: int = 0
    distinct_candidate_pairs: int = 0
    candidate_inflation_ratio: float | None = None
    candidate_inflation_severity: Literal["ok", "warn", "bad", "unknown"] = "unknown"
    anchors_missing_org_entity_pct: float | None = None
    anchors_missing_severity: Literal["ok", "warn", "bad", "unknown"] = "unknown"
    promotable_by_rule_id: list[dict[str, Any]] = Field(default_factory=list)
    promotion_rule_count_green_min: int = 3
    second_link_type_policy: str = "deferred_until_prod_evidence_ge_100_edges"


class AdminCortexIdentityContinuityInspectorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    surface_kind: str = "identity_continuity_inspector"
    inspector_schema_version: int = 2
    tenant_id: uuid.UUID
    captured_at_utc: str | None = None
    identity_continuity: AdminCortexIdentityContinuityTruth | None = None
    unpromoted_candidates: int = 0


class AdminCortexIdentityContinuityDiagnosisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    surface_kind: str = "identity_continuity_diagnosis"
    diagnosis_schema_version: int = 1
    tenant_id: str
    captured_at_utc: str | None = None
    anchor_count: int = 0
    anchor_counts_by_connector: dict[str, int] = Field(default_factory=dict)
    bucket_diagnosis: dict[str, Any] = Field(default_factory=dict)
    email_bridge_coverage: dict[str, Any] = Field(default_factory=dict)
    anchor_samples_by_connector: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    latest_candidate_batch: dict[str, Any] | None = None
    receipt_links: dict[str, Any] = Field(default_factory=dict)
    repro_command: str | None = None


class AdminCortexIdentityContinuitySearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    surface_kind: str = "identity_continuity_search"
    tenant_id: str
    matches: list[dict[str, Any]] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)


class AdminCortexIdentityContinuityEntityInspectorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    surface_kind: str = "identity_continuity_entity_inspector"
    inspector_schema_version: int = 2
    tenant_id: str
    entity: dict[str, Any] = Field(default_factory=dict)
    continuity_status: dict[str, Any] = Field(default_factory=dict)
    resolved_identities: list[dict[str, Any]] = Field(default_factory=list)
    linked_handles: list[dict[str, Any]] = Field(default_factory=list)
    authoritative_links: list[dict[str, Any]] = Field(default_factory=list)
    candidate_explorer_rows: list[dict[str, Any]] = Field(default_factory=list)
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    promotable_candidates: list[dict[str, Any]] = Field(default_factory=list)
    skipped_candidates: list[dict[str, Any]] = Field(default_factory=list)
    unresolved_candidates: list[dict[str, Any]] = Field(default_factory=list)
    promotion_lineage: list[dict[str, Any]] = Field(default_factory=list)
    candidate_lineage: dict[str, Any] = Field(default_factory=dict)
    continuity_evidence: dict[str, Any] = Field(default_factory=dict)
    evidence_receipts: list[dict[str, Any]] = Field(default_factory=list)
    generation_rejections: list[dict[str, Any]] = Field(default_factory=list)
    generation_rejection_counts: dict[str, Any] = Field(default_factory=dict)
    open_ambiguities: list[dict[str, Any]] = Field(default_factory=list)
    conflicting_identities: list[dict[str, Any]] = Field(default_factory=list)
    duplicate_identities: list[dict[str, Any]] = Field(default_factory=list)
    evidence_summary: dict[str, Any] = Field(default_factory=dict)


class AdminCortexIdentityContinuityEntityEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    surface_kind: str = "identity_continuity_entity_evidence"
    tenant_id: str
    entity_id: str
    anchors_scanned: int = 0
    anchors_related_to_entity: int = 0
    evidence_receipts: list[dict[str, Any]] = Field(default_factory=list)
    generation_rejections: list[dict[str, Any]] = Field(default_factory=list)
    generation_rejection_counts: dict[str, Any] = Field(default_factory=dict)
    continuity_join_reason_catalog: dict[str, Any] = Field(default_factory=dict)


class AdminCortexIdentityContinuityEntityCandidatesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    surface_kind: str = "identity_continuity_entity_candidates"
    tenant_id: str
    entity_id: str
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    candidate_lineage: dict[str, Any] = Field(default_factory=dict)
    promotion_lineage: list[dict[str, Any]] = Field(default_factory=list)


