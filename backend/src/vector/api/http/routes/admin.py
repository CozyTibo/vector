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
    AdminConnectionPermissionReport,
    AdminConnectionsResponse,
    AdminConnectorConnectLinkResponse,
    AdminCortexConnectorRawRecordItem,
    AdminCortexConnectorRawRecordsResponse,
    AdminCortexIngestionExhaustCoverageResponse,
    AdminCortexIngestionOverviewResponse,
    AdminCortexIngestionRecentRunItem,
    AdminCortexIngestionRecentRunsResponse,
    AdminCortexIngestionSchedulerBeatConnectorDebrief,
    AdminCortexIngestionSchedulerBeatItem,
    AdminCortexIngestionSchedulerBeatsResponse,
    AdminCortexIngestionResetStreamRequest,
    AdminCortexIngestionResetStreamResponse,
    AdminCortexIngestionTriggerReplayRequest,
    AdminCortexIngestionTriggerReplayResponse,
    AdminCortexIngestionTriggerSyncRequest,
    AdminCortexIngestionTriggerSyncResponse,
    AdminCortexIngestionVerificationResponse,
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
    AdminCortexSchedulerPauseRequest,
    AdminCortexSchedulerPauseResponse,
    AdminCanonPassRunItem,
    AdminCanonReadinessResponse,
    AdminCanonCoverageResponse,
    AdminCanonEntityDetailResponse,
    AdminCanonEntityListResponse,
    AdminCanonEntityStatsResponse,
    AdminIdentityDetailResponse,
    AdminIdentityListResponse,
    AdminIdentityPassRunItem,
    AdminIdentityReadinessResponse,
    AdminIdentityRecentPassRunsResponse,
    AdminIdentityRebuildRequest,
    AdminIdentityRebuildResponse,
    AdminIdentityTriggerPassRequest,
    AdminIdentityTriggerPassResponse,
    AdminIdentityUnresolvedActorsResponse,
    AdminCanonRegistryResponse,
    AdminCanonRecentPassRunsResponse,
    AdminCanonTriggerPassRequest,
    AdminCanonTriggerPassResponse,
    CortexIngestionConnectorId,
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
    AdminSlackChannelsIngestApplyRequest,
    AdminSlackChannelsIngestApplyResponse,
    AdminSlackChannelsIngestListResponse,
    AdminTenantPrimaryMemberFullNamePatchRequest,
    AdminTenantSlackDeliveryRequest,
    AdminTenantWorkspaceAccessRequest,
    AdminToolOptionItem,
    AdminUserListItem,
    AdminUserListResponse,
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
from vector.domains.cortex.connectors.admin_connection_permissions import (
    permissions_by_provider_for_tenant,
)
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
from vector.domains.cortex.canon.admin_coverage import (
    aggregate_canon_entity_stats,
    build_canon_coverage_payload,
)
from vector.domains.cortex.canon.admin_entities import (
    MANUAL_CANON_PASS_CONFIRMATION,
    get_canon_entity_detail,
    list_canon_entities,
)
from vector.domains.cortex.canon.admin_readiness import (
    build_canon_admin_readiness,
    list_recent_canon_pass_runs,
)
from vector.domains.cortex.canon.resource_type_registry import registry_rows
from vector.domains.cortex.identity.admin import (
    MANUAL_IDENTITY_PASS_CONFIRMATION,
    MANUAL_IDENTITY_REBUILD_CONFIRMATION,
    build_identity_readiness,
    get_identity_detail,
    list_identities,
    list_recent_identity_pass_runs,
    list_unresolved_actor_entities,
)
from vector.domains.cortex.ingestion.admin_overview import build_cortex_ingestion_admin_overview
from vector.domains.cortex.ingestion.admin_recent_raw import (
    aggregate_raw_ingestion_stats,
    build_connector_raw_rollups,
    list_raw_records_for_connector,
    list_recent_ingestion_runs,
)
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
CORTEX_RESET_STREAM_CONFIRM_PHRASE = "RESET CORTEX INGESTION STREAM CHECKPOINT"

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
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminConnectionsResponse:
        _assert_tenant(db, tenant_id)
        rows = _list_tenant_connections(db, tenant_id=tenant_id)
        active_providers = {row.provider for row in rows if row.status == "active"}
        per_provider = permissions_by_provider_for_tenant(
            db,
            settings,
            tenant_id=tenant_id,
            active_providers=active_providers,
        )
        permissions_by_provider = {
            k: AdminConnectionPermissionReport.model_validate(v.as_dict())
            for k, v in per_provider.items()
        }
        items: list[TenantConnectionAdminItem] = []
        for row in rows:
            snap = per_provider.get(row.provider)
            perm = (
                AdminConnectionPermissionReport.model_validate(snap.as_dict())
                if snap is not None
                else None
            )
            items.append(
                TenantConnectionAdminItem(
                    id=row.id,
                    provider=row.provider,
                    status=row.status,
                    created_at=row.created_at,
                    permissions=perm,
                )
            )
        return AdminConnectionsResponse(
            items=items,
            permissions_by_provider=permissions_by_provider,
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
        "/tenants/{tenant_id}/connections/slack/channels",
        response_model=AdminSlackChannelsIngestListResponse,
    )
    def admin_slack_channels_ingest_list(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
        refresh: bool = False,
    ) -> AdminSlackChannelsIngestListResponse:
        """List Slack channels visible to the bot and current ingest selection."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.connectors.slack.channel_ingest import list_slack_channels_for_admin
        from vector.domains.cortex.connectors.slack.errors import SlackWebApiError

        try:
            raw = list_slack_channels_for_admin(
                db,
                tenant_id=tenant_id,
                settings=settings,
                force_refresh=refresh,
            )
        except SlackWebApiError as exc:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail=f"slack_channel_catalog_failed:{exc}",
            ) from exc
        if not raw.get("connected"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Slack is not connected for this tenant.")
        return AdminSlackChannelsIngestListResponse.model_validate(raw)

    @r.put(
        "/tenants/{tenant_id}/connections/slack/channels",
        response_model=AdminSlackChannelsIngestApplyResponse,
    )
    def admin_slack_channels_ingest_apply(
        tenant_id: uuid.UUID,
        body: AdminSlackChannelsIngestApplyRequest,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminSlackChannelsIngestApplyResponse:
        """Join selected public channels, persist ingest policy for subsequent syncs."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.connectors.slack.channel_ingest import (
            apply_slack_ingest_channel_selection,
            enqueue_slack_ingest_after_channel_apply,
        )
        from vector.domains.cortex.connectors.slack.errors import SlackWebApiError
        from vector.infrastructure.db.repositories import slack_connection as slack_repo

        link = slack_repo.get_slack_connection_for_tenant(db, tenant_id)
        if link is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Slack is not connected for this tenant.")
        try:
            raw = apply_slack_ingest_channel_selection(
                db,
                tenant_id=tenant_id,
                channel_ids=body.channel_ids,
                settings=settings,
            )
        except ValueError as exc:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except SlackWebApiError as exc:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail=f"slack_channel_apply_failed:{exc}",
            ) from exc
        db.commit()
        enqueue_slack_ingest_after_channel_apply(
            tenant_id=tenant_id,
            connection_id=link.connection.id,
        )
        return AdminSlackChannelsIngestApplyResponse.model_validate(raw)

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
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0, le=50_000)] = 0,
        connector: Annotated[str | None, Query()] = None,
    ) -> AdminCortexIngestionRecentRunsResponse:
        """Recent ingestion runs for drill-down (read-only)."""
        _assert_tenant(db, tenant_id)
        rows, total_count = list_recent_ingestion_runs(
            db,
            tenant_id,
            limit=limit,
            offset=offset,
            connector=connector,
        )
        return AdminCortexIngestionRecentRunsResponse(
            items=[AdminCortexIngestionRecentRunItem.model_validate(x) for x in rows],
            total_count=total_count,
            offset=offset,
            limit=limit,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/ingestion/scheduler-beats",
        response_model=AdminCortexIngestionSchedulerBeatsResponse,
    )
    def admin_cortex_ingestion_scheduler_beats(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=20)] = 20,
    ) -> AdminCortexIngestionSchedulerBeatsResponse:
        """Ingestion-only Beat history with per-connector debrief (pulled / added)."""
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.ingestion.scheduler_tick_history import (
            build_tenant_scheduler_beat_history_v1,
        )

        raw = build_tenant_scheduler_beat_history_v1(db, tenant_id=tenant_id, limit=limit)
        return AdminCortexIngestionSchedulerBeatsResponse(
            tenant_id=tenant_id,
            limit=int(raw["limit"]),
            items=[
                AdminCortexIngestionSchedulerBeatItem(
                    tick_id=item["tick_id"],
                    started_at=item["started_at"],
                    completed_at=item.get("completed_at"),
                    outcome=item["outcome"],
                    beat_interval_seconds=item["beat_interval_seconds"],
                    skip_reason=item.get("skip_reason"),
                    global_enqueued_count=item["global_enqueued_count"],
                    global_candidate_count=item["global_candidate_count"],
                    tenant_enqueued_count=item["tenant_enqueued_count"],
                    connectors=[
                        AdminCortexIngestionSchedulerBeatConnectorDebrief.model_validate(c)
                        for c in item["connectors"]
                    ],
                )
                for item in raw["items"]
            ],
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canon",
        response_model=AdminCanonReadinessResponse,
    )
    def admin_cortex_canon_readiness(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCanonReadinessResponse:
        """Canon v1 readiness — raw inventory, lag, mapper coverage (read-only)."""
        _assert_tenant(db, tenant_id)
        try:
            raw = build_canon_admin_readiness(db, settings, tenant_id)
        except ValueError:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tenant not found.") from None
        return AdminCanonReadinessResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/canon/recent-passes",
        response_model=AdminCanonRecentPassRunsResponse,
    )
    def admin_cortex_canon_recent_passes(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0, le=50_000)] = 0,
    ) -> AdminCanonRecentPassRunsResponse:
        """Recent canon materialization passes (read-only)."""
        _assert_tenant(db, tenant_id)
        rows, total = list_recent_canon_pass_runs(db, tenant_id, limit=limit, offset=offset)
        return AdminCanonRecentPassRunsResponse(
            items=[AdminCanonPassRunItem.model_validate(x) for x in rows],
            total_count=total,
            offset=offset,
            limit=limit,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canon/coverage",
        response_model=AdminCanonCoverageResponse,
    )
    def admin_cortex_canon_coverage(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCanonCoverageResponse:
        """Per-connector canon coverage and raw→entity gaps."""
        _assert_tenant(db, tenant_id)
        raw = build_canon_coverage_payload(db, tenant_id)
        return AdminCanonCoverageResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/canon/stats",
        response_model=AdminCanonEntityStatsResponse,
    )
    def admin_cortex_canon_stats(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        connector: Annotated[str | None, Query()] = None,
        entity_type: Annotated[str | None, Query()] = None,
    ) -> AdminCanonEntityStatsResponse:
        """Canon entity counts by connector and entity_type (for listing filters)."""
        _assert_tenant(db, tenant_id)
        rows = aggregate_canon_entity_stats(
            db,
            tenant_id,
            connector=connector,
            entity_type=entity_type,
        )
        return AdminCanonEntityStatsResponse(
            tenant_id=tenant_id,
            resources=rows,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canon/entities",
        response_model=AdminCanonEntityListResponse,
    )
    def admin_cortex_canon_entities(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0, le=50_000)] = 0,
        connector: Annotated[str | None, Query()] = None,
        entity_type: Annotated[str | None, Query()] = None,
        search: Annotated[str | None, Query()] = None,
    ) -> AdminCanonEntityListResponse:
        _assert_tenant(db, tenant_id)
        items, total = list_canon_entities(
            db,
            tenant_id,
            limit=limit,
            offset=offset,
            connector=connector,
            entity_type=entity_type,
            search=search,
        )
        return AdminCanonEntityListResponse(
            items=items,
            total_count=total,
            offset=offset,
            limit=limit,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/canon/entities/{entity_id}",
        response_model=AdminCanonEntityDetailResponse,
    )
    def admin_cortex_canon_entity_detail(
        tenant_id: uuid.UUID,
        entity_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCanonEntityDetailResponse:
        _assert_tenant(db, tenant_id)
        raw = get_canon_entity_detail(db, tenant_id, entity_id)
        if raw is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Canon entity not found.")
        return AdminCanonEntityDetailResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/canon/registry",
        response_model=AdminCanonRegistryResponse,
    )
    def admin_cortex_canon_registry(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCanonRegistryResponse:
        _assert_tenant(db, tenant_id)
        from vector.domains.cortex.canon.mapper_version import CANON_MAPPER_VERSION

        return AdminCanonRegistryResponse(mapper_version=CANON_MAPPER_VERSION, rows=registry_rows())

    @r.post(
        "/tenants/{tenant_id}/cortex/canon/actions/trigger-pass",
        response_model=AdminCanonTriggerPassResponse,
    )
    def admin_cortex_canon_trigger_pass(
        tenant_id: uuid.UUID,
        body: AdminCanonTriggerPassRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminCanonTriggerPassResponse:
        _assert_tenant(db, tenant_id)
        if body.confirmation != MANUAL_CANON_PASS_CONFIRMATION:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"confirmation must be exactly: {MANUAL_CANON_PASS_CONFIRMATION}",
            )
        from app.tasks.cortex_canon_sync import run_cortex_canon_pass_task

        run_cortex_canon_pass_task.delay(str(tenant_id), source_trigger="manual_admin")
        return AdminCanonTriggerPassResponse(tenant_id=tenant_id)

    @r.get(
        "/tenants/{tenant_id}/cortex/identities/readiness",
        response_model=AdminIdentityReadinessResponse,
    )
    def admin_cortex_identity_readiness(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminIdentityReadinessResponse:
        _assert_tenant(db, tenant_id)
        raw = build_identity_readiness(
            db,
            tenant_id,
            scheduler={
                "enabled": settings.cortex_identity_scheduler_enabled,
                "interval_seconds": settings.cortex_identity_scheduler_interval_seconds,
            },
        )
        return AdminIdentityReadinessResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/identities/runs",
        response_model=AdminIdentityRecentPassRunsResponse,
    )
    def admin_cortex_identity_runs(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0, le=50_000)] = 0,
    ) -> AdminIdentityRecentPassRunsResponse:
        _assert_tenant(db, tenant_id)
        rows, total = list_recent_identity_pass_runs(db, tenant_id, limit=limit, offset=offset)
        return AdminIdentityRecentPassRunsResponse(
            items=[AdminIdentityPassRunItem.model_validate(x) for x in rows],
            total_count=total,
            offset=offset,
            limit=limit,
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/identities",
        response_model=AdminIdentityListResponse,
    )
    def admin_cortex_identities(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        kind: Annotated[str | None, Query()] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0, le=50_000)] = 0,
        search: Annotated[str | None, Query()] = None,
    ) -> AdminIdentityListResponse:
        _assert_tenant(db, tenant_id)
        items, total = list_identities(
            db,
            tenant_id,
            kind=kind,
            limit=limit,
            offset=offset,
            search=search,
        )
        return AdminIdentityListResponse(items=items, total_count=total, offset=offset, limit=limit)

    @r.get(
        "/tenants/{tenant_id}/cortex/identities/{identity_id}",
        response_model=AdminIdentityDetailResponse,
    )
    def admin_cortex_identity_detail(
        tenant_id: uuid.UUID,
        identity_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminIdentityDetailResponse:
        _assert_tenant(db, tenant_id)
        raw = get_identity_detail(db, tenant_id, identity_id)
        if raw is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Identity not found.")
        return AdminIdentityDetailResponse.model_validate(raw)

    @r.get(
        "/tenants/{tenant_id}/cortex/identities/unresolved-actors",
        response_model=AdminIdentityUnresolvedActorsResponse,
    )
    def admin_cortex_identity_unresolved_actors(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0, le=50_000)] = 0,
    ) -> AdminIdentityUnresolvedActorsResponse:
        _assert_tenant(db, tenant_id)
        items, total = list_unresolved_actor_entities(
            db,
            tenant_id,
            limit=limit,
            offset=offset,
        )
        return AdminIdentityUnresolvedActorsResponse(items=items, total_count=total, offset=offset, limit=limit)

    @r.post(
        "/tenants/{tenant_id}/cortex/identities/actions/trigger-pass",
        response_model=AdminIdentityTriggerPassResponse,
    )
    def admin_cortex_identity_trigger_pass(
        tenant_id: uuid.UUID,
        body: AdminIdentityTriggerPassRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminIdentityTriggerPassResponse:
        _assert_tenant(db, tenant_id)
        if body.confirmation != MANUAL_IDENTITY_PASS_CONFIRMATION:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"confirmation must be exactly: {MANUAL_IDENTITY_PASS_CONFIRMATION}",
            )
        from app.tasks.cortex_identity_sync import run_cortex_identity_pass_task

        run_cortex_identity_pass_task.delay(str(tenant_id), source_trigger="manual_admin")
        return AdminIdentityTriggerPassResponse(tenant_id=tenant_id)

    @r.post(
        "/tenants/{tenant_id}/cortex/identities/actions/rebuild",
        response_model=AdminIdentityRebuildResponse,
    )
    def admin_cortex_identity_rebuild(
        tenant_id: uuid.UUID,
        body: AdminIdentityRebuildRequest,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminIdentityRebuildResponse:
        _assert_tenant(db, tenant_id)
        if body.confirmation != MANUAL_IDENTITY_REBUILD_CONFIRMATION:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"confirmation must be exactly: {MANUAL_IDENTITY_REBUILD_CONFIRMATION}",
            )
        from vector.domains.cortex.identity.materialize import rebuild_identities_for_tenant

        out = rebuild_identities_for_tenant(
            db,
            tenant_id=tenant_id,
            resolver_version=settings.cortex_identity_resolver_version,
            source_trigger="manual_rebuild_admin",
            batch_limit=settings.cortex_identity_batch_actor_limit,
        )
        db.commit()
        return AdminIdentityRebuildResponse(
            tenant_id=tenant_id,
            enqueued_actor_count=int(out.get("enqueued", 0)),
            stats={k: int(v) for k, v in (out.get("stats") or {}).items()},
        )

    @r.get(
        "/tenants/{tenant_id}/cortex/ingestion/connectors/{connector}/raw-records",
        response_model=AdminCortexConnectorRawRecordsResponse,
    )
    def admin_cortex_ingestion_connector_raw_records(
        tenant_id: uuid.UUID,
        connector: CortexIngestionConnectorId,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=50)] = 50,
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
        from vector.domains.cortex.ingestion.admin_overview import (
            invalidate_cortex_ingestion_admin_caches_v1,
        )

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
        invalidate_cortex_ingestion_admin_caches_v1(tenant_id)
        return AdminCortexIngestionTriggerSyncResponse(
            connector=body.connector,
            connection_id=tc.id,
            tenant_id=tenant_id,
            sync_mode=body.sync_mode,
        )

    @r.post(
        "/tenants/{tenant_id}/cortex/ingestion/actions/reset-stream",
        response_model=AdminCortexIngestionResetStreamResponse,
    )
    def admin_cortex_ingestion_reset_stream(
        tenant_id: uuid.UUID,
        body: AdminCortexIngestionResetStreamRequest,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> AdminCortexIngestionResetStreamResponse:
        """Clear one stream checkpoint path in the live default scope (raw rows unchanged)."""
        _assert_tenant(db, tenant_id)
        if body.confirmation != CORTEX_RESET_STREAM_CONFIRM_PHRASE:
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
        from vector.domains.cortex.ingestion.admin_overview import (
            invalidate_cortex_ingestion_admin_caches_v1,
        )
        from vector.domains.cortex.ingestion.stream_checkpoint import apply_stream_reset_to_db_state
        from vector.domains.cortex.ingestion.sync_context import SCOPE_DEFAULT
        from vector.domains.cortex.ingestion.sync_shared import (
            read_checkpoint_state,
            replace_checkpoint_state,
        )

        existing = read_checkpoint_state(
            db,
            tenant_id=tenant_id,
            connection_id=tc.id,
            connector=body.connector,
            scope_key=SCOPE_DEFAULT,
        )
        merged = apply_stream_reset_to_db_state(
            existing,
            connector=body.connector,
            stream_key=body.stream_key.strip(),
        )
        if merged != existing:
            replace_checkpoint_state(
                db,
                tenant_id=tenant_id,
                connection_id=tc.id,
                connector=body.connector,
                state=merged,
                scope_key=SCOPE_DEFAULT,
            )
            db.commit()
        invalidate_cortex_ingestion_admin_caches_v1(tenant_id)
        return AdminCortexIngestionResetStreamResponse(
            tenant_id=tenant_id,
            connector=body.connector,
            connection_id=tc.id,
            stream_key=body.stream_key.strip(),
            reset_applied=bool(merged != existing),
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

    return r
