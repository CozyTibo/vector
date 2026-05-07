"""Internal admin API — HTTP Basic (ADMIN_PASSWORD). Cross-tenant inspection."""

from __future__ import annotations

import copy
import logging
import uuid
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
from vector.domains.connectors.calls.errors import CallsConnectorNotConfiguredError
from vector.domains.connectors.calls.oauth_flow import start_calls_oauth_url
from vector.domains.connectors.github.errors import GitHubConnectorNotConfiguredError
from vector.domains.connectors.github.install_flow import start_github_install_url
from vector.domains.connectors.linear.errors import LinearConnectorNotConfiguredError
from vector.domains.connectors.linear.oauth_flow import start_linear_oauth_url
from vector.domains.connectors.notion.errors import NotionConnectorNotConfiguredError
from vector.domains.connectors.notion.oauth_flow import start_notion_oauth_url
from vector.domains.connectors.runtime import runtime_by_id
from vector.domains.connectors.slack.errors import SlackConnectorNotConfiguredError
from vector.domains.connectors.slack.oauth_flow import start_slack_oauth_url
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
from vector.settings import Settings, get_settings

_logger = logging.getLogger("app")


def _legacy_connector_sync_removed(*_a: object, **_k: object) -> None:
    raise RuntimeError("Legacy connector ingestion was removed.")


# Backward-compat shim for tests/patch targets that still reference
# `vector.api.http.routes.admin.connector_sync`.
connector_sync = SimpleNamespace(
    enqueue_github_poll_sync=_legacy_connector_sync_removed,
    enqueue_linear_poll_sync=_legacy_connector_sync_removed,
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

    return r
