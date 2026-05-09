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
    enforcement: dict[str, Any] | None = None


class AdminCortexFlushAndRerunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation: str = Field(
        ...,
        description="Must exactly match the server phrase for flush + rerun Cortex pipeline (see admin UI).",
    )
    canonical_batch_limit: int = Field(
        default=500,
        ge=1,
        le=5000,
        description="Batch size for async canonical backlog drain after full ingestion rerun enqueue.",
    )


class AdminCortexFlushAndRerunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    accepted: bool = True
    tenant_id: uuid.UUID
    enqueued_connectors: list[str]
    canonical_backlog_task_id: str | None = None
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

