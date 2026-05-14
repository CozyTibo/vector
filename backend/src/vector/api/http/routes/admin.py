"""Internal admin API — HTTP Basic (ADMIN_PASSWORD). Cross-tenant inspection."""

from __future__ import annotations

import copy
import logging
import uuid
from collections.abc import Callable
from datetime import datetime
from types import SimpleNamespace
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.api.http.admin_deps import require_admin_basic
from vector.api.http.deps import get_db, settings_dep
from vector.contracts.admin import (
    AdminConnectionsResponse,
    AdminConnectorConnectLinkResponse,
    AdminCortexAmbiguityAggregates,
    AdminCortexAmbiguityConnectorRollupItem,
    AdminCortexAmbiguityLifecycleRequest,
    AdminCortexAmbiguityLifecycleResponse,
    AdminCortexAmbiguityListResponse,
    AdminCortexAmbiguityQueueListResponse,
    AdminCortexAmbiguityRecordItem,
    AdminCortexBundleEquivalenceDeclarationCreateRequest,
    AdminCortexBundleEquivalenceDeclarationItem,
    AdminCortexBundleEquivalenceDeclarationListResponse,
    AdminCortexCanonicalCertificationArchiveDetailResponse,
    AdminCortexCanonicalCertificationArchiveItem,
    AdminCortexCanonicalCertificationArchiveRequest,
    AdminCortexCanonicalCertificationArchiveResponse,
    AdminCortexCanonicalCertificationArchivesListResponse,
    AdminCortexCanonicalCertificationPackResponse,
    AdminCortexCanonicalControlPlaneResponse,
    AdminCortexCanonicalCoverageMatrixResponse,
    AdminCortexCanonicalDeterminismRepairRequest,
    AdminCortexCanonicalDeterminismRepairResponse,
    AdminCortexCanonicalFailuresResponse,
    AdminCortexCanonicalKindInvariantsResponse,
    AdminCortexCanonicalOntologyResponse,
    AdminCortexCanonicalQueryRequest,
    AdminCortexCanonicalQueryResponse,
    AdminCortexCanonicalRemediationValidateRequest,
    AdminCortexCanonicalRemediationValidateResponse,
    AdminCortexCanonicalVerificationGateResult,
    AdminCortexCanonicalVerificationRunItem,
    AdminCortexCanonicalVerificationRunRequest,
    AdminCortexCanonicalVerificationRunResponse,
    AdminCortexCanonicalVerificationRunsListResponse,
    AdminCortexConfidenceSummaryResponse,
    AdminCortexConnectorRawRecordItem,
    AdminCortexConnectorRawRecordsResponse,
    AdminCortexFlushAndRerunRequest,
    AdminCortexFlushAndRerunResponse,
    AdminCortexIdentityAnchorItem,
    AdminCortexIdentityAnchorListResponse,
    AdminCortexIdentityBackfillFromAnchorsRequest,
    AdminCortexIdentityBackfillFromAnchorsResponse,
    AdminCortexIdentityBackfillRunItem,
    AdminCortexIdentityBackfillRunsListResponse,
    AdminCortexIdentityControlPlaneResponse,
    AdminCortexIdentityContinuityRebuildRequest,
    AdminCortexIdentityContinuityRebuildResponse,
    AdminCortexIdentityContinuityVerifyResponse,
    AdminCortexIdentityContinuityEvidenceInspectResponse,
    AdminCortexIdentityHandlesExplorerResponse,
    AdminCortexIdentityLegacyCeleryAsyncDispatchResponse,
    AdminCortexIdentityLinkCandidatesRegenerateAsyncRequest,
    AdminCortexIdentityOperatorActionRequest,
    AdminCortexIdentityReadinessEconomicsResponse,
    AdminCortexIdentityWorkerTaskStatusResponse,
    AdminCortexIngestionExhaustCoverageResponse,
    AdminCortexIngestionOverviewResponse,
    AdminCortexIngestionRecentRunItem,
    AdminCortexIngestionRecentRunsResponse,
    AdminCortexIngestionTriggerReplayRequest,
    AdminCortexIngestionTriggerReplayResponse,
    AdminCortexIngestionTriggerSyncRequest,
    AdminCortexIngestionTriggerSyncResponse,
    AdminCortexIngestionVerificationResponse,
    AdminCortexLinkRuleVersionCreateRequest,
    AdminCortexLinkRuleVersionDetailResponse,
    AdminCortexLinkRuleVersionItem,
    AdminCortexLinkRuleVersionListResponse,
    AdminCortexMappingRegistryResponse,
    AdminCortexMaterializeBacklogAsyncRequest,
    AdminCortexMaterializeBacklogAsyncResponse,
    AdminCortexMaterializeBacklogFailureItem,
    AdminCortexMaterializeBacklogRequest,
    AdminCortexMaterializeBacklogResponse,
    AdminCortexMaterializeTransformRequest,
    AdminCortexMaterializeTransformResponse,
    AdminCortexMergeQueueDetailResponse,
    AdminCortexMergeQueueListResponse,
    AdminCortexOpenAmbiguityRequest,
    AdminCortexOpenAmbiguityResponse,
    AdminCortexOracleManifestResponse,
    AdminCortexOrgAmbiguityAppendRequest,
    AdminCortexOrgAmbiguityDetailResponse,
    AdminCortexOrgAmbiguityItem,
    AdminCortexOrgAmbiguityListResponse,
    AdminCortexOrgAmbiguityQueueRowV1,
    AdminCortexOrgEntityItem,
    AdminCortexOrgEntityListResponse,
    AdminCortexOrgFailureCaseItem,
    AdminCortexOrgFailuresResponse,
    AdminCortexOrgGraphProjectionResponse,
    AdminCortexOrgHandleListRowV1,
    AdminCortexOrgIdentityCertificationArchiveDetailResponse,
    AdminCortexOrgIdentityCertificationArchiveItem,
    AdminCortexOrgIdentityCertificationArchiveRequest,
    AdminCortexOrgIdentityCertificationArchiveResponse,
    AdminCortexOrgIdentityCertificationArchivesListResponse,
    AdminCortexOrgIdentityCertificationPackResponse,
    AdminCortexOrgIdentityVerificationRunItem,
    AdminCortexOrgIdentityVerificationRunRequest,
    AdminCortexOrgIdentityVerificationRunResponse,
    AdminCortexOrgIdentityVerificationRunsListResponse,
    AdminCortexOrgLinkCandidateBatchSummary,
    AdminCortexOrgLinkCandidateQueueResponse,
    AdminCortexOrgLinkExplorerRowV1,
    AdminCortexOrgLinkItem,
    AdminCortexOrgLinkListResponse,
    AdminCortexOrgLinkReplayJobDetailResponse,
    AdminCortexOrgLinkReplayJobEnqueueRequest,
    AdminCortexOrgLinkReplayJobEnqueueResponse,
    AdminCortexOrgLinkReplayJobItem,
    AdminCortexOrgLinkReplayJobListResponse,
    AdminCortexOrgLinkReplayJobReceiptItem,
    AdminCortexOrgLinkReplayJobRunRequest,
    AdminCortexOrgLinkTemporalStripItem,
    AdminCortexOrgLinkTemporalTimelineResponse,
    AdminCortexOrgMergeCreateRequest,
    AdminCortexOrgMergeItem,
    AdminCortexOrgMergeListResponse,
    AdminCortexOrgPrimitiveInstanceAppendRequest,
    AdminCortexOrgPrimitiveInstanceDetailResponse,
    AdminCortexOrgPrimitiveInstanceItem,
    AdminCortexOrgPrimitiveInstanceListResponse,
    AdminCortexOrgPrimitiveListRowV1,
    AdminCortexOrgProjectionPreviewResponse,
    AdminCortexOrgRemediationValidateRequest,
    AdminCortexOrgRemediationValidateResponse,
    AdminCortexOrgRemediationValidationItem,
    AdminCortexPrimitiveExplorerListResponse,
    AdminCortexProvenanceByMaterializationResponse,
    AdminCortexProvenanceByRawResponse,
    AdminCortexProvenanceRecordItem,
    AdminCortexRawIngestionResourceStat,
    AdminCortexRawIngestionStatsResponse,
    AdminCortexRawMemoryControlPlaneResponse,
    AdminCortexRawMemoryFailuresResponse,
    AdminCortexRawMemoryPhaseClosureResponse,
    AdminCortexRawMemoryQueryRequest,
    AdminCortexRawMemoryQueryResponse,
    AdminCortexRawMemoryRecoveryValidateRequest,
    AdminCortexRawMemoryRecoveryValidateResponse,
    AdminCortexRawMemoryRetentionApplyRequest,
    AdminCortexRawMemoryRetentionApplyResponse,
    AdminCortexRawMemoryTrustStateResponse,
    AdminCortexReplayJobDetailResponse,
    AdminCortexReplayJobItem,
    AdminCortexReplayJobListResponse,
    AdminCortexReplayJobReceiptItem,
    AdminCortexReplayJobRunRequest,
    AdminCortexSchedulerPauseRequest,
    AdminCortexSchedulerPauseResponse,
    AdminCortexStabilizationProofRunItem,
    AdminCortexStabilizationProofRunRequest,
    AdminCortexStabilizationProofRunResponse,
    AdminCortexStabilizationProofRunsListResponse,
    AdminCortexTemporalRebuildPreviewRequest,
    AdminCortexTemporalRebuildPreviewResponse,
    AdminCortexTemporalRebuildPreviewRow,
    AdminCortexTemporalSupersessionItem,
    AdminCortexTemporalSupersessionsListResponse,
    AdminCortexTransformLineageListResponse,
    AdminHardDeleteOrphanUserRequest,
    AdminHardDeleteOrphanUserResponse,
    AdminHardDeleteTenantRequest,
    AdminHardDeleteTenantResponse,
    AdminHardDeleteTenantsBulkRequest,
    AdminHardDeleteTenantsBulkResponse,
    AdminOnboardingAnswerOptionsResponse,
    AdminOnboardingCollectedDataPatch,
    AdminResetTenantToSignupRequest,
    AdminResetTenantToSignupResponse,
    AdminTenantPrimaryMemberFullNamePatchRequest,
    AdminTenantSlackDeliveryRequest,
    AdminTenantWorkspaceAccessRequest,
    AdminToolOptionItem,
    AdminUserListItem,
    AdminUserListResponse,
    CortexIngestionConnectorId,
    OnboardingAdminSnapshot,
    OnboardingChatMessageItem,
    SlackCollaboratorMemberSnapshot,
    SlackCollaboratorsSnapshot,
    SlackStakeholdersSnapshot,
    SlackWatchChannelSnapshot,
    SlackWatchChannelsSnapshot,
    TenantAdminDetailResponse,
    TenantConnectionAdminItem,
    TenantListItem,
    TenantListResponse,
)
from vector.contracts.onboarding import OnboardingCompleteResponse
from vector.domains.cortex.connectors.calls.errors import CallsConnectorNotConfiguredError
from vector.domains.cortex.connectors.calls.oauth_flow import start_calls_oauth_url
from vector.domains.cortex.connectors.cortex_ingestion_policy import (
    extract_tenant_id_from_enqueue_args,
    should_route_ingestion_to_cortex,
)
from vector.domains.cortex.connectors.github.errors import GitHubConnectorNotConfiguredError
from vector.domains.cortex.connectors.github.install_flow import start_github_install_url
from vector.domains.cortex.connectors.linear.errors import LinearConnectorNotConfiguredError
from vector.domains.cortex.connectors.linear.oauth_flow import start_linear_oauth_url
from vector.domains.cortex.connectors.notion.errors import NotionConnectorNotConfiguredError
from vector.domains.cortex.connectors.notion.oauth_flow import start_notion_oauth_url
from vector.domains.cortex.connectors.runtime import runtime_by_id
from vector.domains.cortex.connectors.slack.errors import SlackConnectorNotConfiguredError
from vector.domains.cortex.connectors.slack.oauth_flow import start_slack_oauth_url
from vector.domains.cortex.ingestion.admin_overview import build_cortex_ingestion_admin_overview
from vector.domains.cortex.ingestion.admin_recent_raw import (
    aggregate_raw_ingestion_stats,
    build_connector_raw_rollups,
    list_raw_records_for_connector,
    list_recent_ingestion_runs,
)
from vector.domains.cortex.ingestion.full_pipeline_reset import flush_tenant_cortex_pipeline_state
from vector.domains.cortex.ingestion.raw_memory_control_plane import build_raw_memory_control_plane
from vector.domains.cortex.ingestion.raw_memory_enforcement import evaluate_progressive_enforcement
from vector.domains.cortex.ingestion.raw_memory_failure_recovery import (
    run_raw_memory_recovery_validation,
    sync_raw_memory_failure_cases,
)
from vector.domains.cortex.ingestion.raw_memory_query import execute_raw_memory_query
from vector.domains.cortex.ingestion.raw_memory_storage import apply_raw_memory_retention_policy
from vector.domains.cortex.ingestion.raw_memory_trust import (
    build_raw_memory_trust_annotation,
    persist_raw_memory_trust_annotation,
)
from vector.domains.onboarding.constants import (
    ONBOARDING_ALL_TOOL_IDS,
    ONBOARDING_PROFILE_ROLE_CANONICAL,
    ONBOARDING_PROFILE_ROLE_VALUES,
    ONBOARDING_TOOL_OPTIONS,
    PROFILE_ROLE_OTHER,
    TOOL_CATEGORY_KEYS,
    onboarding_tool_ids_for_category,
)
from vector.domains.onboarding.onboarding_commands import (
    dev_force_complete_website_onboarding_for_tenant,
)
from vector.domains.tenancy.hard_delete_orphan_user import (
    HARD_DELETE_ORPHAN_USER_CONFIRMATION_PHRASE,
    hard_delete_orphan_user,
)
from vector.domains.tenancy.hard_delete_tenant import (
    HARD_DELETE_TENANT_CONFIRMATION_PHRASE,
    hard_delete_tenant,
)
from vector.domains.tenancy.reset_tenant_to_fresh_signup import (
    RESET_TENANT_TO_SIGNUP_CONFIRMATION_PHRASE,
    reset_tenant_to_fresh_signup,
)
from vector.infrastructure.db.models.onboarding_state import OnboardingState
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.repositories import onboarding as onboarding_repo
from vector.infrastructure.db.repositories import tenancy as tenancy_repo
from vector.infrastructure.email.onboarding_activation import (
    enqueue_onboarding_activation_email,
    onboarding_entry_url,
)
from vector.infrastructure.observability.ingestion_tasks import PHASE_STEP6, log_ingestion_event
from vector.settings import Settings, get_settings

_logger = logging.getLogger("app")

CORTEX_SCHEDULER_PAUSE_CONFIRM_PHRASE = "PAUSE ALL SCHEDULED CORTEX INGESTION"
CORTEX_SCHEDULER_RESUME_CONFIRM_PHRASE = "RESUME ALL SCHEDULED CORTEX INGESTION"
CORTEX_RAW_MEMORY_DELETE_CONFIRM_PHRASE = "APPLY RAW MEMORY RETENTION DELETION"
CORTEX_MANUAL_SYNC_CONFIRM_PHRASE = "RUN MANUAL CORTEX INGESTION SYNC"
CORTEX_REPLAY_CONFIRM_PHRASE = "RUN CORTEX INGESTION REPLAY JOB"
CORTEX_FLUSH_RERUN_CONFIRM_PHRASE = "FLUSH RAW DATA AND RERUN CORTEX TO IDENTITY"


def _enqueue_cortex_poll_sync(connector_id: str) -> Callable[..., None]:
    """Enqueue Phase 01 Celery sync when flags route this connector×tenant to Cortex."""

    def _fn(*args: object, **kwargs: object) -> None:
        settings = get_settings()
        tenant_id = extract_tenant_id_from_enqueue_args(args, kwargs)
        if tenant_id is None:
            raise RuntimeError(
                "tenant_id is required to enqueue connector poll sync "
                "(pass a positional UUID or tenant_id= keyword).",
            )
        if should_route_ingestion_to_cortex(settings, connector_id, tenant_id):
            from app.tasks.cortex_ingestion_sync import run_cortex_connector_sync_task

            run_cortex_connector_sync_task.delay(str(tenant_id), connector_id, "manual")
            return
        raise RuntimeError(
            "Connector poll ingestion is unavailable for tenants not routed to Cortex "
            "(Cortex ingestion is disabled for this connector×tenant in configuration).",
        )

    return _fn


def _enqueue_cortex_replay_sync(connector_id: str) -> Callable[..., uuid.UUID]:
    """Enqueue Phase 01 replay Celery task (cortex_replay queue) when flags route to Cortex."""

    def _fn(*args: object, **kwargs: object) -> uuid.UUID:
        settings = get_settings()
        tenant_id = extract_tenant_id_from_enqueue_args(args, kwargs)
        if tenant_id is None:
            raise RuntimeError(
                "tenant_id is required to enqueue connector replay sync "
                "(pass a positional UUID or tenant_id= keyword).",
            )
        if not should_route_ingestion_to_cortex(settings, connector_id, tenant_id):
            raise RuntimeError(
                "Connector replay ingestion is unavailable for tenants not routed to Cortex "
                "(Cortex ingestion is disabled for this connector×tenant in configuration).",
            )
        raw_job = kwargs.get("replay_job_id")
        job_id = uuid.UUID(str(raw_job)) if raw_job is not None else uuid.uuid4()
        from app.tasks.cortex_ingestion_sync import run_cortex_connector_replay_sync_task

        rv_obj = kwargs.get("replay_version", 1)
        if isinstance(rv_obj, int):
            replay_version = rv_obj
        elif isinstance(rv_obj, str) and rv_obj.strip().isdigit():
            replay_version = int(rv_obj)
        else:
            replay_version = 1
        run_cortex_connector_replay_sync_task.delay(
            str(tenant_id),
            connector_id,
            str(job_id),
            replay_version,
            "manual_replay",
        )
        return job_id

    return _fn


def _verify_cortex_ingestion_invariants() -> Callable[..., dict[str, Any]]:
    """Run Step 5 read-only invariant sweep for a tenant (uses ``session_scope``)."""

    def _fn(*args: object, **kwargs: object) -> dict[str, Any]:
        tenant_id = extract_tenant_id_from_enqueue_args(args, kwargs)
        if tenant_id is None:
            raise RuntimeError(
                "tenant_id is required to verify Cortex ingestion invariants "
                "(pass tenant_id= keyword or a positional UUID).",
            )
        from vector.domains.cortex.ingestion.verification import verify_tenant_ingestion_invariants
        from vector.infrastructure.db.session import session_scope
        settings = get_settings()

        rl = kwargs.get("run_limit", 30)
        run_limit = rl if isinstance(rl, int) else 30
        with session_scope() as session:
            return verify_tenant_ingestion_invariants(
                session,
                tenant_id,
                run_limit=run_limit,
                enforcement_mode=settings.cortex_raw_memory_enforcement_mode,
            )

    return _fn


# Backward-compat shim for tests/patch targets that still reference
# `vector.api.http.routes.admin.connector_sync`.
connector_sync = SimpleNamespace(
    enqueue_calls_poll_sync=_enqueue_cortex_poll_sync("calls"),
    enqueue_github_poll_sync=_enqueue_cortex_poll_sync("github"),
    enqueue_linear_poll_sync=_enqueue_cortex_poll_sync("linear"),
    enqueue_notion_poll_sync=_enqueue_cortex_poll_sync("notion"),
    enqueue_slack_poll_sync=_enqueue_cortex_poll_sync("slack"),
    enqueue_calls_replay_sync=_enqueue_cortex_replay_sync("calls"),
    enqueue_github_replay_sync=_enqueue_cortex_replay_sync("github"),
    enqueue_linear_replay_sync=_enqueue_cortex_replay_sync("linear"),
    enqueue_notion_replay_sync=_enqueue_cortex_replay_sync("notion"),
    enqueue_slack_replay_sync=_enqueue_cortex_replay_sync("slack"),
    verify_ingestion_invariants=_verify_cortex_ingestion_invariants(),
)


def _admin_reset_tenant_to_signup_response(out: dict[str, Any]) -> AdminResetTenantToSignupResponse:
    s3 = out["step3"]
    s2 = out["step2"]
    s1 = out["step1"]
    return AdminResetTenantToSignupResponse(
        tenant_id=out["tenant_id"],
        company_name=out["company_name"],
        deleted_relationships=s3["deleted_relationships"],
        deleted_mapping_events=s3["deleted_mapping_events"],
        deleted_current_mappings=s3["deleted_current_mappings"],
        deleted_external_references=s3["deleted_external_references"],
        deleted_actor_external_identities=s3["deleted_actor_external_identities"],
        deleted_artifacts=s3["deleted_artifacts"],
        deleted_actors=s3["deleted_actors"],
        deleted_step3_canonical_cursors=s3["deleted_step3_canonical_cursors"],
        deleted_github_projection_rows=s2["deleted_github_projection_rows"],
        deleted_linear_projection_rows=s2["deleted_linear_projection_rows"],
        deleted_connector_projection_progress_rows=s2["deleted_connector_projection_progress_rows"],
        deleted_raw_records=s1["deleted_raw_records"],
        deleted_ingestion_runs=s1["deleted_ingestion_runs"],
        deleted_sync_state_rows=s1["deleted_sync_state_rows"],
        deleted_tenant_connections=out["deleted_tenant_connections"],
    )


def _admin_hard_delete_tenant_response(tenant_id: uuid.UUID, out: dict[str, Any]) -> AdminHardDeleteTenantResponse:
    s3 = out["step3"]
    s2 = out["step2"]
    s1 = out["step1"]
    return AdminHardDeleteTenantResponse(
        deleted_tenant_id=tenant_id,
        deleted_company_name=out["deleted_company_name"],
        deleted_relationships=s3["deleted_relationships"],
        deleted_mapping_events=s3["deleted_mapping_events"],
        deleted_current_mappings=s3["deleted_current_mappings"],
        deleted_external_references=s3["deleted_external_references"],
        deleted_actor_external_identities=s3["deleted_actor_external_identities"],
        deleted_artifacts=s3["deleted_artifacts"],
        deleted_actors=s3["deleted_actors"],
        deleted_step3_canonical_cursors=s3["deleted_step3_canonical_cursors"],
        deleted_github_projection_rows=s2["deleted_github_projection_rows"],
        deleted_linear_projection_rows=s2["deleted_linear_projection_rows"],
        deleted_connector_projection_progress_rows=s2["deleted_connector_projection_progress_rows"],
        deleted_raw_records=s1["deleted_raw_records"],
        deleted_ingestion_runs=s1["deleted_ingestion_runs"],
        deleted_sync_state_rows=s1["deleted_sync_state_rows"],
    )


def _tools_interest(ans: dict[str, object]) -> list[str]:
    raw = ans.get("tools_interest")
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw if x is not None]


def _company_domain(ans: dict[str, object]) -> str | None:
    raw = ans.get("company_domain")
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    return s or None


def _tools_stack(ans: dict[str, object]) -> dict[str, Any] | None:
    raw = ans.get("tools_stack")
    if not isinstance(raw, dict):
        return None
    return dict(raw)


def _profile_phase(ans: dict[str, object]) -> str | None:
    raw = ans.get("profile_phase")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _profile_role(ans: dict[str, object]) -> str | None:
    prof = ans.get("profile")
    if isinstance(prof, dict):
        r = prof.get("role")
        if isinstance(r, str) and r.strip():
            return r.strip()
    return None


def _company_size(ans: dict[str, object]) -> str | None:
    comp = ans.get("company")
    if isinstance(comp, dict):
        s = comp.get("size")
        if isinstance(s, str) and s.strip():
            return s.strip()
    return None


def _company_website(ans: dict[str, object]) -> str | None:
    comp = ans.get("company")
    if isinstance(comp, dict):
        w = comp.get("website")
        if isinstance(w, str) and w.strip():
            return w.strip()
    return _company_domain(ans)


def _tools_category(ans: dict[str, object], key: str) -> list[str]:
    raw = ans.get("tools")
    if not isinstance(raw, dict):
        return []
    v = raw.get(key)
    if not isinstance(v, list):
        return []
    return [str(x) for x in v if isinstance(x, str)]


def _slack_stakeholders_from_answers(ans: dict[str, object]) -> SlackStakeholdersSnapshot | None:
    raw = ans.get("slack_stakeholders")
    if not isinstance(raw, dict):
        return None
    rt = raw.get("raw_text")
    ids = raw.get("slack_user_ids")
    text_out: str | None = None
    if isinstance(rt, str):
        s = rt.strip()
        text_out = s if s else None
    uid_list: list[str] = []
    if isinstance(ids, list):
        uid_list = list(dict.fromkeys(str(x) for x in ids if isinstance(x, str)))
    if text_out is None and not uid_list:
        return None
    return SlackStakeholdersSnapshot(raw_text=text_out, slack_user_ids=uid_list)


def _slack_collaborators_from_answers(ans: dict[str, object]) -> SlackCollaboratorsSnapshot | None:
    raw = ans.get("slack_collaborators")
    if not isinstance(raw, dict):
        return None
    members_raw = raw.get("members")
    if not isinstance(members_raw, list) or not members_raw:
        return None
    rows: list[SlackCollaboratorMemberSnapshot] = []
    seen: set[str] = set()
    for m in members_raw:
        if not isinstance(m, dict):
            continue
        uid = m.get("slack_user_id")
        if not isinstance(uid, str) or not uid.strip():
            continue
        uid = uid.strip()
        if uid in seen:
            continue
        seen.add(uid)
        un = m.get("username")
        username = un.strip().lstrip("@") if isinstance(un, str) and un.strip() else uid
        lab = m.get("label")
        label = lab.strip() if isinstance(lab, str) and lab.strip() else username
        rows.append(
            SlackCollaboratorMemberSnapshot(
                slack_user_id=uid,
                username=username,
                label=label,
            )
        )
    if not rows:
        return None
    return SlackCollaboratorsSnapshot(members=rows)


def _slack_team_members_from_answers(ans: dict[str, object]) -> SlackCollaboratorsSnapshot | None:
    raw = ans.get("slack_team_members")
    if not isinstance(raw, dict):
        return None
    members_raw = raw.get("members")
    if not isinstance(members_raw, list) or not members_raw:
        return None
    rows: list[SlackCollaboratorMemberSnapshot] = []
    seen: set[str] = set()
    for m in members_raw:
        if not isinstance(m, dict):
            continue
        uid = m.get("slack_user_id")
        if not isinstance(uid, str) or not uid.strip():
            continue
        uid = uid.strip()
        if uid in seen:
            continue
        seen.add(uid)
        un = m.get("username")
        username = un.strip().lstrip("@") if isinstance(un, str) and un.strip() else uid
        lab = m.get("label")
        label = lab.strip() if isinstance(lab, str) and lab.strip() else username
        rows.append(
            SlackCollaboratorMemberSnapshot(
                slack_user_id=uid,
                username=username,
                label=label,
            )
        )
    if not rows:
        return None
    return SlackCollaboratorsSnapshot(members=rows)


def _slack_introduce_managers_consent_from_answers(ans: dict[str, object]) -> str | None:
    raw = ans.get("slack_introduce_managers_consent")
    if isinstance(raw, str) and raw.strip() in ("yes", "later", "not_applicable"):
        return raw.strip().lower()
    return None


def _slack_watch_channels_from_answers(ans: dict[str, object]) -> SlackWatchChannelsSnapshot | None:
    raw = ans.get("slack_watch_channels")
    if not isinstance(raw, dict):
        return None
    ch_raw = raw.get("channels")
    if not isinstance(ch_raw, list) or not ch_raw:
        return None
    out: list[SlackWatchChannelSnapshot] = []
    seen: set[str] = set()
    for ch in ch_raw:
        if not isinstance(ch, dict):
            continue
        cid = ch.get("channel_id")
        if not isinstance(cid, str) or not cid.strip():
            continue
        cid = cid.strip()
        if cid in seen:
            continue
        seen.add(cid)
        nm = ch.get("name")
        name = nm.strip().lstrip("#") if isinstance(nm, str) and nm.strip() else cid
        out.append(SlackWatchChannelSnapshot(channel_id=cid, name=name))
    if not out:
        return None
    return SlackWatchChannelsSnapshot(channels=out)


def _connect_queue_plan_snapshot(ans: dict[str, object]) -> tuple[list[str], list[str]]:
    def _coerce_str_list(key: str) -> list[str]:
        raw = ans.get(key)
        if not isinstance(raw, list):
            return []
        return [str(x) for x in raw if isinstance(x, str)]

    return _coerce_str_list("connect_queue"), _coerce_str_list("connect_plan")


def _snapshot_from_onboarding(
    session: Session, row: OnboardingState | None
) -> OnboardingAdminSnapshot | None:
    if row is None:
        return None
    ans = dict(row.answers_json or {})
    cq, cp = _connect_queue_plan_snapshot(ans)
    msgs: list[OnboardingChatMessageItem] = []
    if onboarding_repo.onboarding_messages_table_exists(session):
        # Full transcript from the start, in DB order (created_at, id). Avoid "recent 200 DESC then
        # sort", which drops early turns; tie-break id matches flush order within the same timestamp.
        raw_rows = onboarding_repo.list_onboarding_messages_chronological(
            session, row.tenant_id, limit=2000
        )
        for m in raw_rows:
            msgs.append(
                OnboardingChatMessageItem(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    created_at=m.created_at,
                )
            )
    return OnboardingAdminSnapshot(
        status=row.status,
        current_step=row.current_step,
        started_at=row.started_at,
        completed_at=row.completed_at,
        abandoned_at=row.abandoned_at,
        profile_phase=_profile_phase(ans),
        connect_queue=cq,
        connect_plan=cp,
        tools_interest=_tools_interest(ans),
        company_domain=_company_domain(ans),
        company_website=_company_website(ans),
        company_size=_company_size(ans),
        user_role=_profile_role(ans),
        tools_engineering=_tools_category(ans, "engineering"),
        tools_pm=_tools_category(ans, "pm"),
        tools_communication=_tools_category(ans, "communication"),
        tools_calls=_tools_category(ans, "calls"),
        tools_calendars=_tools_category(ans, "calendars"),
        tools_docs=_tools_category(ans, "docs"),
        tools_stack=_tools_stack(ans),
        slack_stakeholders=_slack_stakeholders_from_answers(ans),
        slack_collaborators=_slack_collaborators_from_answers(ans),
        slack_team_members=_slack_team_members_from_answers(ans),
        slack_watch_channels=_slack_watch_channels_from_answers(ans),
        slack_introduce_managers_consent=_slack_introduce_managers_consent_from_answers(ans),
        chat_messages=msgs,
    )


def _coerce_str_list(v: object) -> list[str]:
    if not isinstance(v, list):
        return []
    return [str(x).strip() for x in v if str(x).strip()]


def _apply_admin_onboarding_collected_patch(
    existing: dict[str, Any],
    patch: dict[str, Any],
) -> dict[str, Any]:
    """Merge admin edits into ``answers_json`` (profile/company/tools only; no FSM fields)."""
    out: dict[str, Any] = copy.deepcopy(existing) if existing else {}

    if "user_role" in patch:
        val = patch["user_role"]
        prof = dict(out["profile"]) if isinstance(out.get("profile"), dict) else {}
        if isinstance(val, str) and val.strip():
            prof["role"] = val.strip()
        else:
            prof.pop("role", None)
        if prof:
            out["profile"] = prof
        else:
            out.pop("profile", None)

    if "company_website" in patch or "company_size" in patch:
        comp = dict(out["company"]) if isinstance(out.get("company"), dict) else {}
        if "company_website" in patch:
            w = patch["company_website"]
            if isinstance(w, str) and w.strip():
                comp["website"] = w.strip()
            else:
                comp.pop("website", None)
        if "company_size" in patch:
            s = patch["company_size"]
            if isinstance(s, str) and s.strip():
                comp["size"] = s.strip()
            else:
                comp.pop("size", None)
        if comp:
            out["company"] = comp
        else:
            out.pop("company", None)

    if "company_domain" in patch:
        d = patch["company_domain"]
        if isinstance(d, str) and d.strip():
            out["company_domain"] = d.strip()
        else:
            out.pop("company_domain", None)

    if "tools_interest" in patch:
        out["tools_interest"] = _coerce_str_list(patch["tools_interest"])

    tool_cat_keys = (
        ("tools_engineering", "engineering"),
        ("tools_pm", "pm"),
        ("tools_communication", "communication"),
        ("tools_calls", "calls"),
        ("tools_calendars", "calendars"),
        ("tools_docs", "docs"),
    )
    if any(pk in patch for pk, _ in tool_cat_keys):
        tools = dict(out["tools"]) if isinstance(out.get("tools"), dict) else {}
        for patch_key, cat in tool_cat_keys:
            if patch_key in patch:
                tools[cat] = _coerce_str_list(patch[patch_key])
        out["tools"] = tools

    return out


def _build_admin_onboarding_answer_options() -> AdminOnboardingAnswerOptionsResponse:
    roles = list(ONBOARDING_PROFILE_ROLE_CANONICAL) + [PROFILE_ROLE_OTHER]
    by_cat: dict[str, list[AdminToolOptionItem]] = {c: [] for c in sorted(TOOL_CATEGORY_KEYS)}
    for cat, tid, label in ONBOARDING_TOOL_OPTIONS:
        by_cat.setdefault(cat, []).append(AdminToolOptionItem(id=tid, label=label))
    return AdminOnboardingAnswerOptionsResponse(
        profile_roles=roles,
        tools_by_category=by_cat,
    )


def _validate_admin_onboarding_collected_patch(patch: dict[str, Any]) -> None:
    if "user_role" in patch:
        v = patch["user_role"]
        if v is not None and (
            not isinstance(v, str) or (v.strip() and v.strip() not in ONBOARDING_PROFILE_ROLE_VALUES)
        ):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="user_role must be empty/null or one of the known profile roles.",
            ) from None
    tool_patch_keys: tuple[tuple[str, str], ...] = (
        ("tools_engineering", "engineering"),
        ("tools_pm", "pm"),
        ("tools_communication", "communication"),
        ("tools_calls", "calls"),
        ("tools_calendars", "calendars"),
        ("tools_docs", "docs"),
    )
    for patch_key, cat in tool_patch_keys:
        if patch_key not in patch:
            continue
        ids = patch[patch_key]
        if not isinstance(ids, list):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"{patch_key} must be a JSON array of tool ids.",
            ) from None
        allowed = onboarding_tool_ids_for_category(cat)
        for i in ids:
            if not isinstance(i, str):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tool id for {patch_key}: {i!r}",
                ) from None
            if i.strip() not in allowed:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tool id for {patch_key}: {i!r}",
                ) from None
    if "tools_interest" in patch:
        ti = patch["tools_interest"]
        if not isinstance(ti, list):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="tools_interest must be a JSON array of tool ids.",
            ) from None
        for i in ti:
            if not isinstance(i, str):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tools_interest id: {i!r}",
                ) from None
            if i.strip() not in ONBOARDING_ALL_TOOL_IDS:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tools_interest id: {i!r}",
                ) from None


def _assert_tenant(session: Session, tenant_id: uuid.UUID) -> None:
    if tenancy_repo.get_tenant_by_id(session, tenant_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found.") from None


def _active_cortex_routed_connection(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    connector_id: str,
    connection_id: uuid.UUID | None = None,
) -> TenantConnection:
    stmt = (
        select(TenantConnection)
        .where(
            TenantConnection.tenant_id == tenant_id,
            TenantConnection.provider == connector_id,
            TenantConnection.status == "active",
        )
        .order_by(TenantConnection.created_at.desc(), TenantConnection.id.desc())
    )
    rows = list(session.scalars(stmt).all())
    if connection_id is not None:
        tc = next((x for x in rows if x.id == connection_id), None)
        if tc is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Active {connector_id} connection {connection_id} not found for this tenant.",
            ) from None
    elif len(rows) > 1:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=(
                f"Multiple active {connector_id} connections found for this tenant. "
                "Specify connection_id explicitly to avoid ambiguous ingestion scope."
            ),
        ) from None
    else:
        tc = rows[0] if rows else None

    if tc is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"No active {connector_id} connection for this tenant.",
        ) from None

    if not should_route_ingestion_to_cortex(settings, connector_id, tenant_id):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=(
                "This connector is not routed to Cortex ingestion for this tenant "
                "(Cortex ingestion is disabled for this connector in configuration)."
            ),
        ) from None
    return tc


def _list_tenant_connections(session: Session, tenant_id: uuid.UUID) -> list[TenantConnection]:
    stmt = (
        select(TenantConnection)
        .where(TenantConnection.tenant_id == tenant_id)
        .order_by(TenantConnection.provider.asc(), TenantConnection.created_at.desc())
    )
    return list(session.scalars(stmt).all())


def build_admin_router() -> APIRouter:
    r = APIRouter(
        prefix="/admin",
        tags=["admin"],
        dependencies=[Depends(require_admin_basic)],
    )

    @r.get("/meta/onboarding-answer-options", response_model=AdminOnboardingAnswerOptionsResponse)
    def get_admin_onboarding_answer_options() -> AdminOnboardingAnswerOptionsResponse:
        return _build_admin_onboarding_answer_options()

    @r.get("/tenants", response_model=TenantListResponse)
    def list_tenants(
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=500)] = 200,
    ) -> TenantListResponse:
        rows = tenancy_repo.list_all_tenants(db, limit=limit)
        t_ids = [t.id for t in rows]
        ob_map = onboarding_repo.list_onboarding_for_tenants(db, t_ids)
        items: list[TenantListItem] = []
        for t in rows:
            ob = ob_map.get(t.id)
            conns = _list_tenant_connections(db, tenant_id=t.id)
            items.append(
                TenantListItem(
                    id=t.id,
                    company_name=t.company_name,
                    created_at=t.created_at,
                    workspace_access_enabled=bool(t.workspace_access_enabled),
                    onboarding_status=ob.status if ob else None,
                    onboarding_current_step=ob.current_step if ob else None,
                    connected_connectors=[c.provider for c in conns],
                ),
            )
        return TenantListResponse(items=items)

    @r.get("/users", response_model=AdminUserListResponse)
    def list_users(
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=500)] = 500,
    ) -> AdminUserListResponse:
        rows = tenancy_repo.list_all_users(db, limit=limit)
        u_ids = [u.id for u in rows]
        m_counts = tenancy_repo.membership_counts_for_user_ids(db, u_ids)
        c_counts = tenancy_repo.tenant_connection_counts_for_connected_user_ids(db, u_ids)
        items: list[AdminUserListItem] = []
        for u in rows:
            mc = m_counts.get(u.id, 0)
            cc = c_counts.get(u.id, 0)
            items.append(
                AdminUserListItem(
                    id=u.id,
                    email=u.email,
                    full_name=u.full_name,
                    created_at=u.created_at,
                    has_password=u.password_hash is not None,
                    membership_count=mc,
                    tenant_connections_as_connector_count=cc,
                    orphan_eligible=mc == 0 and cc == 0,
                ),
            )
        return AdminUserListResponse(items=items)

    @r.post(
        "/tenants/{tenant_id}/hard-delete",
        response_model=AdminHardDeleteTenantResponse,
    )
    def admin_hard_delete_tenant(
        tenant_id: uuid.UUID,
        body: AdminHardDeleteTenantRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminHardDeleteTenantResponse:
        """Hard-delete tenant and all tenant-scoped product data.

        Users are kept; memberships for this tenant are removed via FK cascade.
        """
        t = tenancy_repo.get_tenant_by_id(db, tenant_id)
        if t is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found.") from None
        if body.confirmation != HARD_DELETE_TENANT_CONFIRMATION_PHRASE:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Confirmation phrase does not match.",
            ) from None
        if t.company_name.strip() != body.company_name_confirmation.strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Company name does not match this tenant.",
            ) from None
        try:
            out = hard_delete_tenant(db, tenant_id=tenant_id)
        except ValueError as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e)) from e
        db.commit()
        return _admin_hard_delete_tenant_response(tenant_id, out)

    @r.post(
        "/tenants/{tenant_id}/reset-to-fresh-signup",
        response_model=AdminResetTenantToSignupResponse,
    )
    def admin_reset_tenant_to_fresh_signup(
        tenant_id: uuid.UUID,
        body: AdminResetTenantToSignupRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminResetTenantToSignupResponse:
        """Wipe tenant product data and integrations; keep tenant row and memberships (day-one signup)."""
        t = tenancy_repo.get_tenant_by_id(db, tenant_id)
        if t is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found.") from None
        if body.confirmation != RESET_TENANT_TO_SIGNUP_CONFIRMATION_PHRASE:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Confirmation phrase does not match.",
            ) from None
        if t.company_name.strip() != body.company_name_confirmation.strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Company name does not match this tenant.",
            ) from None
        try:
            out = reset_tenant_to_fresh_signup(db, tenant_id=tenant_id)
        except ValueError as e:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e)) from e
        db.commit()
        return _admin_reset_tenant_to_signup_response(out)

    @r.post(
        "/tenants/hard-delete-bulk",
        response_model=AdminHardDeleteTenantsBulkResponse,
    )
    def admin_hard_delete_tenants_bulk(
        body: AdminHardDeleteTenantsBulkRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminHardDeleteTenantsBulkResponse:
        """Hard-delete many tenants in one transaction (same checks as single delete)."""
        if body.confirmation != HARD_DELETE_TENANT_CONFIRMATION_PHRASE:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Confirmation phrase does not match.",
            ) from None
        seen: set[uuid.UUID] = set()
        for item in body.tenants:
            if item.tenant_id in seen:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail="Duplicate tenant_id in request.",
                ) from None
            seen.add(item.tenant_id)

        results: list[AdminHardDeleteTenantResponse] = []
        try:
            for item in body.tenants:
                t = tenancy_repo.get_tenant_by_id(db, item.tenant_id)
                if t is None:
                    raise HTTPException(
                        status.HTTP_404_NOT_FOUND,
                        detail=f"Tenant not found: {item.tenant_id}",
                    ) from None
                if t.company_name.strip() != item.company_name_confirmation.strip():
                    raise HTTPException(
                        status.HTTP_400_BAD_REQUEST,
                        detail=f"Company name does not match tenant {item.tenant_id}.",
                    ) from None
                out = hard_delete_tenant(db, tenant_id=item.tenant_id)
                results.append(_admin_hard_delete_tenant_response(item.tenant_id, out))
            db.commit()
        except HTTPException:
            db.rollback()
            raise
        except ValueError as e:
            db.rollback()
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e)) from e
        except Exception:
            db.rollback()
            raise
        return AdminHardDeleteTenantsBulkResponse(results=results)

    @r.post(
        "/users/{user_id}/hard-delete",
        response_model=AdminHardDeleteOrphanUserResponse,
    )
    def admin_hard_delete_orphan_user(
        user_id: uuid.UUID,
        body: AdminHardDeleteOrphanUserRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminHardDeleteOrphanUserResponse:
        """Delete a user only when they have no memberships and no tenant_connections as connector."""
        u = tenancy_repo.get_user_by_id(db, user_id)
        if u is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found.") from None
        if body.confirmation != HARD_DELETE_ORPHAN_USER_CONFIRMATION_PHRASE:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Confirmation phrase does not match.",
            ) from None
        if u.email.strip() != body.email_confirmation.strip():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Email does not match this user.",
            ) from None
        try:
            deleted_email = hard_delete_orphan_user(db, user_id=user_id)
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        db.commit()
        return AdminHardDeleteOrphanUserResponse(deleted_user_id=user_id, deleted_email=deleted_email)

    @r.get("/tenants/{tenant_id}", response_model=TenantAdminDetailResponse)
    def get_tenant(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> TenantAdminDetailResponse:
        t = tenancy_repo.get_tenant_by_id(db, tenant_id)
        if t is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found.") from None
        ob = onboarding_repo.get_onboarding_for_tenant(db, tenant_id)
        conns = _list_tenant_connections(db, tenant_id=tenant_id)
        member = tenancy_repo.get_first_user_for_tenant(db, tenant_id)
        return TenantAdminDetailResponse(
            id=t.id,
            company_name=t.company_name,
            created_at=t.created_at,
            workspace_access_enabled=bool(t.workspace_access_enabled),
            onboarding=_snapshot_from_onboarding(db, ob),
            member_full_name=member.full_name if member else None,
            member_email=member.email if member else None,
            connected_connectors=[c.provider for c in conns],
            slack_vector_paused=bool(t.slack_vector_paused),
        )

    @r.patch(
        "/tenants/{tenant_id}/onboarding/collected-data",
        response_model=TenantAdminDetailResponse,
    )
    def patch_tenant_onboarding_collected_data(
        tenant_id: uuid.UUID,
        body: AdminOnboardingCollectedDataPatch,
        db: Annotated[Session, Depends(get_db)],
    ) -> TenantAdminDetailResponse:
        """Update onboarding ``answers_json`` fields (user/company/tools); not status or timestamps."""
        _assert_tenant(db, tenant_id)
        row = onboarding_repo.get_onboarding_for_tenant(db, tenant_id)
        if row is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="No onboarding row for this tenant.",
            ) from None
        patch = body.model_dump(exclude_unset=True)
        if not patch:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="No fields to update.",
            ) from None
        _validate_admin_onboarding_collected_patch(patch)
        merged = _apply_admin_onboarding_collected_patch(dict(row.answers_json or {}), patch)
        onboarding_repo.normalize_slack_stakeholders_in_place(merged)
        onboarding_repo.normalize_slack_collaborators_in_place(merged)
        onboarding_repo.normalize_slack_team_members_in_place(merged)
        onboarding_repo.normalize_slack_watch_channels_in_place(merged)
        row.answers_json = merged
        row.version = int(row.version) + 1
        db.commit()
        db.refresh(row)
        t = tenancy_repo.get_tenant_by_id(db, tenant_id)
        assert t is not None
        ob = onboarding_repo.get_onboarding_for_tenant(db, tenant_id)
        conns = _list_tenant_connections(db, tenant_id=tenant_id)
        member = tenancy_repo.get_first_user_for_tenant(db, tenant_id)
        return TenantAdminDetailResponse(
            id=t.id,
            company_name=t.company_name,
            created_at=t.created_at,
            workspace_access_enabled=bool(t.workspace_access_enabled),
            onboarding=_snapshot_from_onboarding(db, ob),
            member_full_name=member.full_name if member else None,
            member_email=member.email if member else None,
            connected_connectors=[c.provider for c in conns],
            slack_vector_paused=bool(t.slack_vector_paused),
        )

    @r.patch(
        "/tenants/{tenant_id}/primary-member-full-name",
        response_model=TenantAdminDetailResponse,
    )
    def patch_tenant_primary_member_full_name(
        tenant_id: uuid.UUID,
        body: AdminTenantPrimaryMemberFullNamePatchRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> TenantAdminDetailResponse:
        """Update ``users.full_name`` for the primary (oldest) member of this tenant."""
        _assert_tenant(db, tenant_id)
        user = tenancy_repo.get_first_user_for_tenant(db, tenant_id)
        if user is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="No membership user found for this tenant.",
            ) from None
        raw = body.member_full_name
        if raw is None:
            user.full_name = None
        else:
            s = raw.strip()
            user.full_name = s if s else None
        db.commit()
        db.refresh(user)
        t = tenancy_repo.get_tenant_by_id(db, tenant_id)
        assert t is not None
        ob = onboarding_repo.get_onboarding_for_tenant(db, tenant_id)
        conns = _list_tenant_connections(db, tenant_id=tenant_id)
        member = tenancy_repo.get_first_user_for_tenant(db, tenant_id)
        return TenantAdminDetailResponse(
            id=t.id,
            company_name=t.company_name,
            created_at=t.created_at,
            workspace_access_enabled=bool(t.workspace_access_enabled),
            onboarding=_snapshot_from_onboarding(db, ob),
            member_full_name=member.full_name if member else None,
            member_email=member.email if member else None,
            connected_connectors=[c.provider for c in conns],
            slack_vector_paused=bool(t.slack_vector_paused),
        )

    @r.patch(
        "/tenants/{tenant_id}/workspace-access",
        response_model=TenantAdminDetailResponse,
    )
    def set_tenant_workspace_access(
        tenant_id: uuid.UUID,
        body: AdminTenantWorkspaceAccessRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> TenantAdminDetailResponse:
        t = tenancy_repo.get_tenant_by_id(db, tenant_id)
        if t is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found.") from None
        was_enabled = bool(t.workspace_access_enabled)
        t.workspace_access_enabled = body.workspace_access_enabled
        db.commit()
        db.refresh(t)
        if body.workspace_access_enabled and not was_enabled:
            member = tenancy_repo.get_first_user_for_tenant(db, tenant_id)
            if member and member.email:
                settings = get_settings()
                enqueue_onboarding_activation_email(
                    to=str(member.email),
                    full_name=member.full_name,
                    onboarding_url=onboarding_entry_url(settings),
                )
        ob = onboarding_repo.get_onboarding_for_tenant(db, tenant_id)
        conns = _list_tenant_connections(db, tenant_id=tenant_id)
        member = tenancy_repo.get_first_user_for_tenant(db, tenant_id)
        return TenantAdminDetailResponse(
            id=t.id,
            company_name=t.company_name,
            created_at=t.created_at,
            workspace_access_enabled=bool(t.workspace_access_enabled),
            onboarding=_snapshot_from_onboarding(db, ob),
            member_full_name=member.full_name if member else None,
            member_email=member.email if member else None,
            connected_connectors=[c.provider for c in conns],
            slack_vector_paused=bool(t.slack_vector_paused),
        )

    @r.patch(
        "/tenants/{tenant_id}/slack-delivery",
        response_model=TenantAdminDetailResponse,
    )
    def set_tenant_slack_delivery(
        tenant_id: uuid.UUID,
        body: AdminTenantSlackDeliveryRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> TenantAdminDetailResponse:
        t = tenancy_repo.get_tenant_by_id(db, tenant_id)
        if t is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found.") from None
        t.slack_vector_paused = body.slack_vector_paused
        db.commit()
        db.refresh(t)
        ob = onboarding_repo.get_onboarding_for_tenant(db, tenant_id)
        conns = _list_tenant_connections(db, tenant_id=tenant_id)
        member = tenancy_repo.get_first_user_for_tenant(db, tenant_id)
        return TenantAdminDetailResponse(
            id=t.id,
            company_name=t.company_name,
            created_at=t.created_at,
            workspace_access_enabled=bool(t.workspace_access_enabled),
            onboarding=_snapshot_from_onboarding(db, ob),
            member_full_name=member.full_name if member else None,
            member_email=member.email if member else None,
            connected_connectors=[c.provider for c in conns],
            slack_vector_paused=bool(t.slack_vector_paused),
        )

    @r.post(
        "/tenants/{tenant_id}/dev-complete-website-onboarding",
        response_model=OnboardingCompleteResponse,
    )
    def admin_dev_complete_website_onboarding(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> OnboardingCompleteResponse:
        """Development only: mark website onboarding completed so /me sees onboarding_completed (dashboard)."""
        if settings.env.strip().lower() != "development":
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="This endpoint is only available when ENV=development.",
            ) from None
        t = tenancy_repo.get_tenant_by_id(db, tenant_id)
        if t is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found.") from None
        out = dev_force_complete_website_onboarding_for_tenant(db, tenant_id=tenant_id)
        db.commit()
        return out

    @r.get("/tenants/{tenant_id}/connections", response_model=AdminConnectionsResponse)
    def list_connections(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminConnectionsResponse:
        _assert_tenant(db, tenant_id)
        rows = _list_tenant_connections(db, tenant_id=tenant_id)
        return AdminConnectionsResponse(
            items=[
                TenantConnectionAdminItem(
                    id=row.id,
                    provider=row.provider,
                    status=row.status,
                    created_at=row.created_at,
                )
                for row in rows
            ],
        )

    @r.delete(
        "/tenants/{tenant_id}/connections/{provider}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def admin_disconnect_tenant_connector(
        tenant_id: uuid.UUID,
        provider: str,
        db: Annotated[Session, Depends(get_db)],
    ) -> Response:
        """Remove a workspace integration (GitHub, Linear, or Slack) for support / testing."""
        _assert_tenant(db, tenant_id)
        runtimes = runtime_by_id()
        runtime = runtimes.get(provider)
        if runtime is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail=f"Unknown connector provider: {provider!r}.",
            ) from None
        runtime.disconnect_tenant(db, tenant_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @r.get(
        "/tenants/{tenant_id}/connections/{provider}/connect-link",
        response_model=AdminConnectorConnectLinkResponse,
    )
    def admin_connector_connect_link(
        tenant_id: uuid.UUID,
        provider: Literal["slack", "github", "linear", "notion", "calls"],
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminConnectorConnectLinkResponse:
        """Generate a tenant-scoped OAuth install URL for admin-assisted setup."""
        _assert_tenant(db, tenant_id)
        member = tenancy_repo.get_first_user_for_tenant(db, tenant_id)
        if member is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Tenant has no member to anchor OAuth state.",
            ) from None
        return_to = f"/admin/tenants/{tenant_id}/integrations"
        try:
            if provider == "slack":
                connect_url = start_slack_oauth_url(
                    settings,
                    tenant_id=tenant_id,
                    user_id=member.id,
                    return_to=return_to,
                )
            elif provider == "github":
                connect_url = start_github_install_url(
                    settings,
                    tenant_id=tenant_id,
                    user_id=member.id,
                    return_to=return_to,
                )
            elif provider == "linear":
                connect_url = start_linear_oauth_url(
                    settings,
                    tenant_id=tenant_id,
                    user_id=member.id,
                    return_to=return_to,
                )
            elif provider == "notion":
                connect_url = start_notion_oauth_url(
                    settings,
                    tenant_id=tenant_id,
                    user_id=member.id,
                    return_to=return_to,
                )
            else:
                connect_url = start_calls_oauth_url(
                    settings,
                    tenant_id=tenant_id,
                    user_id=member.id,
                    return_to=return_to,
                )
        except (
            SlackConnectorNotConfiguredError,
            GitHubConnectorNotConfiguredError,
            LinearConnectorNotConfiguredError,
            NotionConnectorNotConfiguredError,
            CallsConnectorNotConfiguredError,
        ) as e:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
        except Exception as e:
            _logger.exception(
                "admin connect-link generation failed",
                extra={"tenant_id": str(tenant_id), "provider": provider},
            )
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"connect-link generation failed for provider={provider}: {e}",
            ) from e
        return AdminConnectorConnectLinkResponse(
            provider=provider,
            connect_url=connect_url,
            tenant_id=tenant_id,
            user_id=member.id,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/ingestion",
        response_model=AdminCortexIngestionOverviewResponse,
    )
    def admin_cortex_ingestion_overview(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCortexIngestionOverviewResponse:
        """Phase 01 Step 6 — visibility: runs, checkpoints, routing, scheduler mode (read-only)."""
        _assert_tenant(db, tenant_id)
        try:
            raw = build_cortex_ingestion_admin_overview(db, settings, tenant_id)
        except ValueError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found.") from None
        return AdminCortexIngestionOverviewResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/ingestion/exhaust-coverage",
        response_model=AdminCortexIngestionExhaustCoverageResponse,
    )
    def admin_cortex_ingestion_exhaust_coverage(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexIngestionExhaustCoverageResponse:
        """Declared organizational exhaust depth (matrix + maturity levels; read-only)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.ingestion.exhaust_coverage_registry import (
            build_admin_exhaust_coverage_payload,
        )

        raw = build_admin_exhaust_coverage_payload(tenant_id=tenant_id)
        return AdminCortexIngestionExhaustCoverageResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/ingestion/raw-stats",
        response_model=AdminCortexRawIngestionStatsResponse,
    )
    def admin_cortex_ingestion_raw_stats(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        connector: Annotated[str | None, Query()] = None,
        resource_type: Annotated[str | None, Query()] = None,
        fetched_after: Annotated[datetime | None, Query()] = None,
        fetched_before: Annotated[datetime | None, Query()] = None,
        include_health_rows: Annotated[bool, Query()] = False,
    ) -> AdminCortexRawIngestionStatsResponse:
        """Observed raw exhaust aggregates (defaults to hiding health-like ping rows)."""
        _assert_tenant(db, tenant_id)
        rows = aggregate_raw_ingestion_stats(
            db,
            tenant_id,
            connector=connector,
            resource_type=resource_type,
            fetched_after=fetched_after,
            fetched_before=fetched_before,
            include_health_rows=include_health_rows,
        )
        rollups = build_connector_raw_rollups(rows)
        return AdminCortexRawIngestionStatsResponse(
            tenant_id=tenant_id,
            resources=[AdminCortexRawIngestionResourceStat.model_validate(x) for x in rows],
            connector_rollups=rollups,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/ingestion/verification",
        response_model=AdminCortexIngestionVerificationResponse,
    )
    def admin_cortex_ingestion_verification(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
        run_limit: Annotated[int, Query(ge=1, le=200)] = 30,
    ) -> AdminCortexIngestionVerificationResponse:
        """Phase 01 Step 6 — operator checklist (read-only invariant sweep)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.ingestion.verification import verify_tenant_ingestion_invariants

        rep = verify_tenant_ingestion_invariants(
            db,
            tenant_id,
            run_limit=run_limit,
            enforce_exhaust_gate=True,
            enforcement_mode=settings.cortex_raw_memory_enforcement_mode,
        )
        log_ingestion_event(
            _logger,
            logging.INFO,
            "admin cortex ingestion verification",
            task_name="admin_cortex_ingestion_verification",
            phase=PHASE_STEP6,
            outcome="passed" if rep["passed"] else "failed",
            tenant_id=str(tenant_id),
        )
        return AdminCortexIngestionVerificationResponse.model_validate(rep)

    @r.get(
        "/tenants/{tenant_id}/cortex/ingestion/recent-runs",
        response_model=AdminCortexIngestionRecentRunsResponse,
    )
    def admin_cortex_ingestion_recent_runs(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=100)] = 30,
    ) -> AdminCortexIngestionRecentRunsResponse:
        """Recent ingestion runs for drill-down (read-only)."""
        _assert_tenant(db, tenant_id)
        rows = list_recent_ingestion_runs(db, tenant_id, limit=limit)
        return AdminCortexIngestionRecentRunsResponse(
            items=[AdminCortexIngestionRecentRunItem.model_validate(x) for x in rows],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/ingestion/connectors/{connector}/raw-records",
        response_model=AdminCortexConnectorRawRecordsResponse,
    )
    def admin_cortex_ingestion_connector_raw_records(
        tenant_id: uuid.UUID,
        connector: CortexIngestionConnectorId,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0, le=50_000)] = 0,
        resource_type: Annotated[str | None, Query()] = None,
        fetched_after: Annotated[datetime | None, Query()] = None,
        fetched_before: Annotated[datetime | None, Query()] = None,
        search_query: Annotated[str | None, Query()] = None,
        include_health_rows: Annotated[bool, Query()] = False,
    ) -> AdminCortexConnectorRawRecordsResponse:
        """Raw rows for tenant+connector with Step 13 filters and payload drilldown search."""
        _assert_tenant(db, tenant_id)
        items, truncated, total_count = list_raw_records_for_connector(
            db,
            tenant_id,
            connector,
            limit=limit,
            offset=offset,
            resource_type=resource_type,
            fetched_after=fetched_after,
            fetched_before=fetched_before,
            search_query=search_query,
            include_health_rows=include_health_rows,
        )
        return AdminCortexConnectorRawRecordsResponse(
            tenant_id=tenant_id,
            connector=connector,
            items=[AdminCortexConnectorRawRecordItem.model_validate(x) for x in items],
            total_count=total_count,
            offset=offset,
            limit=limit,
            truncated=truncated,
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/memory/query",
        response_model=AdminCortexRawMemoryQueryResponse,
    )
    def admin_cortex_memory_query(
        tenant_id: uuid.UUID,
        body: AdminCortexRawMemoryQueryRequest,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCortexRawMemoryQueryResponse:
        """Phase 02 Step 5 — deterministic evidence retrieval with anti-goal guardrails."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.ingestion.verification import verify_tenant_ingestion_invariants

        verification_payload = verify_tenant_ingestion_invariants(
            db,
            tenant_id,
            run_limit=30,
            enforce_exhaust_gate=True,
            enforcement_mode=settings.cortex_raw_memory_enforcement_mode,
        )
        trust_annotation = (
            verification_payload.get("raw_memory_trust", {}).get("annotation")
            if isinstance(verification_payload.get("raw_memory_trust"), dict)
            else None
        )
        enforcement = evaluate_progressive_enforcement(
            trust_annotation=trust_annotation if isinstance(trust_annotation, dict) else None,
            phase_closure=(
                verification_payload.get("raw_memory_phase_closure")
                if isinstance(verification_payload.get("raw_memory_phase_closure"), dict)
                else None
            ),
            mode=(
                settings.cortex_raw_memory_enforcement_mode
                if settings.cortex_raw_memory_enforcement_mode in {"observe", "progressive", "strict"}
                else "progressive"
            ),
            operation=("reconstruction_read" if body.mode == "temporal" else "memory_query"),
        )
        if enforcement["blocked"]:
            raise HTTPException(
                status.HTTP_423_LOCKED,
                detail={
                    "message": "Operation blocked by raw-memory enforcement policy.",
                    "enforcement": enforcement,
                },
            ) from None
        try:
            out = execute_raw_memory_query(
                db,
                tenant_id=tenant_id,
                mode=body.mode,
                intent=body.intent,
                query_text=body.query_text,
                connector=body.connector,
                resource_type=body.resource_type,
                source_identity_key=body.source_identity_key,
                source_revision_key=body.source_revision_key,
                replay_job_id=body.replay_job_id,
                run_id=body.run_id,
                provenance_chain_id=body.provenance_chain_id,
                fetched_after=body.fetched_after,
                fetched_before=body.fetched_before,
                temporal_submode=body.temporal_submode,
                as_of=body.as_of,
                limit=body.limit,
                offset=body.offset,
            )
        except ValueError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        return AdminCortexRawMemoryQueryResponse(
            tenant_id=tenant_id,
            mode=out["mode"],
            items=[AdminCortexConnectorRawRecordItem.model_validate(x) for x in out["items"]],
            total_count=out["total_count"],
            offset=out["offset"],
            limit=out["limit"],
            truncated=out["truncated"],
            enforcement=enforcement,
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/memory/retention/apply",
        response_model=AdminCortexRawMemoryRetentionApplyResponse,
    )
    def admin_cortex_memory_retention_apply(
        tenant_id: uuid.UUID,
        body: AdminCortexRawMemoryRetentionApplyRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexRawMemoryRetentionApplyResponse:
        """Phase 02 Step 6 — apply (or dry-run) raw memory storage retention policy."""
        _assert_tenant(db, tenant_id)
        if body.allow_delete and body.dry_run is False:
            if body.confirmation != CORTEX_RAW_MEMORY_DELETE_CONFIRM_PHRASE:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail="Confirmation phrase does not match raw-memory deletion phrase.",
                ) from None
        out = apply_raw_memory_retention_policy(
            db,
            tenant_id=tenant_id,
            dry_run=body.dry_run,
            archive_after_days=body.archive_after_days,
            delete_after_days=body.delete_after_days,
            allow_delete=body.allow_delete,
        )
        return AdminCortexRawMemoryRetentionApplyResponse(
            tenant_id=tenant_id,
            dry_run=out["dry_run"],
            archive_after_days=out["archive_after_days"],
            delete_after_days=out["delete_after_days"],
            archive_candidate_count=out["archive_candidate_count"],
            delete_candidate_count=out["delete_candidate_count"],
            archive_candidate_ids=out["archive_candidate_ids"],
            delete_candidate_ids=out["delete_candidate_ids"],
            deletes_executed=out["deletes_executed"],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/memory/failures",
        response_model=AdminCortexRawMemoryFailuresResponse,
    )
    def admin_cortex_memory_failures(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexRawMemoryFailuresResponse:
        """Phase 02 Step 7 — synchronize and expose active failure-class summary."""
        _assert_tenant(db, tenant_id)
        out = sync_raw_memory_failure_cases(db, tenant_id)
        return AdminCortexRawMemoryFailuresResponse(
            tenant_id=tenant_id,
            active_failure_count=out["active_failure_count"],
            active_failure_classes=out["active_failure_classes"],
            sync=out,
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/memory/recovery/validate",
        response_model=AdminCortexRawMemoryRecoveryValidateResponse,
    )
    def admin_cortex_memory_recovery_validate(
        tenant_id: uuid.UUID,
        body: AdminCortexRawMemoryRecoveryValidateRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexRawMemoryRecoveryValidateResponse:
        """Phase 02 Step 7 — run recovery validation with optional index/catalog repairs."""
        _assert_tenant(db, tenant_id)
        out = run_raw_memory_recovery_validation(
            db,
            tenant_id=tenant_id,
            apply_repairs=body.apply_repairs,
        )
        return AdminCortexRawMemoryRecoveryValidateResponse(
            tenant_id=tenant_id,
            status=out["status"],
            apply_repairs=out["apply_repairs"],
            active_failures=out["active_failures"],
            unresolved_recoverable=out["unresolved_recoverable"],
            detail=out["detail"],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/memory/trust-state",
        response_model=AdminCortexRawMemoryTrustStateResponse,
    )
    def admin_cortex_memory_trust_state(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCortexRawMemoryTrustStateResponse:
        """Phase 02 Step 8 — canonical trust annotation for raw-memory scope."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.ingestion.verification import verify_tenant_ingestion_invariants

        rep = verify_tenant_ingestion_invariants(
            db,
            tenant_id,
            run_limit=30,
            enforce_exhaust_gate=True,
            enforcement_mode=settings.cortex_raw_memory_enforcement_mode,
        )
        trust = rep.get("raw_memory_trust") or {}
        annotation = trust.get("annotation") if isinstance(trust, dict) else None
        if not isinstance(annotation, dict):
            annotation = build_raw_memory_trust_annotation(
                db,
                tenant_id=tenant_id,
                raw_memory_contracts=rep.get("raw_memory_contracts", {}),
                raw_memory_persistence=rep.get("raw_memory_persistence", {}),
                raw_memory_temporal=rep.get("raw_memory_temporal", {}),
                raw_memory_replay=rep.get("raw_memory_replay", {}),
                raw_memory_query=rep.get("raw_memory_query", {}),
                raw_memory_failure_recovery=rep.get("raw_memory_failure_recovery", {}),
            )
            persist_raw_memory_trust_annotation(db, tenant_id=tenant_id, annotation=annotation)
        return AdminCortexRawMemoryTrustStateResponse(
            tenant_id=tenant_id,
            trust_state=str(annotation.get("trust_state", "unverifiable")),
            severity=str(annotation.get("severity", "S2")),
            state_reason_codes=list(annotation.get("state_reason_codes", [])),
            replay=dict(annotation.get("replay", {})),
            reconstruction=dict(annotation.get("reconstruction", {})),
            provenance=dict(annotation.get("provenance", {})),
            blocking=dict(annotation.get("blocking", {})),
            continuity_gaps=list(annotation.get("continuity_gaps", [])),
            verification=dict(annotation.get("verification", {})),
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/memory/control-plane",
        response_model=AdminCortexRawMemoryControlPlaneResponse,
    )
    def admin_cortex_memory_control_plane(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCortexRawMemoryControlPlaneResponse:
        """Phase 02 Step 9 — operator runtime memory control-plane aggregate."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.ingestion.verification import verify_tenant_ingestion_invariants

        verification_payload = verify_tenant_ingestion_invariants(
            db,
            tenant_id,
            run_limit=30,
            enforce_exhaust_gate=True,
            enforcement_mode=settings.cortex_raw_memory_enforcement_mode,
        )
        out = build_raw_memory_control_plane(
            db,
            tenant_id,
            verification_payload=verification_payload,
        )
        return AdminCortexRawMemoryControlPlaneResponse.model_validate(out)

    @r.get(
        "/tenants/{tenant_id}/cortex/memory/phase-closure",
        response_model=AdminCortexRawMemoryPhaseClosureResponse,
    )
    def admin_cortex_memory_phase_closure(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCortexRawMemoryPhaseClosureResponse:
        """Phase 02 Step 10 — binary closure gate status."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.ingestion.verification import verify_tenant_ingestion_invariants

        verification_payload = verify_tenant_ingestion_invariants(
            db,
            tenant_id,
            run_limit=30,
            enforce_exhaust_gate=True,
            enforcement_mode=settings.cortex_raw_memory_enforcement_mode,
        )
        closure = verification_payload.get("raw_memory_phase_closure") or {}
        return AdminCortexRawMemoryPhaseClosureResponse.model_validate(closure)

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/ontology",
        response_model=AdminCortexCanonicalOntologyResponse,
    )
    def admin_cortex_canonical_ontology(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexCanonicalOntologyResponse:
        """Phase 03 Steps 1–17 — ontology + taxonomy + logical keys + contracts + registry + transform + ambiguity + confidence + identity + replay + provenance + temporal ordering + canonical query + failure/remediation + verification engine + control-plane + stabilization-proof pointers."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.ontology import (
            build_phase03_step01_ontology_public_document,
        )

        raw = build_phase03_step01_ontology_public_document(tenant_id=tenant_id)
        return AdminCortexCanonicalOntologyResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/control-plane",
        response_model=AdminCortexCanonicalControlPlaneResponse,
    )
    def admin_cortex_canonical_control_plane(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexCanonicalControlPlaneResponse:
        """Phase 03 Step 16 — operator canonical control-plane aggregate (substrate metrics + IA route hints)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.canonical_control_plane import (
            build_canonical_control_plane,
        )

        raw = build_canonical_control_plane(db, tenant_id)
        return AdminCortexCanonicalControlPlaneResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/coverage-matrix",
        response_model=AdminCortexCanonicalCoverageMatrixResponse,
    )
    def admin_cortex_canonical_coverage_matrix(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexCanonicalCoverageMatrixResponse:
        """Canonical coverage matrix — routing registry + ingest exhaust + live raw/materialization counts."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.canonical_coverage_matrix import (
            build_canonical_coverage_matrix,
        )

        raw = build_canonical_coverage_matrix(db, tenant_id=tenant_id)
        return AdminCortexCanonicalCoverageMatrixResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/kind-invariants",
        response_model=AdminCortexCanonicalKindInvariantsResponse,
    )
    def admin_cortex_canonical_kind_invariants(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexCanonicalKindInvariantsResponse:
        """Canonical kind invariant contract matrix (identity/temporal/provenance/structure/ambiguity)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.canonical_kind_invariants import (
            build_canonical_kind_invariants_document,
        )

        raw = build_canonical_kind_invariants_document()
        return AdminCortexCanonicalKindInvariantsResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/stabilization-proof",
        response_model=AdminCortexStabilizationProofRunResponse,
    )
    def admin_cortex_canonical_stabilization_proof_snapshot(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexStabilizationProofRunResponse:
        """Phase 03 Step 17 — live stabilization / economics proof snapshot (read-only)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.canonical_stabilization_proof import (
            build_stabilization_proof_report,
        )

        raw = build_stabilization_proof_report(db, tenant_id)
        raw["persisted_run_id"] = None
        return AdminCortexStabilizationProofRunResponse.model_validate(raw)

    @r.post(
        "/tenants/{tenant_id}/cortex/canonical/stabilization-proof/run",
        response_model=AdminCortexStabilizationProofRunResponse,
    )
    def admin_cortex_canonical_stabilization_proof_run(
        tenant_id: uuid.UUID,
        body: AdminCortexStabilizationProofRunRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexStabilizationProofRunResponse:
        """Phase 03 Step 17 — compute stabilization proof; optionally persist ledger row."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.canonical_stabilization_proof import (
            run_stabilization_proof_pass,
        )

        raw = run_stabilization_proof_pass(db, tenant_id=tenant_id, persist=body.persist)
        if body.persist:
            db.commit()
        return AdminCortexStabilizationProofRunResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/stabilization-proof/runs",
        response_model=AdminCortexStabilizationProofRunsListResponse,
    )
    def admin_cortex_canonical_stabilization_proof_runs(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> AdminCortexStabilizationProofRunsListResponse:
        """Phase 03 Step 17 — recent persisted stabilization proof runs."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.canonical_stabilization_proof import (
            STABILIZATION_PROOF_SCHEMA_VERSION,
            list_stabilization_proof_runs,
            stabilization_proof_run_public_dict,
        )

        rows = list_stabilization_proof_runs(db, tenant_id=tenant_id, limit=limit)
        items: list[AdminCortexStabilizationProofRunItem] = []
        for r in rows:
            d = stabilization_proof_run_public_dict(r)
            items.append(
                AdminCortexStabilizationProofRunItem(
                    id=d["id"],
                    tenant_id=d["tenant_id"],
                    proof_schema_version=d["proof_schema_version"],
                    passed=d["passed"],
                    probes_json=d["probes_json"],
                    created_at=d["created_at"],
                )
            )
        return AdminCortexStabilizationProofRunsListResponse(
            stabilization_proof_schema_version=STABILIZATION_PROOF_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            runs=items,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/oracle-manifest",
        response_model=AdminCortexOracleManifestResponse,
    )
    def admin_cortex_canonical_oracle_manifest(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOracleManifestResponse:
        """Phase 03 Step 3 — oracle vectors manifest (pre-runtime CI/promotion inventory)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.oracle_manifest import (
            build_oracle_manifest_public_document,
        )

        raw = build_oracle_manifest_public_document(tenant_id=tenant_id)
        return AdminCortexOracleManifestResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/mapping-registry",
        response_model=AdminCortexMappingRegistryResponse,
    )
    def admin_cortex_canonical_mapping_registry(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexMappingRegistryResponse:
        """Phase 03 Step 5 — mapping bundle registry, pins, compatibility edges, changelog."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.mapping_bundle_registry import (
            build_tenant_mapping_registry_public_document,
        )

        raw = build_tenant_mapping_registry_public_document(db=db, tenant_id=tenant_id)
        return AdminCortexMappingRegistryResponse.model_validate(raw)

    @r.post(
        "/tenants/{tenant_id}/cortex/canonical/transform/materialize",
        response_model=AdminCortexMaterializeTransformResponse,
    )
    def admin_cortex_canonical_transform_materialize(
        tenant_id: uuid.UUID,
        body: AdminCortexMaterializeTransformRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexMaterializeTransformResponse:
        """Phase 03 Step 6 — run deterministic stub transform + persist field lineage."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.transform_runtime import (
            MaterializeError,
            materialization_public_dict,
            materialize_raw_record,
        )

        try:
            mat = materialize_raw_record(
                db,
                tenant_id=tenant_id,
                bundle_id=body.bundle_id,
                raw_record_id=body.raw_record_id,
            )
        except MaterializeError as exc:
            from vector.domains.cortex.canonical.failure_remediation_runtime import (
                record_transform_materialize_failure,
            )

            record_transform_materialize_failure(
                db,
                tenant_id=tenant_id,
                bundle_id=body.bundle_id,
                raw_record_id=body.raw_record_id,
                message=str(exc),
            )
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        payload = {"materialization": materialization_public_dict(mat)}
        return AdminCortexMaterializeTransformResponse.model_validate(payload)

    @r.post(
        "/tenants/{tenant_id}/cortex/canonical/transform/materialize-backlog",
        response_model=AdminCortexMaterializeBacklogResponse,
    )
    def admin_cortex_canonical_transform_materialize_backlog(
        tenant_id: uuid.UUID,
        body: AdminCortexMaterializeBacklogRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexMaterializeBacklogResponse:
        """Route-routable ingested rows missing a materialization for ``bundle_id`` (batched; scopeable)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.transform_runtime import (
            MaterializeError,
            materialize_stub_backlog,
        )

        try:
            raw = materialize_stub_backlog(
                db,
                tenant_id=tenant_id,
                bundle_id=body.bundle_id,
                connector=body.connector,
                resource_type=body.resource_type,
                batch_limit=body.batch_limit,
                dry_run=body.dry_run,
            )
        except MaterializeError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        failures = [
            AdminCortexMaterializeBacklogFailureItem.model_validate(x) for x in raw["failures"]
        ]
        return AdminCortexMaterializeBacklogResponse(
            transform_runtime_schema_version=raw["transform_runtime_schema_version"],
            tenant_id=raw["tenant_id"],
            bundle_id=raw["bundle_id"],
            dry_run=raw["dry_run"],
            stub_resource_pairs_selected=raw["stub_resource_pairs_selected"],
            scope_connector=raw.get("scope_connector"),
            scope_resource_type=raw.get("scope_resource_type"),
            batch_limit_applied=raw["batch_limit_applied"],
            candidate_more_remain=raw["candidate_more_remain"],
            attempted=raw["attempted"],
            attempted_by_resource_type=raw.get("attempted_by_resource_type") or {},
            succeeded=raw["succeeded"],
            succeeded_by_resource_type=raw.get("succeeded_by_resource_type") or {},
            failures=failures,
            raw_record_ids_sample=raw["raw_record_ids_sample"],
            duration_ms=raw.get("duration_ms"),
            throughput_rows_per_second=raw.get("throughput_rows_per_second"),
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/canonical/transform/materialize-backlog-async",
        response_model=AdminCortexMaterializeBacklogAsyncResponse,
    )
    def admin_cortex_canonical_transform_materialize_backlog_async(
        tenant_id: uuid.UUID,
        body: AdminCortexMaterializeBacklogAsyncRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexMaterializeBacklogAsyncResponse:
        """Enqueue Celery drain of routable backlog until idle (scopeable connector/resource_type filters)."""
        _assert_tenant(db, tenant_id)
        from app.tasks.cortex_canonical_materialize_backlog import (
            drain_stub_materialize_backlog_task,
        )
        from vector.domains.cortex.canonical.transform_runtime import (
            resolve_default_bundle_id_for_stub_transform,
        )

        hint = body.bundle_id.strip() if body.bundle_id and body.bundle_id.strip() else None
        resolved = hint or resolve_default_bundle_id_for_stub_transform(db, tenant_id)
        if resolved is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=(
                    "no_transformable_bundle — add a tenant mapping pin or ensure an approved/candidate bundle exists"
                ),
            )
        enqueued_batch_limit = body.batch_limit if body.batch_limit is not None else 400
        try:
            async_result = drain_stub_materialize_backlog_task.delay(
                str(tenant_id),
                resolved,
                body.connector,
                body.resource_type,
                enqueued_batch_limit,
            )
        except Exception as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"celery_enqueue_failed:{exc}",
            ) from exc

        return AdminCortexMaterializeBacklogAsyncResponse(
            enqueued=True,
            celery_task_id=str(async_result.id),
            tenant_id=str(tenant_id),
            bundle_id_used=resolved,
            scope_connector=body.connector.strip() if body.connector and body.connector.strip() else None,
            scope_resource_type=body.resource_type.strip() if body.resource_type and body.resource_type.strip() else None,
            batch_limit=enqueued_batch_limit,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/transform/lineage",
        response_model=AdminCortexTransformLineageListResponse,
    )
    def admin_cortex_canonical_transform_lineage(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> AdminCortexTransformLineageListResponse:
        """Phase 03 Steps 6–8 — recent transform materializations + field lineage + confidence metadata."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.confidence_runtime import (
            CONFIDENCE_PROPAGATION_SCHEMA_VERSION,
        )
        from vector.domains.cortex.canonical.transform_runtime import (
            TRANSFORM_RUNTIME_SCHEMA_VERSION,
            list_recent_materializations,
            materialization_public_dict,
        )

        mats = list_recent_materializations(db, tenant_id=tenant_id, limit=limit)
        raw = {
            "transform_runtime_schema_version": TRANSFORM_RUNTIME_SCHEMA_VERSION,
            "confidence_propagation_schema_version": CONFIDENCE_PROPAGATION_SCHEMA_VERSION,
            "tenant_id": str(tenant_id),
            "materializations": [materialization_public_dict(m) for m in mats],
        }
        return AdminCortexTransformLineageListResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/confidence/summary",
        response_model=AdminCortexConfidenceSummaryResponse,
    )
    def admin_cortex_canonical_confidence_summary(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexConfidenceSummaryResponse:
        """Phase 03 Step 8 — aggregate confidence_class counts over field lineage (structured, non-ranking)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.confidence_runtime import (
            CONFIDENCE_NON_RANKING_SEMANTICS,
            CONFIDENCE_PROPAGATION_SCHEMA_VERSION,
            confidence_class_rollup_for_tenant,
        )

        total, by_class = confidence_class_rollup_for_tenant(db, tenant_id=tenant_id)
        return AdminCortexConfidenceSummaryResponse(
            confidence_propagation_schema_version=CONFIDENCE_PROPAGATION_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            field_lineage_rows_total=total,
            by_confidence_class=by_class,
            confidence_non_ranking_semantics=CONFIDENCE_NON_RANKING_SEMANTICS,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/identity/anchors",
        response_model=AdminCortexIdentityAnchorListResponse,
    )
    def admin_cortex_canonical_identity_anchors_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> AdminCortexIdentityAnchorListResponse:
        """Phase 03 Step 9 — provider-scoped canonical identity anchors + Phase 04 handoff hooks."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.identity_runtime import (
            IDENTITY_RUNTIME_SCHEMA_VERSION,
            identity_anchor_public_dict,
            list_identity_anchors,
        )

        rows = list_identity_anchors(db, tenant_id=tenant_id, limit=limit)
        return AdminCortexIdentityAnchorListResponse(
            identity_runtime_schema_version=IDENTITY_RUNTIME_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            anchors=[AdminCortexIdentityAnchorItem.model_validate(identity_anchor_public_dict(x)) for x in rows],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/identity/anchors/{canonical_entity_id}",
        response_model=AdminCortexIdentityAnchorItem,
    )
    def admin_cortex_canonical_identity_anchor_detail(
        tenant_id: uuid.UUID,
        canonical_entity_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexIdentityAnchorItem:
        """Phase 03 Step 9 — single identity anchor by deterministic canonical_entity_id."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.identity_runtime import (
            get_identity_anchor,
            identity_anchor_public_dict,
        )

        row = get_identity_anchor(db, tenant_id=tenant_id, canonical_entity_id=canonical_entity_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="identity_anchor_not_found")
        return AdminCortexIdentityAnchorItem.model_validate(identity_anchor_public_dict(row))

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/entities",
        response_model=AdminCortexOrgEntityListResponse,
    )
    def admin_cortex_identity_org_entities_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
    ) -> AdminCortexOrgEntityListResponse:
        """Phase 04 Step 3 — read-only org entity (org handle) list per doctrine."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_entities import (
            ORG_ENTITY_RUNTIME_SCHEMA_VERSION,
            list_org_entities,
            org_entity_public_dict,
        )

        rows = list_org_entities(db, tenant_id=tenant_id, limit=limit)
        entities = [
            AdminCortexOrgEntityItem.model_validate(org_entity_public_dict(x)) for x in rows
        ]
        return AdminCortexOrgEntityListResponse(
            org_entity_runtime_schema_version=ORG_ENTITY_RUNTIME_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            entities=entities,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/entities/{org_entity_id}",
        response_model=AdminCortexOrgEntityItem,
    )
    def admin_cortex_identity_org_entity_detail(
        tenant_id: uuid.UUID,
        org_entity_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgEntityItem:
        """Phase 04 Step 3 — read-only org entity detail by deterministic id."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_entities import (
            get_org_entity,
            org_entity_public_dict,
        )

        row = get_org_entity(db, tenant_id=tenant_id, org_entity_id=org_entity_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="org_entity_not_found")
        return AdminCortexOrgEntityItem.model_validate(org_entity_public_dict(row))

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/handles",
        response_model=AdminCortexIdentityHandlesExplorerResponse,
    )
    def admin_cortex_identity_handles_explorer_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
    ) -> AdminCortexIdentityHandlesExplorerResponse:
        """Phase 04 Step 18 — handles explorer (**org_handle_list_row_v1**), alias of org entities with queue row shape."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.operator_console import (
            IDENTITY_OPERATOR_CONSOLE_SCHEMA_VERSION,
            list_org_handle_list_rows,
        )

        rows = list_org_handle_list_rows(db, tenant_id=tenant_id, limit=limit)
        return AdminCortexIdentityHandlesExplorerResponse(
            identity_operator_console_schema_version=IDENTITY_OPERATOR_CONSOLE_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            rows=[AdminCortexOrgHandleListRowV1.model_validate(x) for x in rows],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/handles/{handle_id}",
        response_model=AdminCortexOrgEntityItem,
    )
    def admin_cortex_identity_handle_detail(
        tenant_id: uuid.UUID,
        handle_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgEntityItem:
        """Phase 04 Step 18 — handle inspector (same payload as ``…/entities/{id}``)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_entities import (
            get_org_entity,
            org_entity_public_dict,
        )

        row = get_org_entity(db, tenant_id=tenant_id, org_entity_id=handle_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="org_entity_not_found")
        return AdminCortexOrgEntityItem.model_validate(org_entity_public_dict(row))

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/links",
        response_model=AdminCortexOrgLinkListResponse,
    )
    def admin_cortex_identity_org_links_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
        link_authority: Annotated[str | None, Query()] = None,
        link_class: Annotated[str | None, Query()] = None,
        authoritative_only: Annotated[bool | None, Query()] = None,
        candidate_only: Annotated[bool | None, Query()] = None,
        ambiguous: Annotated[bool | None, Query()] = None,
        revoked: Annotated[bool | None, Query()] = None,
        replay_drift: Annotated[bool | None, Query()] = None,
        rule_version: Annotated[str | None, Query()] = None,
        primitive_id: Annotated[uuid.UUID | None, Query()] = None,
        handle_id: Annotated[uuid.UUID | None, Query()] = None,
        time_valid_at: Annotated[datetime | None, Query()] = None,
    ) -> AdminCortexOrgLinkListResponse:
        """Phase 04 Step 4 + Step 18 — link ledger list + §9.2 explorer rows (**org_link_list_row_v1**)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.link_explorer import list_org_link_explorer_rows
        from vector.domains.cortex.identity.link_ledger import (
            LINK_LEDGER_RUNTIME_SCHEMA_VERSION,
            link_public_dict,
            list_org_links,
        )

        la = link_authority.strip() if link_authority else None
        lc = link_class.strip() if link_class else None
        rows = list_org_links(db, tenant_id=tenant_id, limit=limit, link_authority=la, link_class=lc)
        links = [AdminCortexOrgLinkItem.model_validate(link_public_dict(x)) for x in rows]
        explorer_dicts = list_org_link_explorer_rows(
            db,
            tenant_id=tenant_id,
            limit=limit,
            authoritative_only=authoritative_only,
            candidate_only=candidate_only,
            ambiguous=ambiguous,
            revoked=revoked,
            replay_drift=replay_drift,
            rule_version=rule_version,
            primitive_id=primitive_id,
            handle_id=handle_id,
            time_valid_at=time_valid_at,
        )
        explorer_rows = [AdminCortexOrgLinkExplorerRowV1.model_validate(x) for x in explorer_dicts]
        return AdminCortexOrgLinkListResponse(
            link_ledger_runtime_schema_version=LINK_LEDGER_RUNTIME_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            links=links,
            explorer_rows=explorer_rows,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/links/hints",
        response_model=AdminCortexOrgLinkListResponse,
    )
    def admin_cortex_identity_org_link_hints_bucket(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
    ) -> AdminCortexOrgLinkListResponse:
        """Phase 04 Step 7 — read-only hint / inferred / prohibited link bucket."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.link_ledger import (
            LINK_LEDGER_RUNTIME_SCHEMA_VERSION,
            link_public_dict,
            list_org_link_hint_bucket,
        )

        rows = list_org_link_hint_bucket(db, tenant_id=tenant_id, limit=limit)
        links = [AdminCortexOrgLinkItem.model_validate(link_public_dict(x)) for x in rows]
        return AdminCortexOrgLinkListResponse(
            link_ledger_runtime_schema_version=LINK_LEDGER_RUNTIME_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            links=links,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/links/timeline",
        response_model=AdminCortexOrgLinkTemporalTimelineResponse,
    )
    def admin_cortex_identity_org_link_temporal_timeline(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        include_revoked: Annotated[bool, Query()] = False,
    ) -> AdminCortexOrgLinkTemporalTimelineResponse:
        """Phase 04 Step 8 — temporal validity + revocation timeline strip (read-only)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.link_ledger import (
            LINK_LEDGER_RUNTIME_SCHEMA_VERSION,
            list_org_link_temporal_timeline,
        )
        from vector.domains.cortex.identity.org_link_temporal import (
            ORG_LINK_TEMPORAL_SCHEMA_VERSION,
            org_link_temporal_strip_public,
        )

        rows = list_org_link_temporal_timeline(
            db, tenant_id=tenant_id, limit=limit, include_revoked=include_revoked
        )
        strips = [
            AdminCortexOrgLinkTemporalStripItem.model_validate(org_link_temporal_strip_public(x)) for x in rows
        ]
        return AdminCortexOrgLinkTemporalTimelineResponse(
            org_link_temporal_schema_version=ORG_LINK_TEMPORAL_SCHEMA_VERSION,
            link_ledger_runtime_schema_version=LINK_LEDGER_RUNTIME_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            strips=strips,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/links/{link_id}",
        response_model=AdminCortexOrgLinkItem,
    )
    def admin_cortex_identity_org_link_detail(
        tenant_id: uuid.UUID,
        link_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgLinkItem:
        """Phase 04 Step 4 — read-only single link row."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.link_ledger import get_org_link, link_public_dict

        row = get_org_link(db, tenant_id=tenant_id, link_id=link_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="org_link_not_found")
        return AdminCortexOrgLinkItem.model_validate(link_public_dict(row))

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/links/{link_id}/revoke",
        response_model=AdminCortexOrgLinkItem,
    )
    def admin_cortex_identity_org_link_revoke(
        tenant_id: uuid.UUID,
        link_id: uuid.UUID,
        body: AdminCortexIdentityOperatorActionRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgLinkItem:
        """Phase 04 Step 18 — policy-gated soft revoke + durable audit row (**G-P04-23**)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.link_ledger import (
            LinkLedgerInvariantError,
            link_public_dict,
            soft_revoke_org_link,
        )
        from vector.domains.cortex.identity.operator_audit import append_identity_console_audit
        from vector.domains.cortex.identity.operator_console import (
            IDENTITY_OPERATOR_CONSOLE_CONFIRM_PHRASE,
        )

        if body.confirmation_phrase.strip() != IDENTITY_OPERATOR_CONSOLE_CONFIRM_PHRASE:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="confirmation_phrase_invalid")
        try:
            row = soft_revoke_org_link(db, tenant_id=tenant_id, link_id=link_id)
            append_identity_console_audit(
                db,
                tenant_id=tenant_id,
                surface="link_ledger",
                action_kind="org_link_revoke",
                ref_uuid=link_id,
                detail_json={"operator_note": body.operator_note} if body.operator_note else {},
            )
            db.commit()
        except LinkLedgerInvariantError as exc:
            db.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return AdminCortexOrgLinkItem.model_validate(link_public_dict(row))

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/link-candidates",
        response_model=AdminCortexOrgLinkCandidateQueueResponse,
    )
    def admin_cortex_identity_link_candidate_queue(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        batch_limit: Annotated[int, Query(ge=1, le=50)] = 10,
    ) -> AdminCortexOrgLinkCandidateQueueResponse:
        """Phase 04 Step 5 — sparse candidate queue (recent batches + bounded rows per batch)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.candidate_generation import (
            CANDIDATE_GENERATION_SCHEMA_VERSION,
            candidate_batch_public_dict,
            candidate_row_public_dict,
            list_candidate_batches,
            list_candidates_for_batch,
        )

        summaries: list[AdminCortexOrgLinkCandidateBatchSummary] = []
        for batch in list_candidate_batches(db, tenant_id=tenant_id, limit=batch_limit):
            cands = list_candidates_for_batch(db, tenant_id=tenant_id, batch_id=batch.id)[:50]
            payload = {
                **candidate_batch_public_dict(batch),
                "candidates": [candidate_row_public_dict(c) for c in cands],
            }
            summaries.append(AdminCortexOrgLinkCandidateBatchSummary.model_validate(payload))
        return AdminCortexOrgLinkCandidateQueueResponse(
            candidate_generation_schema_version=CANDIDATE_GENERATION_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            batches=summaries,
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/link-candidates/regenerate-async",
        response_model=AdminCortexIdentityLegacyCeleryAsyncDispatchResponse,
    )
    def admin_cortex_identity_link_candidates_regenerate_async(
        tenant_id: uuid.UUID,
        body: AdminCortexIdentityLinkCandidatesRegenerateAsyncRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexIdentityLegacyCeleryAsyncDispatchResponse:
        """Phase 04 Step 19 — enqueue legacy candidate regen Celery task + dispatch registry row."""
        _assert_tenant(db, tenant_id)
        from app.tasks.cortex_org_link_jobs import (
            CELERY_TASK_NAME_REGENERATE_LINK_CANDIDATES,
            regenerate_link_candidates_task,
        )
        from vector.domains.cortex.identity.worker_dispatch import append_identity_celery_dispatch

        try:
            ar = regenerate_link_candidates_task.delay(str(tenant_id), body.rule_version.strip())
        except Exception as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"celery_enqueue_failed:{exc}",
            ) from exc
        append_identity_celery_dispatch(
            db,
            tenant_id=tenant_id,
            celery_task_id=str(ar.id),
            task_name=CELERY_TASK_NAME_REGENERATE_LINK_CANDIDATES,
            request_summary={"rule_version": body.rule_version.strip()},
        )
        db.commit()
        path = f"/admin/tenants/{tenant_id}/cortex/identity/worker-tasks/{ar.id}"
        return AdminCortexIdentityLegacyCeleryAsyncDispatchResponse(
            tenant_id=str(tenant_id),
            celery_task_id=str(ar.id),
            task_name=CELERY_TASK_NAME_REGENERATE_LINK_CANDIDATES,
            worker_task_status_path=path,
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/authoritative-replay-async",
        response_model=AdminCortexIdentityLegacyCeleryAsyncDispatchResponse,
    )
    def admin_cortex_identity_authoritative_replay_async(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexIdentityLegacyCeleryAsyncDispatchResponse:
        """Phase 04 Step 19 — enqueue legacy authoritative replay hash Celery task + dispatch row."""
        _assert_tenant(db, tenant_id)
        from app.tasks.cortex_org_link_jobs import (
            CELERY_TASK_NAME_REPLAY_AUTHORITATIVE_LINKS,
            replay_authoritative_links_task,
        )
        from vector.domains.cortex.identity.worker_dispatch import append_identity_celery_dispatch

        try:
            ar = replay_authoritative_links_task.delay(str(tenant_id))
        except Exception as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"celery_enqueue_failed:{exc}",
            ) from exc
        append_identity_celery_dispatch(
            db,
            tenant_id=tenant_id,
            celery_task_id=str(ar.id),
            task_name=CELERY_TASK_NAME_REPLAY_AUTHORITATIVE_LINKS,
            request_summary={},
        )
        db.commit()
        path = f"/admin/tenants/{tenant_id}/cortex/identity/worker-tasks/{ar.id}"
        return AdminCortexIdentityLegacyCeleryAsyncDispatchResponse(
            tenant_id=str(tenant_id),
            celery_task_id=str(ar.id),
            task_name=CELERY_TASK_NAME_REPLAY_AUTHORITATIVE_LINKS,
            worker_task_status_path=path,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/merges",
        response_model=AdminCortexOrgMergeListResponse,
    )
    def admin_cortex_identity_merges_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
    ) -> AdminCortexOrgMergeListResponse:
        """Phase 04 Step 6 — read-only merge ledger list."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.merge_governance import (
            MERGE_GOVERNANCE_SCHEMA_VERSION,
            list_org_merges,
            merge_public_dict,
        )

        rows = list_org_merges(db, tenant_id=tenant_id, limit=limit)
        merges = [AdminCortexOrgMergeItem.model_validate(merge_public_dict(x)) for x in rows]
        return AdminCortexOrgMergeListResponse(
            merge_governance_schema_version=MERGE_GOVERNANCE_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            merges=merges,
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/merges",
        response_model=AdminCortexOrgMergeItem,
    )
    def admin_cortex_identity_merges_append(
        tenant_id: uuid.UUID,
        body: AdminCortexOrgMergeCreateRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgMergeItem:
        """Phase 04 Step 6 — append merge ledger row (durable merge_record)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.merge_governance import (
            MergeGovernanceError,
            append_org_merge,
            merge_public_dict,
        )

        try:
            row = append_org_merge(
                db,
                tenant_id=tenant_id,
                merge_kind=body.merge_kind,
                merge_policy_id=body.merge_policy_id,
                source_entity_ids=list(body.source_entity_ids),
                target_entity_id=body.target_entity_id,
                evidence_raw_record_ids=list(body.evidence_raw_record_ids),
                operator_user_id=body.operator_user_id,
                supersedes_merge_id=body.supersedes_merge_id,
                metadata_json=body.metadata_json,
            )
            db.commit()
        except MergeGovernanceError as exc:
            db.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return AdminCortexOrgMergeItem.model_validate(merge_public_dict(row))

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/bundle-equivalence",
        response_model=AdminCortexBundleEquivalenceDeclarationListResponse,
    )
    def admin_cortex_identity_bundle_equivalence_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=500)] = 200,
        include_revoked: Annotated[bool, Query()] = False,
    ) -> AdminCortexBundleEquivalenceDeclarationListResponse:
        """Phase 04 Step 9 — list bundle equivalence declarations (audit)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.bundle_equivalence import (
            BUNDLE_EQUIVALENCE_SCHEMA_VERSION,
            bundle_equivalence_public_dict,
            list_bundle_equivalence_declarations,
        )

        rows = list_bundle_equivalence_declarations(
            db, tenant_id=tenant_id, limit=limit, include_revoked=include_revoked
        )
        items = [
            AdminCortexBundleEquivalenceDeclarationItem.model_validate(bundle_equivalence_public_dict(x))
            for x in rows
        ]
        return AdminCortexBundleEquivalenceDeclarationListResponse(
            bundle_equivalence_schema_version=BUNDLE_EQUIVALENCE_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            declarations=items,
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/bundle-equivalence",
        response_model=AdminCortexBundleEquivalenceDeclarationItem,
    )
    def admin_cortex_identity_bundle_equivalence_append(
        tenant_id: uuid.UUID,
        body: AdminCortexBundleEquivalenceDeclarationCreateRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexBundleEquivalenceDeclarationItem:
        """Phase 04 Step 9 — append equivalence declaration (operator escape hatch)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.bundle_equivalence import (
            BundleEquivalenceError,
            append_bundle_equivalence_declaration,
            bundle_equivalence_public_dict,
        )

        try:
            row = append_bundle_equivalence_declaration(
                db,
                tenant_id=tenant_id,
                bundle_id_a=body.bundle_id_a,
                bundle_id_b=body.bundle_id_b,
                evidence_raw_record_ids=list(body.evidence_raw_record_ids),
                metadata_json=body.metadata_json,
            )
            db.commit()
        except BundleEquivalenceError as exc:
            db.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return AdminCortexBundleEquivalenceDeclarationItem.model_validate(bundle_equivalence_public_dict(row))

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/replay-jobs/run",
        response_model=AdminCortexOrgLinkReplayJobDetailResponse,
    )
    def admin_cortex_identity_org_link_replay_job_run(
        tenant_id: uuid.UUID,
        body: AdminCortexOrgLinkReplayJobRunRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgLinkReplayJobDetailResponse:
        """Phase 04 Step 10 — run org link continuity replay / candidate regen (job + L-class receipts)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_link_replay_runtime import (
            ORG_LINK_REPLAY_SCHEMA_VERSION,
            OrgLinkReplayError,
            execute_org_link_replay_job,
            org_link_replay_job_public_dict,
            org_link_replay_receipt_public_dict,
        )

        try:
            job = execute_org_link_replay_job(
                db,
                tenant_id=tenant_id,
                job_kind=body.job_kind,
                pinned_rule_version=body.pinned_rule_version,
                dry_run=body.dry_run,
                scope_json=body.scope_json,
            )
            db.commit()
        except OrgLinkReplayError as exc:
            db.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        receipts = sorted(job.receipts, key=lambda r: r.id)
        return AdminCortexOrgLinkReplayJobDetailResponse(
            org_link_replay_schema_version=ORG_LINK_REPLAY_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            job=AdminCortexOrgLinkReplayJobItem.model_validate(org_link_replay_job_public_dict(job)),
            receipts=[
                AdminCortexOrgLinkReplayJobReceiptItem.model_validate(org_link_replay_receipt_public_dict(r))
                for r in receipts
            ],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/replay-jobs",
        response_model=AdminCortexOrgLinkReplayJobListResponse,
    )
    def admin_cortex_identity_org_link_replay_jobs_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> AdminCortexOrgLinkReplayJobListResponse:
        """Phase 04 Step 10 — list recent org link replay jobs."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_link_replay_runtime import (
            ORG_LINK_REPLAY_SCHEMA_VERSION,
            list_org_link_replay_jobs,
            org_link_replay_job_public_dict,
        )

        jobs = list_org_link_replay_jobs(db, tenant_id=tenant_id, limit=limit)
        return AdminCortexOrgLinkReplayJobListResponse(
            org_link_replay_schema_version=ORG_LINK_REPLAY_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            jobs=[AdminCortexOrgLinkReplayJobItem.model_validate(org_link_replay_job_public_dict(j)) for j in jobs],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/replay-jobs/{job_id}",
        response_model=AdminCortexOrgLinkReplayJobDetailResponse,
    )
    def admin_cortex_identity_org_link_replay_job_detail(
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgLinkReplayJobDetailResponse:
        """Phase 04 Step 10 — org link replay job + receipts."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_link_replay_runtime import (
            ORG_LINK_REPLAY_SCHEMA_VERSION,
            get_org_link_replay_job,
            org_link_replay_job_public_dict,
            org_link_replay_receipt_public_dict,
        )

        job = get_org_link_replay_job(db, tenant_id=tenant_id, job_id=job_id)
        if job is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="org_link_replay_job_not_found")
        receipts = sorted(job.receipts, key=lambda r: r.id)
        return AdminCortexOrgLinkReplayJobDetailResponse(
            org_link_replay_schema_version=ORG_LINK_REPLAY_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            job=AdminCortexOrgLinkReplayJobItem.model_validate(org_link_replay_job_public_dict(job)),
            receipts=[
                AdminCortexOrgLinkReplayJobReceiptItem.model_validate(org_link_replay_receipt_public_dict(r))
                for r in receipts
            ],
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/replay-jobs/enqueue",
        response_model=AdminCortexOrgLinkReplayJobEnqueueResponse,
    )
    def admin_cortex_identity_org_link_replay_job_enqueue(
        tenant_id: uuid.UUID,
        body: AdminCortexOrgLinkReplayJobEnqueueRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgLinkReplayJobEnqueueResponse:
        """Phase 04 Step 19 — queue org link replay / projection export job + Celery worker."""
        _assert_tenant(db, tenant_id)
        from app.tasks.cortex_org_link_jobs import run_org_link_replay_job_task
        from vector.domains.cortex.identity.org_link_replay_runtime import (
            ORG_LINK_REPLAY_SCHEMA_VERSION,
            OrgLinkReplayError,
            create_queued_org_link_replay_job,
            org_link_replay_job_public_dict,
        )

        try:
            job = create_queued_org_link_replay_job(
                db,
                tenant_id=tenant_id,
                job_kind=body.job_kind,
                pinned_rule_version=body.pinned_rule_version,
                dry_run=body.dry_run,
                scope_json=body.scope_json,
            )
            db.flush()
        except OrgLinkReplayError as exc:
            db.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        try:
            async_result = run_org_link_replay_job_task.delay(
                str(tenant_id),
                body.job_kind,
                body.pinned_rule_version,
                body.dry_run,
                body.scope_json,
                str(job.id),
            )
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"celery_enqueue_failed:{exc}",
            ) from exc
        job.celery_task_id = str(async_result.id)
        db.commit()
        db.refresh(job)
        path = f"/admin/tenants/{tenant_id}/cortex/identity/worker-tasks/{async_result.id}"
        return AdminCortexOrgLinkReplayJobEnqueueResponse(
            org_link_replay_schema_version=ORG_LINK_REPLAY_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            celery_task_id=str(async_result.id),
            worker_task_status_path=path,
            job=AdminCortexOrgLinkReplayJobItem.model_validate(org_link_replay_job_public_dict(job)),
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/worker-tasks/{celery_task_id}",
        response_model=AdminCortexIdentityWorkerTaskStatusResponse,
    )
    def admin_cortex_identity_worker_task_status(
        tenant_id: uuid.UUID,
        celery_task_id: str,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexIdentityWorkerTaskStatusResponse:
        """Phase 04 Step 19 — poll Celery state for tasks bound to this tenant (replay job or dispatch row)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.worker_dispatch import (
            build_worker_task_status_payload,
            resolve_worker_task_binding,
        )

        try:
            bind_kind, job_uuid = resolve_worker_task_binding(
                db, tenant_id=tenant_id, celery_task_id=celery_task_id
            )
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="worker_task_not_found_for_tenant") from exc
        payload = build_worker_task_status_payload(
            celery_task_id=celery_task_id.strip(),
            bind_kind=bind_kind,
            job_id=job_uuid,
        )
        payload["tenant_id"] = str(tenant_id)
        return AdminCortexIdentityWorkerTaskStatusResponse.model_validate(payload)

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/link-rule-versions",
        response_model=AdminCortexLinkRuleVersionDetailResponse,
    )
    def admin_cortex_identity_link_rule_version_append(
        tenant_id: uuid.UUID,
        body: AdminCortexLinkRuleVersionCreateRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexLinkRuleVersionDetailResponse:
        """Phase 04 Step 11 — register a frozen linkage rule manifest (semantic_version + hash)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.linkage_rules import (
            LINK_RULE_VERSION_SCHEMA_VERSION,
            LinkageRulesError,
            create_link_rule_version,
            link_rule_version_public_dict,
        )

        try:
            row = create_link_rule_version(
                db,
                tenant_id=tenant_id,
                semantic_version=body.semantic_version,
                rules_manifest_json=body.rules_manifest_json,
                lifecycle_state=body.lifecycle_state,
                notes=body.notes,
            )
            db.commit()
        except LinkageRulesError as exc:
            db.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return AdminCortexLinkRuleVersionDetailResponse(
            link_rule_version_schema_version=LINK_RULE_VERSION_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            version=AdminCortexLinkRuleVersionItem.model_validate(link_rule_version_public_dict(row)),
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/link-rule-versions",
        response_model=AdminCortexLinkRuleVersionListResponse,
    )
    def admin_cortex_identity_link_rule_versions_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> AdminCortexLinkRuleVersionListResponse:
        """Phase 04 Step 11 — list linkage rule versions for operator readout."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.linkage_rules import (
            LINK_RULE_VERSION_SCHEMA_VERSION,
            link_rule_version_public_dict,
            list_link_rule_versions,
        )

        rows = list_link_rule_versions(db, tenant_id=tenant_id, limit=limit)
        return AdminCortexLinkRuleVersionListResponse(
            link_rule_version_schema_version=LINK_RULE_VERSION_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            versions=[AdminCortexLinkRuleVersionItem.model_validate(link_rule_version_public_dict(r)) for r in rows],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/link-rule-versions/{rule_version_id}",
        response_model=AdminCortexLinkRuleVersionDetailResponse,
    )
    def admin_cortex_identity_link_rule_version_detail(
        tenant_id: uuid.UUID,
        rule_version_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexLinkRuleVersionDetailResponse:
        """Phase 04 Step 11 — one linkage rule version row."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.linkage_rules import (
            LINK_RULE_VERSION_SCHEMA_VERSION,
            get_link_rule_version,
            link_rule_version_public_dict,
        )

        row = get_link_rule_version(db, tenant_id=tenant_id, rule_version_id=rule_version_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="link_rule_version_not_found")
        return AdminCortexLinkRuleVersionDetailResponse(
            link_rule_version_schema_version=LINK_RULE_VERSION_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            version=AdminCortexLinkRuleVersionItem.model_validate(link_rule_version_public_dict(row)),
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/primitive-instances",
        response_model=AdminCortexOrgPrimitiveInstanceDetailResponse,
    )
    def admin_cortex_identity_primitive_instance_append(
        tenant_id: uuid.UUID,
        body: AdminCortexOrgPrimitiveInstanceAppendRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgPrimitiveInstanceDetailResponse:
        """Phase 04 Step 12 — persist execution primitive envelope (evidence-bound) on an org entity."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.execution_primitives import (
            ORG_PRIMITIVE_INSTANCE_SCHEMA_VERSION,
            PrimitivePersistenceError,
            append_org_primitive_instance,
            org_primitive_instance_public_dict,
        )

        try:
            row = append_org_primitive_instance(
                db,
                tenant_id=tenant_id,
                org_entity_id=body.org_entity_id,
                envelope_json=body.envelope_json,
                lifecycle_state=body.lifecycle_state,
            )
            db.commit()
        except PrimitivePersistenceError as exc:
            db.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return AdminCortexOrgPrimitiveInstanceDetailResponse(
            org_primitive_instance_schema_version=ORG_PRIMITIVE_INSTANCE_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            instance=AdminCortexOrgPrimitiveInstanceItem.model_validate(org_primitive_instance_public_dict(row)),
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/primitive-instances",
        response_model=AdminCortexOrgPrimitiveInstanceListResponse,
    )
    def admin_cortex_identity_primitive_instances_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> AdminCortexOrgPrimitiveInstanceListResponse:
        """Phase 04 Step 12 — list execution primitive instances (operator inspector)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.execution_primitives import (
            ORG_PRIMITIVE_INSTANCE_SCHEMA_VERSION,
            list_org_primitive_instances,
            org_primitive_instance_public_dict,
        )

        rows = list_org_primitive_instances(db, tenant_id=tenant_id, limit=limit)
        return AdminCortexOrgPrimitiveInstanceListResponse(
            org_primitive_instance_schema_version=ORG_PRIMITIVE_INSTANCE_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            instances=[
                AdminCortexOrgPrimitiveInstanceItem.model_validate(org_primitive_instance_public_dict(r)) for r in rows
            ],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/primitive-instances/{instance_id}",
        response_model=AdminCortexOrgPrimitiveInstanceDetailResponse,
    )
    def admin_cortex_identity_primitive_instance_detail(
        tenant_id: uuid.UUID,
        instance_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgPrimitiveInstanceDetailResponse:
        """Phase 04 Step 12 — one execution primitive instance."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.execution_primitives import (
            ORG_PRIMITIVE_INSTANCE_SCHEMA_VERSION,
            get_org_primitive_instance,
            org_primitive_instance_public_dict,
        )

        row = get_org_primitive_instance(db, tenant_id=tenant_id, instance_id=instance_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="org_primitive_instance_not_found")
        return AdminCortexOrgPrimitiveInstanceDetailResponse(
            org_primitive_instance_schema_version=ORG_PRIMITIVE_INSTANCE_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            instance=AdminCortexOrgPrimitiveInstanceItem.model_validate(org_primitive_instance_public_dict(row)),
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/graph-projection",
        response_model=AdminCortexOrgGraphProjectionResponse,
    )
    def admin_cortex_identity_graph_projection(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgGraphProjectionResponse:
        """Phase 04 Step 13 — OrgGraphProjectionV1 export (deterministic JSON + SHA-256)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.projection_export import (
            build_org_graph_projection_export_document,
        )

        doc = build_org_graph_projection_export_document(db, tenant_id=tenant_id)
        return AdminCortexOrgGraphProjectionResponse.model_validate(doc)

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/org-ambiguities",
        response_model=AdminCortexOrgAmbiguityDetailResponse,
    )
    def admin_cortex_identity_org_ambiguity_append(
        tenant_id: uuid.UUID,
        body: AdminCortexOrgAmbiguityAppendRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgAmbiguityDetailResponse:
        """Phase 04 Step 14 — append org-scoped multiplicity ambiguity receipt."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_ambiguity import (
            ORG_AMBIGUITY_SCHEMA_VERSION,
            OrgAmbiguityError,
            append_org_ambiguity_record,
            org_ambiguity_record_public_dict,
        )

        try:
            row = append_org_ambiguity_record(
                db,
                tenant_id=tenant_id,
                org_ambiguity_class=body.org_ambiguity_class,
                subject_key=body.subject_key,
                involved_org_entity_ids=body.involved_org_entity_ids,
                status=body.status,
                evidence_json=body.evidence_json,
                operator_note=body.operator_note,
            )
            db.commit()
        except OrgAmbiguityError as exc:
            db.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return AdminCortexOrgAmbiguityDetailResponse(
            org_ambiguity_schema_version=ORG_AMBIGUITY_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            record=AdminCortexOrgAmbiguityItem.model_validate(org_ambiguity_record_public_dict(row)),
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/org-ambiguities",
        response_model=AdminCortexOrgAmbiguityListResponse,
    )
    def admin_cortex_identity_org_ambiguities_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        status: Annotated[str | None, Query()] = None,
        org_ambiguity_class: Annotated[str | None, Query()] = None,
    ) -> AdminCortexOrgAmbiguityListResponse:
        """Phase 04 Step 14 — list org ambiguity receipts (unresolved actors queue)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_ambiguity import (
            ORG_AMBIGUITY_SCHEMA_VERSION,
            list_org_ambiguity_records,
            org_ambiguity_record_public_dict,
        )

        rows = list_org_ambiguity_records(
            db,
            tenant_id=tenant_id,
            limit=limit,
            status=status,
            org_ambiguity_class=org_ambiguity_class,
        )
        return AdminCortexOrgAmbiguityListResponse(
            org_ambiguity_schema_version=ORG_AMBIGUITY_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            records=[
                AdminCortexOrgAmbiguityItem.model_validate(org_ambiguity_record_public_dict(r)) for r in rows
            ],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/org-ambiguities/{record_id}",
        response_model=AdminCortexOrgAmbiguityDetailResponse,
    )
    def admin_cortex_identity_org_ambiguity_detail(
        tenant_id: uuid.UUID,
        record_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgAmbiguityDetailResponse:
        """Phase 04 Step 14 — one org ambiguity record."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_ambiguity import (
            ORG_AMBIGUITY_SCHEMA_VERSION,
            get_org_ambiguity_record,
            org_ambiguity_record_public_dict,
        )

        row = get_org_ambiguity_record(db, tenant_id=tenant_id, record_id=record_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="org_ambiguity_record_not_found")
        return AdminCortexOrgAmbiguityDetailResponse(
            org_ambiguity_schema_version=ORG_AMBIGUITY_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            record=AdminCortexOrgAmbiguityItem.model_validate(org_ambiguity_record_public_dict(row)),
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/verification/run",
        response_model=AdminCortexOrgIdentityVerificationRunResponse,
    )
    def admin_cortex_identity_verification_run(
        tenant_id: uuid.UUID,
        body: AdminCortexOrgIdentityVerificationRunRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgIdentityVerificationRunResponse:
        """Phase 04 Step 15 — Phase 04 gate slice from canonical verification + optional org ledger row."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_verification_metadata import (
            ORG_IDENTITY_VERIFICATION_ENGINE_SCHEMA_VERSION,
        )
        from vector.domains.cortex.identity.verification import run_org_identity_verification

        raw = run_org_identity_verification(
            db,
            tenant_id=tenant_id,
            materialization_sample_limit=body.materialization_sample_limit,
            persist=body.persist,
        )
        gates = [AdminCortexCanonicalVerificationGateResult.model_validate(g) for g in raw["gates"]]
        return AdminCortexOrgIdentityVerificationRunResponse(
            org_identity_verification_engine_schema_version=ORG_IDENTITY_VERIFICATION_ENGINE_SCHEMA_VERSION,
            tenant_id=raw["tenant_id"],
            passed=raw["passed"],
            gates=gates,
            evidence=raw["evidence"],
            persisted_run_id=raw.get("persisted_run_id"),
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/verification/runs",
        response_model=AdminCortexOrgIdentityVerificationRunsListResponse,
    )
    def admin_cortex_identity_verification_runs(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> AdminCortexOrgIdentityVerificationRunsListResponse:
        """Phase 04 Step 15 — recent persisted Phase 04 verification slice runs."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_verification_metadata import (
            ORG_IDENTITY_VERIFICATION_ENGINE_SCHEMA_VERSION,
        )
        from vector.domains.cortex.identity.verification import (
            list_org_identity_verification_runs,
            org_verification_run_public_dict,
        )

        rows = list_org_identity_verification_runs(db, tenant_id=tenant_id, limit=limit)
        items: list[AdminCortexOrgIdentityVerificationRunItem] = []
        for row in rows:
            d = org_verification_run_public_dict(row)
            items.append(
                AdminCortexOrgIdentityVerificationRunItem(
                    id=d["id"],
                    tenant_id=d["tenant_id"],
                    engine_schema_version=d["engine_schema_version"],
                    passed=d["passed"],
                    gates=[AdminCortexCanonicalVerificationGateResult.model_validate(x) for x in d["gates_json"]],
                    evidence=d["evidence_json"],
                    created_at=d["created_at"],
                )
            )
        return AdminCortexOrgIdentityVerificationRunsListResponse(
            org_identity_verification_engine_schema_version=ORG_IDENTITY_VERIFICATION_ENGINE_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            runs=items,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/merge-queue",
        response_model=AdminCortexMergeQueueListResponse,
    )
    def admin_cortex_identity_merge_queue_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
    ) -> AdminCortexMergeQueueListResponse:
        """Phase 04 Step 18 — merge proposals view (**org_merge_queue_row_v1**)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.merge_governance import MERGE_GOVERNANCE_SCHEMA_VERSION
        from vector.domains.cortex.identity.operator_console import (
            list_org_merge_queue_rows,
            org_merge_queue_row_v1,
        )

        merges = list_org_merge_queue_rows(db, tenant_id=tenant_id, limit=limit)
        proposals = [org_merge_queue_row_v1(db, m) for m in merges]
        return AdminCortexMergeQueueListResponse(
            merge_governance_schema_version=MERGE_GOVERNANCE_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            proposals=[AdminCortexMergeQueueRowV1.model_validate(x) for x in proposals],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/merge-queue/{merge_proposal_id}",
        response_model=AdminCortexMergeQueueDetailResponse,
    )
    def admin_cortex_identity_merge_queue_detail(
        tenant_id: uuid.UUID,
        merge_proposal_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexMergeQueueDetailResponse:
        """Phase 04 Step 18 — merge proposal detail (queue row + full merge ledger row)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.merge_governance import (
            MERGE_GOVERNANCE_SCHEMA_VERSION,
            get_org_merge,
            merge_public_dict,
        )
        from vector.domains.cortex.identity.operator_console import org_merge_queue_row_v1

        row = get_org_merge(db, tenant_id=tenant_id, merge_id=merge_proposal_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="merge_proposal_not_found")
        prop = org_merge_queue_row_v1(db, row)
        return AdminCortexMergeQueueDetailResponse(
            merge_governance_schema_version=MERGE_GOVERNANCE_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            proposal=AdminCortexMergeQueueRowV1.model_validate(prop),
            merge=AdminCortexOrgMergeItem.model_validate(merge_public_dict(row)),
        )

    def _merge_queue_action(
        tenant_id: uuid.UUID,
        merge_proposal_id: uuid.UUID,
        body: AdminCortexIdentityOperatorActionRequest,
        db: Session,
        *,
        action: str,
    ) -> AdminCortexOrgMergeItem:
        from vector.domains.cortex.identity.merge_governance import merge_public_dict
        from vector.domains.cortex.identity.operator_console import (
            OperatorConsoleError,
            apply_merge_queue_action,
        )

        try:
            row = apply_merge_queue_action(
                db,
                tenant_id=tenant_id,
                merge_id=merge_proposal_id,
                action=action,
                confirmation_phrase=body.confirmation_phrase,
                operator_note=body.operator_note,
            )
            db.commit()
        except OperatorConsoleError as exc:
            db.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return AdminCortexOrgMergeItem.model_validate(merge_public_dict(row))

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/merge-queue/{merge_proposal_id}/approve",
        response_model=AdminCortexOrgMergeItem,
    )
    def admin_cortex_identity_merge_queue_approve(
        tenant_id: uuid.UUID,
        merge_proposal_id: uuid.UUID,
        body: AdminCortexIdentityOperatorActionRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgMergeItem:
        """Phase 04 Step 18 — approve merge proposal (metadata transition + audit)."""
        _assert_tenant(db, tenant_id)
        return _merge_queue_action(
            tenant_id, merge_proposal_id, body, db, action="approve"
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/merge-queue/{merge_proposal_id}/reject",
        response_model=AdminCortexOrgMergeItem,
    )
    def admin_cortex_identity_merge_queue_reject(
        tenant_id: uuid.UUID,
        merge_proposal_id: uuid.UUID,
        body: AdminCortexIdentityOperatorActionRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgMergeItem:
        _assert_tenant(db, tenant_id)
        return _merge_queue_action(
            tenant_id, merge_proposal_id, body, db, action="reject"
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/merge-queue/{merge_proposal_id}/defer",
        response_model=AdminCortexOrgMergeItem,
    )
    def admin_cortex_identity_merge_queue_defer(
        tenant_id: uuid.UUID,
        merge_proposal_id: uuid.UUID,
        body: AdminCortexIdentityOperatorActionRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgMergeItem:
        _assert_tenant(db, tenant_id)
        return _merge_queue_action(
            tenant_id, merge_proposal_id, body, db, action="defer"
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/merge-queue/{merge_proposal_id}/split",
        response_model=AdminCortexOrgMergeItem,
    )
    def admin_cortex_identity_merge_queue_split(
        tenant_id: uuid.UUID,
        merge_proposal_id: uuid.UUID,
        body: AdminCortexIdentityOperatorActionRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgMergeItem:
        _assert_tenant(db, tenant_id)
        return _merge_queue_action(
            tenant_id, merge_proposal_id, body, db, action="split"
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/ambiguity-queue",
        response_model=AdminCortexAmbiguityQueueListResponse,
    )
    def admin_cortex_identity_ambiguity_queue_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> AdminCortexAmbiguityQueueListResponse:
        """Phase 04 Step 18 — ambiguity queue rows (**org_ambiguity_queue_row_v1**)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.operator_console import org_ambiguity_queue_row_v1
        from vector.domains.cortex.identity.org_ambiguity import (
            ORG_AMBIGUITY_SCHEMA_VERSION,
            list_org_ambiguity_records,
        )

        rows = list_org_ambiguity_records(db, tenant_id=tenant_id, limit=limit)
        qrows = [org_ambiguity_queue_row_v1(r) for r in rows]
        return AdminCortexAmbiguityQueueListResponse(
            org_ambiguity_schema_version=ORG_AMBIGUITY_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            rows=[AdminCortexOrgAmbiguityQueueRowV1.model_validate(x) for x in qrows],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/ambiguity-queue/{ambiguity_id}",
        response_model=AdminCortexOrgAmbiguityDetailResponse,
    )
    def admin_cortex_identity_ambiguity_queue_detail(
        tenant_id: uuid.UUID,
        ambiguity_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgAmbiguityDetailResponse:
        """Phase 04 Step 18 — ambiguity inspector (same contract as ``…/org-ambiguities/{id}``)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_ambiguity import (
            ORG_AMBIGUITY_SCHEMA_VERSION,
            get_org_ambiguity_record,
            org_ambiguity_record_public_dict,
        )

        row = get_org_ambiguity_record(db, tenant_id=tenant_id, record_id=ambiguity_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="org_ambiguity_record_not_found")
        return AdminCortexOrgAmbiguityDetailResponse(
            org_ambiguity_schema_version=ORG_AMBIGUITY_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            record=AdminCortexOrgAmbiguityItem.model_validate(org_ambiguity_record_public_dict(row)),
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/primitives",
        response_model=AdminCortexPrimitiveExplorerListResponse,
    )
    def admin_cortex_identity_primitives_explorer_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        include_raw_envelope: Annotated[bool, Query()] = False,
    ) -> AdminCortexPrimitiveExplorerListResponse:
        """Phase 04 Step 18 — primitive explorer defaulting to structured rows without raw blob (**G-P04-26**)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.execution_primitives import (
            ORG_PRIMITIVE_INSTANCE_SCHEMA_VERSION,
            list_org_primitive_instances,
        )
        from vector.domains.cortex.identity.operator_console import org_primitive_list_row_v1

        rows = list_org_primitive_instances(db, tenant_id=tenant_id, limit=limit)
        out = [org_primitive_list_row_v1(r, include_raw_envelope=include_raw_envelope) for r in rows]
        return AdminCortexPrimitiveExplorerListResponse(
            org_primitive_instance_schema_version=ORG_PRIMITIVE_INSTANCE_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            include_raw_envelope=include_raw_envelope,
            rows=[AdminCortexOrgPrimitiveListRowV1.model_validate(x) for x in out],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/primitives/{primitive_id}",
        response_model=AdminCortexOrgPrimitiveInstanceDetailResponse,
    )
    def admin_cortex_identity_primitive_explorer_detail(
        tenant_id: uuid.UUID,
        primitive_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgPrimitiveInstanceDetailResponse:
        """Phase 04 Step 18 — primitive inspector (full envelope, same as ``…/primitive-instances/{id}``)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.execution_primitives import (
            ORG_PRIMITIVE_INSTANCE_SCHEMA_VERSION,
            get_org_primitive_instance,
            org_primitive_instance_public_dict,
        )

        row = get_org_primitive_instance(db, tenant_id=tenant_id, instance_id=primitive_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="org_primitive_instance_not_found")
        return AdminCortexOrgPrimitiveInstanceDetailResponse(
            org_primitive_instance_schema_version=ORG_PRIMITIVE_INSTANCE_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            instance=AdminCortexOrgPrimitiveInstanceItem.model_validate(org_primitive_instance_public_dict(row)),
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/projection-preview",
        response_model=AdminCortexOrgProjectionPreviewResponse,
    )
    def admin_cortex_identity_projection_preview(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgProjectionPreviewResponse:
        """Phase 04 Step 18 — graph export preview metadata only (**§14**, **G-P04-25**)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.projection_export import (
            build_org_graph_projection_preview_metadata,
        )

        raw = build_org_graph_projection_preview_metadata(db, tenant_id=tenant_id)
        return AdminCortexOrgProjectionPreviewResponse.model_validate(raw)

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/projection-export/run",
        response_model=AdminCortexOrgLinkReplayJobEnqueueResponse,
    )
    def admin_cortex_identity_projection_export_run(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgLinkReplayJobEnqueueResponse:
        """Phase 04 Step 19 — enqueue async OrgGraphProjectionV1 export via org link replay job pipeline."""
        _assert_tenant(db, tenant_id)
        from app.tasks.cortex_org_link_jobs import run_org_link_replay_job_task
        from vector.domains.cortex.identity.org_link_replay_runtime import (
            ORG_LINK_REPLAY_SCHEMA_VERSION,
            create_queued_org_link_replay_job,
            org_link_replay_job_public_dict,
        )

        job = create_queued_org_link_replay_job(
            db,
            tenant_id=tenant_id,
            job_kind="graph_projection_export",
            dry_run=False,
        )
        db.flush()
        try:
            async_result = run_org_link_replay_job_task.delay(
                str(tenant_id),
                "graph_projection_export",
                None,
                False,
                None,
                str(job.id),
            )
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"celery_enqueue_failed:{exc}",
            ) from exc
        job.celery_task_id = str(async_result.id)
        db.commit()
        db.refresh(job)
        path = f"/admin/tenants/{tenant_id}/cortex/identity/worker-tasks/{async_result.id}"
        return AdminCortexOrgLinkReplayJobEnqueueResponse(
            org_link_replay_schema_version=ORG_LINK_REPLAY_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            celery_task_id=str(async_result.id),
            worker_task_status_path=path,
            job=AdminCortexOrgLinkReplayJobItem.model_validate(org_link_replay_job_public_dict(job)),
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/control-plane",
        response_model=AdminCortexIdentityControlPlaneResponse,
    )
    def admin_cortex_identity_control_plane(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexIdentityControlPlaneResponse:
        """Phase 04 Step 17 — Identity Dashboard aggregate (**identity_control_plane_v1**)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.control_plane import build_identity_control_plane

        raw = build_identity_control_plane(db, tenant_id=tenant_id)
        return AdminCortexIdentityControlPlaneResponse.model_validate(raw)

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/rebuild-continuity",
        response_model=AdminCortexIdentityContinuityRebuildResponse,
    )
    def admin_cortex_identity_rebuild_continuity(
        tenant_id: uuid.UUID,
        body: AdminCortexIdentityContinuityRebuildRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexIdentityContinuityRebuildResponse:
        """Deterministic Phase 04 continuity rebuild: materialize drain → repair → anchor backfill → candidates."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.transform_runtime import MaterializeError
        from vector.domains.cortex.identity.continuity_rebuild import run_identity_continuity_rebuild

        try:
            report = run_identity_continuity_rebuild(
                db,
                tenant_id=tenant_id,
                bundle_id=body.bundle_id.strip(),
                materialize_batch_limit=body.materialize_batch_limit,
                anchor_limit=body.anchor_limit,
                run_determinism_repair=body.run_determinism_repair,
                dry_run=body.dry_run,
                replay_job=None,
            )
            db.commit()
        except MaterializeError as exc:
            db.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"identity_continuity_rebuild_failed:{exc}",
            ) from exc
        return AdminCortexIdentityContinuityRebuildResponse(rebuild=report)

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/continuity-fixture-verify",
        response_model=AdminCortexIdentityContinuityVerifyResponse,
    )
    def admin_cortex_identity_continuity_fixture_verify(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        sample_limit: Annotated[int, Query(ge=50, le=5000)] = 800,
    ) -> AdminCortexIdentityContinuityVerifyResponse:
        """Read-only: substrate row counts + raw payload continuity_fixture field hits (hostile proof)."""
        _assert_tenant(db, tenant_id)
        from mock_connectors.fixtures.phase04_continuity_fixtures import resolve_phase04_continuity_scenario_key
        from vector.domains.cortex.identity.continuity_rebuild import (
            substrate_counts,
            verify_continuity_fixture_pressure,
        )

        counts = substrate_counts(db, tenant_id=tenant_id)
        pressure = verify_continuity_fixture_pressure(db, tenant_id=tenant_id, sample_limit=sample_limit)
        return AdminCortexIdentityContinuityVerifyResponse(
            scenario_key=resolve_phase04_continuity_scenario_key(),
            substrate_counts=counts,
            fixture_pressure=pressure,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/debug-anchor-evidence",
        response_model=AdminCortexIdentityContinuityEvidenceInspectResponse,
    )
    def admin_cortex_identity_debug_anchor_evidence(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        anchor_scan_limit: Annotated[int, Query(ge=1, le=100_000)] = 50_000,
        sample_limit: Annotated[int, Query(ge=1, le=200)] = 30,
        fixture_survival_sample_limit: Annotated[int, Query(ge=1, le=500)] = 40,
    ) -> AdminCortexIdentityContinuityEvidenceInspectResponse:
        """Read-only: where continuity join keys come from (raw vs canonical) + skip reasons + kind collapse."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.continuity_evidence_inspector import (
            build_continuity_evidence_inspection_for_tenant,
        )

        raw = build_continuity_evidence_inspection_for_tenant(
            db,
            tenant_id=tenant_id,
            anchor_scan_limit=anchor_scan_limit,
            sample_limit=sample_limit,
            fixture_survival_sample_limit=fixture_survival_sample_limit,
        )
        return AdminCortexIdentityContinuityEvidenceInspectResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/readiness-economics",
        response_model=AdminCortexIdentityReadinessEconomicsResponse,
    )
    def admin_cortex_identity_readiness_economics(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexIdentityReadinessEconomicsResponse:
        """Phase 04 Step 21 — readiness economics snapshot (**identity_readiness_economics_v1**)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.readiness_economics import (
            build_identity_readiness_economics,
        )

        raw = build_identity_readiness_economics(db, tenant_id=tenant_id)
        return AdminCortexIdentityReadinessEconomicsResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/certification-pack",
        response_model=AdminCortexOrgIdentityCertificationPackResponse,
    )
    def admin_cortex_org_identity_certification_pack_snapshot(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        materialization_sample_limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> AdminCortexOrgIdentityCertificationPackResponse:
        """Phase 04 Step 22 — org identity closure certification pack (pre-archive)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_identity_certification_pack import (
            build_org_identity_certification_pack,
        )

        raw = build_org_identity_certification_pack(
            db,
            tenant_id=tenant_id,
            materialization_sample_limit=materialization_sample_limit,
        )
        return AdminCortexOrgIdentityCertificationPackResponse.model_validate(raw)

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/certification-pack/archive",
        response_model=AdminCortexOrgIdentityCertificationArchiveResponse,
    )
    def admin_cortex_org_identity_certification_pack_archive(
        tenant_id: uuid.UUID,
        body: AdminCortexOrgIdentityCertificationArchiveRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgIdentityCertificationArchiveResponse:
        """Phase 04 Step 22 — persist org certification pack when all hard-fail closure rows pass."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_identity_certification_pack import (
            ORG_IDENTITY_CERTIFICATION_PACK_SCHEMA_VERSION,
            persist_org_identity_certification_archive,
        )

        raw = persist_org_identity_certification_archive(
            db,
            tenant_id=tenant_id,
            materialization_sample_limit=body.materialization_sample_limit,
        )
        pack = raw["pack"]
        db.commit()
        return AdminCortexOrgIdentityCertificationArchiveResponse(
            persisted=bool(raw["persisted"]),
            passed=bool(raw["passed"]),
            archive_id=raw.get("archive_id"),
            org_certification_pack_schema_version=int(
                pack.get("org_certification_pack_schema_version") or ORG_IDENTITY_CERTIFICATION_PACK_SCHEMA_VERSION
            ),
            tenant_id=str(tenant_id),
            pack=pack,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/certification-pack/archives",
        response_model=AdminCortexOrgIdentityCertificationArchivesListResponse,
    )
    def admin_cortex_org_identity_certification_pack_archives(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> AdminCortexOrgIdentityCertificationArchivesListResponse:
        """Phase 04 Step 22 — recent org identity certification archives."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_identity_certification_pack import (
            ORG_IDENTITY_CERTIFICATION_PACK_SCHEMA_VERSION,
            list_org_identity_certification_archives,
            org_certification_archive_public_dict,
        )

        rows = list_org_identity_certification_archives(db, tenant_id=tenant_id, limit=limit)
        items = [
            AdminCortexOrgIdentityCertificationArchiveItem.model_validate(org_certification_archive_public_dict(r))
            for r in rows
        ]
        return AdminCortexOrgIdentityCertificationArchivesListResponse(
            org_certification_pack_schema_version=ORG_IDENTITY_CERTIFICATION_PACK_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            archives=items,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/certification-pack/archives/{archive_id}",
        response_model=AdminCortexOrgIdentityCertificationArchiveDetailResponse,
    )
    def admin_cortex_org_identity_certification_pack_archive_detail(
        tenant_id: uuid.UUID,
        archive_id: int,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgIdentityCertificationArchiveDetailResponse:
        """Phase 04 Step 22 — fetch one org certification archive (full JSON)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.org_identity_certification_pack import (
            get_org_identity_certification_archive,
        )

        row = get_org_identity_certification_archive(db, tenant_id=tenant_id, archive_id=archive_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Org certification archive not found.") from None
        return AdminCortexOrgIdentityCertificationArchiveDetailResponse(
            id=row.id,
            tenant_id=str(row.tenant_id),
            org_certification_pack_schema_version=row.org_certification_pack_schema_version,
            passed=row.passed,
            created_at=row.created_at,
            pack=dict(row.pack_json),
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/backfill/from-canonical-anchors",
        response_model=AdminCortexIdentityBackfillFromAnchorsResponse,
    )
    def admin_cortex_identity_backfill_from_canonical_anchors(
        tenant_id: uuid.UUID,
        body: AdminCortexIdentityBackfillFromAnchorsRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexIdentityBackfillFromAnchorsResponse:
        """Phase 04 Step 20 — upsert org handles from Phase 03 identity anchors (candidate lane only)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.backfill import (
            run_anchor_handle_backfill,
        )

        raw = run_anchor_handle_backfill(
            db,
            tenant_id=tenant_id,
            dry_run=body.dry_run,
            anchor_limit=body.anchor_limit,
        )
        db.commit()
        return AdminCortexIdentityBackfillFromAnchorsResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/backfill/runs",
        response_model=AdminCortexIdentityBackfillRunsListResponse,
    )
    def admin_cortex_identity_backfill_runs(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> AdminCortexIdentityBackfillRunsListResponse:
        """Phase 04 Step 20 — recent anchor→handle backfill audit rows."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.backfill import (
            ORG_IDENTITY_BACKFILL_SCHEMA_VERSION,
            list_org_identity_backfill_runs,
            org_identity_backfill_run_public_dict,
        )

        rows = list_org_identity_backfill_runs(db, tenant_id=tenant_id, limit=limit)
        return AdminCortexIdentityBackfillRunsListResponse(
            org_identity_backfill_schema_version=ORG_IDENTITY_BACKFILL_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            runs=[AdminCortexIdentityBackfillRunItem.model_validate(org_identity_backfill_run_public_dict(r)) for r in rows],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identity/failures",
        response_model=AdminCortexOrgFailuresResponse,
    )
    def admin_cortex_identity_failures(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgFailuresResponse:
        """Phase 04 Step 16 — active org failure cases + recent org remediation validations."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.failure_remediation import (
            ORG_FAILURE_REMEDIATION_RUNTIME_SCHEMA_VERSION,
            org_failure_case_public_dict,
            org_remediation_validation_public_dict,
            sync_org_failure_cases,
        )

        raw = sync_org_failure_cases(db, tenant_id)
        cases = [AdminCortexOrgFailureCaseItem.model_validate(org_failure_case_public_dict(c)) for c in raw["cases"]]
        vals = [
            AdminCortexOrgRemediationValidationItem.model_validate(org_remediation_validation_public_dict(v))
            for v in raw["recent_remediation_validations"]
        ]
        return AdminCortexOrgFailuresResponse(
            org_failure_remediation_runtime_schema_version=ORG_FAILURE_REMEDIATION_RUNTIME_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            active_failure_count=raw["active_failure_count"],
            active_failure_classes=raw["active_failure_classes"],
            cases=cases,
            recent_remediation_validations=vals,
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/identity/remediation/validate",
        response_model=AdminCortexOrgRemediationValidateResponse,
    )
    def admin_cortex_identity_remediation_validate(
        tenant_id: uuid.UUID,
        body: AdminCortexOrgRemediationValidateRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOrgRemediationValidateResponse:
        """Phase 04 Step 16 — policy-gated org remediation (ambiguity triage ack or org link replay retry)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.identity.failure_remediation import (
            validate_org_remediation,
        )

        raw = validate_org_remediation(
            db,
            tenant_id=tenant_id,
            remediation_class=body.remediation_class,
            dry_run=body.dry_run,
            confirm_execution=body.confirm_execution,
            failure_case_gap_id=body.failure_case_gap_id,
            payload=body.payload,
        )
        return AdminCortexOrgRemediationValidateResponse(
            tenant_id=raw["tenant_id"],
            remediation_class=raw["remediation_class"],
            validation=AdminCortexOrgRemediationValidationItem.model_validate(raw["validation"]),
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/canonical/replay-jobs/run",
        response_model=AdminCortexReplayJobDetailResponse,
    )
    def admin_cortex_canonical_replay_job_run(
        tenant_id: uuid.UUID,
        body: AdminCortexReplayJobRunRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexReplayJobDetailResponse:
        """Phase 03 Step 10 — pinned-bundle rebuild/regeneration with C0–C5 divergence receipts."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.replay_runtime import (
            REPLAY_RUNTIME_SCHEMA_VERSION,
            ReplayJobError,
            execute_canonical_replay_job,
            replay_job_public_dict,
            replay_receipt_public_dict,
        )

        try:
            job = execute_canonical_replay_job(
                db,
                tenant_id=tenant_id,
                pinned_bundle_id=body.pinned_bundle_id,
                job_kind=body.job_kind,
                raw_record_ids=body.raw_record_ids,
                source_bundle_id=body.source_bundle_id,
                dry_run=body.dry_run,
                connector=body.connector,
                resource_type=body.resource_type,
                include_dependency_neighborhood=body.include_dependency_neighborhood,
                subtree_anchor_raw_record_id=body.subtree_anchor_raw_record_id,
                parent_anchor_raw_record_id=body.parent_anchor_raw_record_id,
            )
        except ReplayJobError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        receipts = sorted(job.receipts, key=lambda r: r.id)
        return AdminCortexReplayJobDetailResponse(
            replay_runtime_schema_version=REPLAY_RUNTIME_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            job=AdminCortexReplayJobItem.model_validate(replay_job_public_dict(job)),
            receipts=[AdminCortexReplayJobReceiptItem.model_validate(replay_receipt_public_dict(r)) for r in receipts],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/replay-jobs",
        response_model=AdminCortexReplayJobListResponse,
    )
    def admin_cortex_canonical_replay_jobs_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=100)] = 30,
    ) -> AdminCortexReplayJobListResponse:
        """Phase 03 Step 10 — recent canonical replay jobs (pins + receipts summary)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.replay_runtime import (
            REPLAY_RUNTIME_SCHEMA_VERSION,
            list_replay_jobs,
            replay_job_public_dict,
        )

        jobs = list_replay_jobs(db, tenant_id=tenant_id, limit=limit)
        return AdminCortexReplayJobListResponse(
            replay_runtime_schema_version=REPLAY_RUNTIME_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            jobs=[AdminCortexReplayJobItem.model_validate(replay_job_public_dict(j)) for j in jobs],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/replay-jobs/{job_id}",
        response_model=AdminCortexReplayJobDetailResponse,
    )
    def admin_cortex_canonical_replay_job_detail(
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexReplayJobDetailResponse:
        """Phase 03 Step 10 — single replay job with ordered divergence receipts."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.replay_runtime import (
            REPLAY_RUNTIME_SCHEMA_VERSION,
            get_replay_job,
            replay_job_public_dict,
            replay_receipt_public_dict,
        )

        job = get_replay_job(db, tenant_id=tenant_id, job_id=job_id)
        if job is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="replay_job_not_found")
        receipts = sorted(job.receipts, key=lambda r: r.id)
        return AdminCortexReplayJobDetailResponse(
            replay_runtime_schema_version=REPLAY_RUNTIME_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            job=AdminCortexReplayJobItem.model_validate(replay_job_public_dict(job)),
            receipts=[AdminCortexReplayJobReceiptItem.model_validate(replay_receipt_public_dict(r)) for r in receipts],
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/canonical/replay-jobs/{job_id}/resume",
        response_model=AdminCortexReplayJobDetailResponse,
    )
    def admin_cortex_canonical_replay_job_resume(
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexReplayJobDetailResponse:
        """Resume a failed replay job using the stored deterministic process order (Phase 03 hardening)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.replay_runtime import (
            REPLAY_RUNTIME_SCHEMA_VERSION,
            ReplayJobError,
            get_replay_job,
            replay_job_public_dict,
            replay_receipt_public_dict,
            resume_canonical_replay_job,
        )

        try:
            job = resume_canonical_replay_job(db, tenant_id=tenant_id, job_id=job_id)
        except ReplayJobError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        job = get_replay_job(db, tenant_id=tenant_id, job_id=job_id)
        assert job is not None
        receipts = sorted(job.receipts, key=lambda r: r.id)
        return AdminCortexReplayJobDetailResponse(
            replay_runtime_schema_version=REPLAY_RUNTIME_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            job=AdminCortexReplayJobItem.model_validate(replay_job_public_dict(job)),
            receipts=[AdminCortexReplayJobReceiptItem.model_validate(replay_receipt_public_dict(r)) for r in receipts],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/provenance/raw-records/{raw_record_id}",
        response_model=AdminCortexProvenanceByRawResponse,
    )
    def admin_cortex_canonical_provenance_by_raw(
        tenant_id: uuid.UUID,
        raw_record_id: int,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> AdminCortexProvenanceByRawResponse:
        """Phase 03 Step 11 — forward index: canonical provenance rows citing this raw record."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.provenance_runtime import (
            PROVENANCE_RUNTIME_SCHEMA_VERSION,
            list_provenance_for_raw_record,
            provenance_public_dict,
        )

        rows = list_provenance_for_raw_record(db, tenant_id=tenant_id, raw_record_id=raw_record_id, limit=limit)
        return AdminCortexProvenanceByRawResponse(
            provenance_runtime_schema_version=PROVENANCE_RUNTIME_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            raw_record_id=raw_record_id,
            records=[AdminCortexProvenanceRecordItem.model_validate(provenance_public_dict(r)) for r in rows],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/provenance/materializations/{materialization_id}",
        response_model=AdminCortexProvenanceByMaterializationResponse,
    )
    def admin_cortex_canonical_provenance_by_materialization(
        tenant_id: uuid.UUID,
        materialization_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexProvenanceByMaterializationResponse:
        """Phase 03 Step 11 — provenance envelope for a transform materialization (reverse trace)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.provenance_runtime import (
            PROVENANCE_RUNTIME_SCHEMA_VERSION,
            get_provenance_for_materialization,
            provenance_public_dict,
        )

        row = get_provenance_for_materialization(
            db, tenant_id=tenant_id, materialization_id=materialization_id
        )
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="provenance_record_not_found")
        return AdminCortexProvenanceByMaterializationResponse(
            provenance_runtime_schema_version=PROVENANCE_RUNTIME_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            record=AdminCortexProvenanceRecordItem.model_validate(provenance_public_dict(row)),
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/temporal/supersessions",
        response_model=AdminCortexTemporalSupersessionsListResponse,
    )
    def admin_cortex_canonical_temporal_supersessions_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        bundle_id: Annotated[str | None, Query(description="Optional filter to one mapping bundle id")] = None,
    ) -> AdminCortexTemporalSupersessionsListResponse:
        """Phase 03 Step 12 — append-only supersession ledger (prior materialization replaced on same scope)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.temporal_runtime import (
            TEMPORAL_RUNTIME_SCHEMA_VERSION,
            list_temporal_supersessions,
            supersession_public_dict,
        )

        rows = list_temporal_supersessions(db, tenant_id=tenant_id, limit=limit, bundle_id=bundle_id)
        return AdminCortexTemporalSupersessionsListResponse(
            temporal_runtime_schema_version=TEMPORAL_RUNTIME_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            items=[AdminCortexTemporalSupersessionItem.model_validate(supersession_public_dict(r)) for r in rows],
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/canonical/temporal/rebuild-preview",
        response_model=AdminCortexTemporalRebuildPreviewResponse,
    )
    def admin_cortex_canonical_temporal_rebuild_preview(
        tenant_id: uuid.UUID,
        body: AdminCortexTemporalRebuildPreviewRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexTemporalRebuildPreviewResponse:
        """Phase 03 Step 12 — deterministic ordering preview for replay/rebuild raw id lists (read-only)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.temporal_runtime import (
            TEMPORAL_RUNTIME_SCHEMA_VERSION,
            preview_rebuild_raw_order,
        )

        ordered = preview_rebuild_raw_order(db, tenant_id=tenant_id, raw_record_ids=body.raw_record_ids)
        return AdminCortexTemporalRebuildPreviewResponse(
            temporal_runtime_schema_version=TEMPORAL_RUNTIME_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            ordered=[AdminCortexTemporalRebuildPreviewRow.model_validate(r) for r in ordered],
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/canonical/query",
        response_model=AdminCortexCanonicalQueryResponse,
    )
    def admin_cortex_canonical_query(
        tenant_id: uuid.UUID,
        body: AdminCortexCanonicalQueryRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexCanonicalQueryResponse:
        """Phase 03 Step 13 — bounded canonical retrieval (anti-goal guarded; truncation metadata when capped)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.canonical_query_runtime import (
            CANONICAL_QUERY_RUNTIME_SCHEMA_VERSION,
            CanonicalQueryError,
            execute_canonical_query,
        )

        try:
            raw_out = execute_canonical_query(
                db,
                tenant_id=tenant_id,
                query_class=body.query_class,
                intent=body.intent,
                query_text=body.query_text,
                params=body.params,
                limit=body.limit,
            )
        except CanonicalQueryError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return AdminCortexCanonicalQueryResponse(
            canonical_query_runtime_schema_version=CANONICAL_QUERY_RUNTIME_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            query_class=str(raw_out["query_class"]),
            result_kind=str(raw_out["result_kind"]),
            payload=raw_out["payload"],
            truncation=raw_out.get("truncation"),
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/failures",
        response_model=AdminCortexCanonicalFailuresResponse,
    )
    def admin_cortex_canonical_failures(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexCanonicalFailuresResponse:
        """Phase 03 Step 14 — active canonical failure cases + recent remediation validations."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.failure_remediation_runtime import (
            sync_canonical_failure_cases,
        )

        raw = sync_canonical_failure_cases(db, tenant_id)
        return AdminCortexCanonicalFailuresResponse.model_validate(raw)

    @r.post(
        "/tenants/{tenant_id}/cortex/canonical/remediation/validate",
        response_model=AdminCortexCanonicalRemediationValidateResponse,
    )
    def admin_cortex_canonical_remediation_validate(
        tenant_id: uuid.UUID,
        body: AdminCortexCanonicalRemediationValidateRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexCanonicalRemediationValidateResponse:
        """Phase 03 Step 14 — policy-gated remediation validation (scoped rebuild or ambiguity triage ack)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.failure_remediation_runtime import (
            validate_canonical_remediation,
        )

        raw = validate_canonical_remediation(
            db,
            tenant_id=tenant_id,
            remediation_class=body.remediation_class,
            dry_run=body.dry_run,
            confirm_execution=body.confirm_execution,
            failure_case_gap_id=body.failure_case_gap_id,
            payload=body.payload,
        )
        return AdminCortexCanonicalRemediationValidateResponse.model_validate(raw)

    @r.post(
        "/tenants/{tenant_id}/cortex/canonical/verification/run",
        response_model=AdminCortexCanonicalVerificationRunResponse,
    )
    def admin_cortex_canonical_verification_run(
        tenant_id: uuid.UUID,
        body: AdminCortexCanonicalVerificationRunRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexCanonicalVerificationRunResponse:
        """Phase 03 Step 15 — deterministic canonical invariant sweep + optional persisted report (G-P03-12)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.canonical_verification_engine import (
            run_canonical_verification,
        )

        raw = run_canonical_verification(
            db,
            tenant_id=tenant_id,
            materialization_sample_limit=body.materialization_sample_limit,
            persist=body.persist,
        )
        gates = [AdminCortexCanonicalVerificationGateResult.model_validate(g) for g in raw["gates"]]
        return AdminCortexCanonicalVerificationRunResponse(
            canonical_verification_engine_schema_version=raw["canonical_verification_engine_schema_version"],
            tenant_id=raw["tenant_id"],
            passed=raw["passed"],
            gates=gates,
            evidence=raw["evidence"],
            persisted_run_id=raw.get("persisted_run_id"),
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/canonical/verification/repair-determinism-drift",
        response_model=AdminCortexCanonicalDeterminismRepairResponse,
    )
    def admin_cortex_canonical_verification_repair_determinism_drift(
        tenant_id: uuid.UUID,
        body: AdminCortexCanonicalDeterminismRepairRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexCanonicalDeterminismRepairResponse:
        """Rematerialize rows that fail G-P03-01 oracle-vs-stored hash comparison (bounded scan)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.transform_runtime import (
            repair_tenant_materialization_oracle_determinism_drift,
        )

        raw = repair_tenant_materialization_oracle_determinism_drift(
            db,
            tenant_id=tenant_id,
            bundle_id=body.bundle_id,
            scan_limit=body.scan_limit,
            dry_run=body.dry_run,
        )
        return AdminCortexCanonicalDeterminismRepairResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/verification/runs",
        response_model=AdminCortexCanonicalVerificationRunsListResponse,
    )
    def admin_cortex_canonical_verification_runs(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> AdminCortexCanonicalVerificationRunsListResponse:
        """Phase 03 Step 15 — recent persisted verification runs for audit replay."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.canonical_verification_engine import (
            CANONICAL_VERIFICATION_ENGINE_SCHEMA_VERSION,
            list_canonical_verification_runs,
            verification_run_public_dict,
        )

        rows = list_canonical_verification_runs(db, tenant_id=tenant_id, limit=limit)
        items: list[AdminCortexCanonicalVerificationRunItem] = []
        for r in rows:
            d = verification_run_public_dict(r)
            items.append(
                AdminCortexCanonicalVerificationRunItem(
                    id=d["id"],
                    tenant_id=d["tenant_id"],
                    engine_schema_version=d["engine_schema_version"],
                    passed=d["passed"],
                    gates=[AdminCortexCanonicalVerificationGateResult.model_validate(x) for x in d["gates_json"]],
                    evidence=d["evidence_json"],
                    created_at=d["created_at"],
                )
            )
        return AdminCortexCanonicalVerificationRunsListResponse(
            canonical_verification_engine_schema_version=CANONICAL_VERIFICATION_ENGINE_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            runs=items,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/certification-pack",
        response_model=AdminCortexCanonicalCertificationPackResponse,
    )
    def admin_cortex_canonical_certification_pack_snapshot(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        materialization_sample_limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> AdminCortexCanonicalCertificationPackResponse:
        """Phase 03 Step 18 — operator-visible certification evidence pack + closure gate matrix (pre-archive)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.canonical_certification_pack import (
            build_canonical_certification_pack,
        )

        raw = build_canonical_certification_pack(
            db,
            tenant_id=tenant_id,
            materialization_sample_limit=materialization_sample_limit,
        )
        return AdminCortexCanonicalCertificationPackResponse.model_validate(raw)

    @r.post(
        "/tenants/{tenant_id}/cortex/canonical/certification-pack/archive",
        response_model=AdminCortexCanonicalCertificationArchiveResponse,
    )
    def admin_cortex_canonical_certification_pack_archive(
        tenant_id: uuid.UUID,
        body: AdminCortexCanonicalCertificationArchiveRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexCanonicalCertificationArchiveResponse:
        """Phase 03 Step 18 — persist certification pack when all hard-fail closure rows pass."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.canonical_certification_pack import (
            CERTIFICATION_PACK_SCHEMA_VERSION,
            persist_canonical_certification_archive,
        )

        raw = persist_canonical_certification_archive(
            db,
            tenant_id=tenant_id,
            materialization_sample_limit=body.materialization_sample_limit,
        )
        pack = raw["pack"]
        db.commit()
        return AdminCortexCanonicalCertificationArchiveResponse(
            persisted=bool(raw["persisted"]),
            passed=bool(raw["passed"]),
            archive_id=raw.get("archive_id"),
            certification_pack_schema_version=int(
                pack.get("certification_pack_schema_version") or CERTIFICATION_PACK_SCHEMA_VERSION
            ),
            tenant_id=str(tenant_id),
            pack=pack,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/certification-pack/archives",
        response_model=AdminCortexCanonicalCertificationArchivesListResponse,
    )
    def admin_cortex_canonical_certification_pack_archives(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> AdminCortexCanonicalCertificationArchivesListResponse:
        """Phase 03 Step 18 — recent archived certification packs."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.canonical_certification_pack import (
            CERTIFICATION_PACK_SCHEMA_VERSION,
            certification_archive_public_dict,
            list_canonical_certification_archives,
        )

        rows = list_canonical_certification_archives(db, tenant_id=tenant_id, limit=limit)
        items = [
            AdminCortexCanonicalCertificationArchiveItem.model_validate(certification_archive_public_dict(r))
            for r in rows
        ]
        return AdminCortexCanonicalCertificationArchivesListResponse(
            certification_pack_schema_version=CERTIFICATION_PACK_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            archives=items,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/certification-pack/archives/{archive_id}",
        response_model=AdminCortexCanonicalCertificationArchiveDetailResponse,
    )
    def admin_cortex_canonical_certification_pack_archive_detail(
        tenant_id: uuid.UUID,
        archive_id: int,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexCanonicalCertificationArchiveDetailResponse:
        """Phase 03 Step 18 — fetch one archived certification pack (full JSON)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.canonical_certification_pack import (
            get_canonical_certification_archive,
        )

        row = get_canonical_certification_archive(db, tenant_id=tenant_id, archive_id=archive_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Certification archive not found.") from None
        return AdminCortexCanonicalCertificationArchiveDetailResponse(
            id=row.id,
            tenant_id=str(row.tenant_id),
            certification_pack_schema_version=row.certification_pack_schema_version,
            passed=row.passed,
            created_at=row.created_at,
            pack=dict(row.pack_json),
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/ambiguity",
        response_model=AdminCortexAmbiguityListResponse,
    )
    def admin_cortex_canonical_ambiguity_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        status: Annotated[str | None, Query(description="Filter by ambiguity status")] = None,
        ambiguity_class: Annotated[str | None, Query(description="Filter by ambiguity_class")] = None,
        connector: Annotated[str | None, Query(description="Filter by primary_connector")] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> AdminCortexAmbiguityListResponse:
        """Phase 03 Step 7 — list ambiguity receipts + operator aggregates (counts by status/class/connector)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.ambiguity_runtime import (
            AMBIGUITY_RUNTIME_SCHEMA_VERSION,
            ambiguity_record_public_dict,
            build_ambiguity_aggregates,
            list_ambiguity_records,
        )

        ag = build_ambiguity_aggregates(db, tenant_id=tenant_id)
        rows = list_ambiguity_records(
            db,
            tenant_id=tenant_id,
            status=status,
            ambiguity_class=ambiguity_class,
            connector=connector,
            limit=limit,
        )
        aggregates = AdminCortexAmbiguityAggregates(
            by_status=ag["by_status"],
            by_class=ag["by_class"],
            by_connector_resource=[AdminCortexAmbiguityConnectorRollupItem(**x) for x in ag["by_connector_resource"]],
        )
        records = [AdminCortexAmbiguityRecordItem.model_validate(ambiguity_record_public_dict(r)) for r in rows]
        return AdminCortexAmbiguityListResponse(
            ambiguity_runtime_schema_version=AMBIGUITY_RUNTIME_SCHEMA_VERSION,
            tenant_id=str(tenant_id),
            aggregates=aggregates,
            records=records,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canonical/ambiguity/{ambiguity_id}",
        response_model=AdminCortexOpenAmbiguityResponse,
    )
    def admin_cortex_canonical_ambiguity_detail(
        tenant_id: uuid.UUID,
        ambiguity_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOpenAmbiguityResponse:
        """Phase 03 Step 7 — one ambiguity record with append-only lifecycle event log."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.ambiguity_runtime import (
            ambiguity_record_public_dict,
            get_ambiguity_record,
        )

        rec = get_ambiguity_record(db, tenant_id=tenant_id, ambiguity_record_id=ambiguity_id)
        if rec is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="ambiguity_record_not_found")
        payload = ambiguity_record_public_dict(rec, include_events=True)
        return AdminCortexOpenAmbiguityResponse(record=AdminCortexAmbiguityRecordItem.model_validate(payload))

    @r.post(
        "/tenants/{tenant_id}/cortex/canonical/ambiguity",
        response_model=AdminCortexOpenAmbiguityResponse,
    )
    def admin_cortex_canonical_ambiguity_open(
        tenant_id: uuid.UUID,
        body: AdminCortexOpenAmbiguityRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexOpenAmbiguityResponse:
        """Phase 03 Step 7 — open a new ambiguity receipt (durable row + opened lifecycle event)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.ambiguity_runtime import (
            AmbiguityError,
            ambiguity_record_public_dict,
            open_ambiguity_record,
        )

        try:
            rec = open_ambiguity_record(
                db,
                tenant_id=tenant_id,
                bundle_id=body.bundle_id,
                ambiguity_class=body.ambiguity_class,
                scope=body.scope,
                raw_record_ids=body.raw_record_ids,
                rule_ids_involved=body.rule_ids_involved,
                record_handle=body.record_handle,
                evidence_payload=body.evidence_payload,
            )
        except AmbiguityError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return AdminCortexOpenAmbiguityResponse(
            record=AdminCortexAmbiguityRecordItem.model_validate(ambiguity_record_public_dict(rec))
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/canonical/ambiguity/{ambiguity_id}/lifecycle",
        response_model=AdminCortexAmbiguityLifecycleResponse,
    )
    def admin_cortex_canonical_ambiguity_lifecycle(
        tenant_id: uuid.UUID,
        ambiguity_id: uuid.UUID,
        body: AdminCortexAmbiguityLifecycleRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCortexAmbiguityLifecycleResponse:
        """Phase 03 Step 7 — supersede or void an ambiguity (append-only lifecycle log + status update)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canonical.ambiguity_runtime import (
            AmbiguityError,
            ambiguity_record_public_dict,
            transition_ambiguity_record,
        )

        try:
            rec = transition_ambiguity_record(
                db,
                tenant_id=tenant_id,
                ambiguity_record_id=ambiguity_id,
                target_status=body.target_status,
                supersession_note=body.supersession_note,
                superseded_by_ambiguity_id=body.superseded_by_ambiguity_id,
            )
        except AmbiguityError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return AdminCortexAmbiguityLifecycleResponse(
            record=AdminCortexAmbiguityRecordItem.model_validate(ambiguity_record_public_dict(rec))
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/ingestion/actions/trigger-sync",
        response_model=AdminCortexIngestionTriggerSyncResponse,
    )
    def admin_cortex_ingestion_trigger_sync(
        tenant_id: uuid.UUID,
        body: AdminCortexIngestionTriggerSyncRequest,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCortexIngestionTriggerSyncResponse:
        """Enqueue one manual live-lane sync (cortex_live) for a routed connector."""
        _assert_tenant(db, tenant_id)
        if body.confirmation != CORTEX_MANUAL_SYNC_CONFIRM_PHRASE:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Confirmation phrase does not match.",
            ) from None
        tc = _active_cortex_routed_connection(
            db,
            settings,
            tenant_id=tenant_id,
            connector_id=body.connector,
            connection_id=body.connection_id,
        )
        from app.tasks.cortex_ingestion_sync import run_cortex_connector_sync_task

        run_cortex_connector_sync_task.delay(
            str(tenant_id),
            body.connector,
            "manual_admin",
            body.sync_mode,
            str(tc.id),
        )
        log_ingestion_event(
            _logger,
            logging.INFO,
            "admin cortex manual sync enqueued",
            task_name="admin_cortex_ingestion_trigger_sync",
            phase=PHASE_STEP6,
            outcome="enqueued",
            tenant_id=str(tenant_id),
            connector=body.connector,
            sync_mode=body.sync_mode,
        )
        return AdminCortexIngestionTriggerSyncResponse(
            connector=body.connector,
            connection_id=tc.id,
            tenant_id=tenant_id,
            sync_mode=body.sync_mode,
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/ingestion/actions/trigger-replay",
        response_model=AdminCortexIngestionTriggerReplayResponse,
    )
    def admin_cortex_ingestion_trigger_replay(
        tenant_id: uuid.UUID,
        body: AdminCortexIngestionTriggerReplayRequest,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCortexIngestionTriggerReplayResponse:
        """Enqueue a replay-scoped sync on cortex_replay with isolated checkpoints."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.ingestion.verification import verify_tenant_ingestion_invariants

        verification_payload = verify_tenant_ingestion_invariants(
            db,
            tenant_id,
            run_limit=30,
            enforce_exhaust_gate=True,
            enforcement_mode=settings.cortex_raw_memory_enforcement_mode,
        )
        trust_annotation = (
            verification_payload.get("raw_memory_trust", {}).get("annotation")
            if isinstance(verification_payload.get("raw_memory_trust"), dict)
            else None
        )
        enforcement = evaluate_progressive_enforcement(
            trust_annotation=trust_annotation if isinstance(trust_annotation, dict) else None,
            phase_closure=(
                verification_payload.get("raw_memory_phase_closure")
                if isinstance(verification_payload.get("raw_memory_phase_closure"), dict)
                else None
            ),
            mode=(
                settings.cortex_raw_memory_enforcement_mode
                if settings.cortex_raw_memory_enforcement_mode in {"observe", "progressive", "strict"}
                else "progressive"
            ),
            operation="replay_trigger",
        )
        if enforcement["blocked"]:
            raise HTTPException(
                status.HTTP_423_LOCKED,
                detail={
                    "message": "Replay blocked by raw-memory enforcement policy.",
                    "enforcement": enforcement,
                },
            ) from None
        if body.confirmation != CORTEX_REPLAY_CONFIRM_PHRASE:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Confirmation phrase does not match.",
            ) from None
        tc = _active_cortex_routed_connection(
            db,
            settings,
            tenant_id=tenant_id,
            connector_id=body.connector,
            connection_id=body.connection_id,
        )
        job_id = uuid.uuid4()
        from app.tasks.cortex_ingestion_sync import run_cortex_connector_replay_sync_task

        run_cortex_connector_replay_sync_task.delay(
            str(tenant_id),
            body.connector,
            str(job_id),
            body.replay_version,
            "manual_admin_replay",
            str(tc.id),
        )
        log_ingestion_event(
            _logger,
            logging.INFO,
            "admin cortex replay sync enqueued",
            task_name="admin_cortex_ingestion_trigger_replay",
            phase=PHASE_STEP6,
            outcome="enqueued",
            tenant_id=str(tenant_id),
            connector=body.connector,
            ing_replay_job_id=str(job_id),
        )
        return AdminCortexIngestionTriggerReplayResponse(
            replay_job_id=job_id,
            connector=body.connector,
            connection_id=tc.id,
            tenant_id=tenant_id,
            replay_version=body.replay_version,
            enforcement=enforcement,
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/ingestion/actions/flush-rerun-to-identity",
        response_model=AdminCortexFlushAndRerunResponse,
    )
    def admin_cortex_flush_rerun_to_identity(
        tenant_id: uuid.UUID,
        body: AdminCortexFlushAndRerunRequest,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCortexFlushAndRerunResponse:
        """Flush tenant Cortex state, rerun routed connectors, canonical drain, then org identity backfill."""
        _assert_tenant(db, tenant_id)
        if body.confirmation != CORTEX_FLUSH_RERUN_CONFIRM_PHRASE:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Confirmation phrase does not match flush+rerun safeguard phrase.",
            ) from None

        active_connections = list(
            db.scalars(
                select(TenantConnection)
                .where(
                    TenantConnection.tenant_id == tenant_id,
                    TenantConnection.status == "active",
                )
                .order_by(TenantConnection.provider.asc(), TenantConnection.created_at.desc())
            ).all()
        )
        connector_candidates = sorted({c.provider for c in active_connections})
        routed_connectors = [
            connector
            for connector in connector_candidates
            if should_route_ingestion_to_cortex(settings, connector, tenant_id)
        ]

        flush_summary = flush_tenant_cortex_pipeline_state(db, tenant_id=tenant_id)

        from app.tasks.cortex_full_pipeline_rerun import run_cortex_flush_rerun_to_identity_task
        from vector.domains.cortex.canonical.transform_runtime import (
            resolve_default_bundle_id_for_stub_transform,
        )

        enqueued_connectors: list[str] = []
        orchestrator_connectors: list[dict[str, str]] = []
        for connector in routed_connectors:
            tc = _active_cortex_routed_connection(
                db,
                settings,
                tenant_id=tenant_id,
                connector_id=connector,
            )
            enqueued_connectors.append(connector)
            orchestrator_connectors.append({"connector": connector, "connection_id": str(tc.id)})

        resolved_bundle_id = resolve_default_bundle_id_for_stub_transform(db, tenant_id)
        if resolved_bundle_id is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=(
                    "no_transformable_bundle — add a tenant mapping pin or ensure an approved/candidate bundle exists"
                ),
            )

        async_result = run_cortex_flush_rerun_to_identity_task.delay(
            str(tenant_id),
            resolved_bundle_id,
            orchestrator_connectors,
            body.canonical_batch_limit,
        )

        log_ingestion_event(
            _logger,
            logging.WARNING,
            "admin cortex full flush+rerun enqueued",
            task_name="admin_cortex_flush_rerun_to_identity",
            phase=PHASE_STEP6,
            outcome="enqueued",
            tenant_id=str(tenant_id),
            connectors=enqueued_connectors,
            canonical_batch_limit=body.canonical_batch_limit,
            deleted_rows_total=flush_summary["deleted_rows_total"],
        )
        return AdminCortexFlushAndRerunResponse(
            tenant_id=tenant_id,
            enqueued_connectors=enqueued_connectors,
            canonical_backlog_task_id=str(async_result.id) if async_result and async_result.id else None,
            canonical_batch_limit=body.canonical_batch_limit,
            deleted_rows_total=int(flush_summary["deleted_rows_total"]),
            deleted_rows_by_table={
                str(k): int(v)
                for k, v in (flush_summary.get("deleted_rows_by_table") or {}).items()
            },
        )

    @r.post(
        "/cortex/ingestion/scheduler-pause",
        response_model=AdminCortexSchedulerPauseResponse,
    )
    def admin_cortex_ingestion_scheduler_pause(
        body: AdminCortexSchedulerPauseRequest,
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCortexSchedulerPauseResponse:
        """Global operator brake: pause/resume Beat enqueue via Redis (all tenants)."""
        from vector.infrastructure.cortex_scheduler_pause import (
            scheduler_pause_redis_available,
            write_scheduler_paused_flag,
        )

        if not scheduler_pause_redis_available(settings):
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Scheduler pause requires REDIS_URL (same broker Celery uses).",
            ) from None
        if body.paused:
            if body.confirmation != CORTEX_SCHEDULER_PAUSE_CONFIRM_PHRASE:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail="Confirmation phrase does not match pause phrase.",
                ) from None
        elif body.confirmation != CORTEX_SCHEDULER_RESUME_CONFIRM_PHRASE:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Confirmation phrase does not match resume phrase.",
            ) from None
        try:
            write_scheduler_paused_flag(settings, paused=body.paused)
        except RuntimeError as e:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
        log_ingestion_event(
            _logger,
            logging.INFO,
            "admin cortex scheduler pause flag written",
            task_name="admin_cortex_ingestion_scheduler_pause",
            phase=PHASE_STEP6,
            outcome="paused" if body.paused else "resumed",
        )
        return AdminCortexSchedulerPauseResponse(paused_via_redis=body.paused)

    from vector.api.http.routes.admin_octs_walks import register_octs_walk_traversal_routes

    register_octs_walk_traversal_routes(r)

    return r
