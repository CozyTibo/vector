"""Internal admin API — HTTP Basic (ADMIN_PASSWORD). Cross-tenant inspection."""

from __future__ import annotations

import copy
import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from vector.api.http.admin_deps import require_admin_basic
from vector.api.http.deps import get_db, settings_dep
from vector.api.http.routes.admin_manager_onboarding import (
    build_admin_manager_onboarding_router,
    build_admin_manager_onboarding_tenant_router,
)
from vector.api.http.serialization import orm_to_dict
from vector.application.services import connector_sync
from vector.contracts.admin import (
    AdminOnboardingAnswerOptionsResponse,
    AdminOnboardingCollectedDataPatch,
    AdminTenantPrimaryMemberFullNamePatchRequest,
    AdminToolOptionItem,
    AdminConnectionsResponse,
    AdminHardDeleteOrphanUserRequest,
    AdminHardDeleteOrphanUserResponse,
    AdminHardDeleteTenantRequest,
    AdminHardDeleteTenantResponse,
    AdminHardDeleteTenantsBulkRequest,
    AdminHardDeleteTenantsBulkResponse,
    AdminResetTenantToSignupRequest,
    AdminResetTenantToSignupResponse,
    AdminStep1RawResetRequest,
    AdminStep1RawResetResponse,
    AdminStep2ProjectionsResetRequest,
    AdminStep2ProjectionsResetResponse,
    AdminStep3CanonicalResetRequest,
    AdminStep3CanonicalResetResponse,
    AdminTenantWorkspaceAccessRequest,
    AdminUserListItem,
    AdminUserListResponse,
    OnboardingAdminSnapshot,
    OnboardingChatMessageItem,
    RawIngestionAdminDetail,
    RawIngestionAdminDetailResponse,
    RawIngestionAdminItem,
    RawIngestionAdminPage,
    SlackStakeholdersSnapshot,
    TenantAdminDetailResponse,
    TenantConnectionAdminItem,
    TenantListItem,
    TenantListResponse,
)
from vector.contracts.onboarding import OnboardingCompleteResponse
from vector.contracts.connectors import (
    GithubIngestionRunListItem,
    GithubIngestionRunsListResponse,
    LinearIngestionRunListItem,
    LinearIngestionRunsListResponse,
)
from vector.contracts.debug_canonical import (
    CanonicalStatusResponse,
    PaginatedResponse,
    SubgraphAnchor,
    SubgraphEdge,
    SubgraphNode,
    SubgraphResponse,
)
from vector.contracts.debug_projections import ProjectionRowsResponse
from vector.domains.canonical.worker import (
    count_canonical_lag,
    drain_github_canonical,
    drain_linear_canonical,
)
from vector.domains.connectors.runtime import runtime_by_id
from vector.domains.debug.github_pipeline_wipe import (
    rebuild_derived_from_step1_github,
    reset_github_pipeline_state,
)
from vector.domains.ingestion.github_poll_sync import run_github_poll_ingestion_for_tenant
from vector.domains.ingestion.http_fetch import FetchFatalError
from vector.domains.ingestion.mock_preflight import preflight_mock_connectors_reachable
from vector.domains.ingestion.step1_reset import (
    STEP1_RAW_RESET_CONFIRMATION_PHRASE,
    wipe_step1_raw_for_tenant,
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
from vector.domains.onboarding.onboarding_commands import dev_force_complete_website_onboarding_for_tenant
from vector.domains.ingestion.step2_step3_reset import (
    STEP2_PROJECTIONS_RESET_CONFIRMATION_PHRASE,
    STEP3_CANONICAL_RESET_CONFIRMATION_PHRASE,
    wipe_step2_projections_for_tenant,
    wipe_step3_canonical_for_tenant,
)
from vector.domains.projections.github.worker import drain_github_projections
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
from vector.infrastructure.db.models.canonical import Step3CanonicalCursor
from vector.infrastructure.db.models.onboarding_state import OnboardingState
from vector.infrastructure.db.repositories import canonical_debug_queries as cq
from vector.infrastructure.db.repositories import ingestion_queries as ing_queries
from vector.infrastructure.db.repositories import onboarding as onboarding_repo
from vector.infrastructure.db.repositories import projection_debug_queries as dbg
from vector.infrastructure.db.repositories import tenancy as tenancy_repo
from vector.infrastructure.db.repositories.ingestion import (
    CONNECTOR_GITHUB,
    CONNECTOR_LINEAR,
    RUN_STATUS_SUCCEEDED,
)
from vector.settings import Settings

GITHUB_ENTITIES = frozenset({"repositories", "pull_requests", "issues", "commits", "users"})
LINEAR_ENTITIES = frozenset({"teams", "projects", "issues", "users", "issue_comments"})


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
        deleted_manager_onboarding_sessions=out["deleted_manager_onboarding_sessions"],
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


def _snapshot_from_onboarding(
    session: Session, row: OnboardingState | None
) -> OnboardingAdminSnapshot | None:
    if row is None:
        return None
    ans = dict(row.answers_json or {})
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
        tools_interest=_tools_interest(ans),
        company_domain=_company_domain(ans),
        company_website=_company_website(ans),
        company_size=_company_size(ans),
        user_role=_profile_role(ans),
        tools_engineering=_tools_category(ans, "engineering"),
        tools_pm=_tools_category(ans, "pm"),
        tools_communication=_tools_category(ans, "communication"),
        tools_docs=_tools_category(ans, "docs"),
        tools_crm=_tools_category(ans, "crm"),
        tools_stack=_tools_stack(ans),
        slack_stakeholders=_slack_stakeholders_from_answers(ans),
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
        ("tools_docs", "docs"),
        ("tools_crm", "crm"),
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
        ("tools_docs", "docs"),
        ("tools_crm", "crm"),
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


def build_admin_router() -> APIRouter:
    r = APIRouter(
        prefix="/admin",
        tags=["admin"],
        dependencies=[Depends(require_admin_basic)],
    )
    r.include_router(build_admin_manager_onboarding_router())
    r.include_router(build_admin_manager_onboarding_tenant_router())

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
            conns = dbg.list_tenant_connections_for_tenant(db, tenant_id=t.id)
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
        conns = dbg.list_tenant_connections_for_tenant(db, tenant_id=tenant_id)
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
        row.answers_json = merged
        row.version = int(row.version) + 1
        db.commit()
        db.refresh(row)
        t = tenancy_repo.get_tenant_by_id(db, tenant_id)
        assert t is not None
        ob = onboarding_repo.get_onboarding_for_tenant(db, tenant_id)
        conns = dbg.list_tenant_connections_for_tenant(db, tenant_id=tenant_id)
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
        conns = dbg.list_tenant_connections_for_tenant(db, tenant_id=tenant_id)
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
        t.workspace_access_enabled = body.workspace_access_enabled
        db.commit()
        db.refresh(t)
        ob = onboarding_repo.get_onboarding_for_tenant(db, tenant_id)
        conns = dbg.list_tenant_connections_for_tenant(db, tenant_id=tenant_id)
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
        rows = dbg.list_tenant_connections_for_tenant(db, tenant_id=tenant_id)
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

    @r.get("/tenants/{tenant_id}/raw-ingestion", response_model=RawIngestionAdminPage)
    def list_raw_ingestion(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> RawIngestionAdminPage:
        _assert_tenant(db, tenant_id)
        page = dbg.list_raw_ingestion_records_for_tenant(
            db,
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
        )
        items = [
            RawIngestionAdminItem(
                id=row.id,
                connector=row.connector,
                replay_sequence=int(row.replay_sequence),
                resource_type=row.resource_type,
                external_id=row.external_id,
                fetched_at=row.fetched_at,
                http_status=row.http_status,
            )
            for row in page.items
        ]
        return RawIngestionAdminPage(
            total=page.total,
            limit=limit,
            offset=offset,
            items=items,
        )

    @r.get(
        "/tenants/{tenant_id}/raw-ingestion/{record_id}",
        response_model=RawIngestionAdminDetailResponse,
    )
    def get_raw_ingestion_detail(
        tenant_id: uuid.UUID,
        record_id: Annotated[int, Path(ge=1)],
        db: Annotated[Session, Depends(get_db)],
    ) -> RawIngestionAdminDetailResponse:
        _assert_tenant(db, tenant_id)
        row = dbg.get_raw_ingestion_record_for_tenant(
            db,
            tenant_id=tenant_id,
            record_id=record_id,
        )
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Raw ingestion record not found")
        detail = RawIngestionAdminDetail(
            id=row.id,
            connection_id=row.connection_id,
            run_id=row.run_id,
            connector=row.connector,
            source_trigger=row.source_trigger,
            replay_sequence=int(row.replay_sequence),
            resource_type=row.resource_type,
            external_id=row.external_id,
            api_endpoint=row.api_endpoint,
            query_params=row.query_params,
            payload_hash=row.payload_hash,
            http_status=row.http_status,
            fetched_at=row.fetched_at,
            payload_body=row.payload_body,
        )
        return RawIngestionAdminDetailResponse(item=detail)

    @r.post(
        "/tenants/{tenant_id}/raw-ingestion/reset",
        response_model=AdminStep1RawResetResponse,
    )
    def reset_tenant_step1_raw_ingestion(
        tenant_id: uuid.UUID,
        body: AdminStep1RawResetRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminStep1RawResetResponse:
        """Wipe Step 1 for tenant (raw rows, ingestion runs, sync state). No connector calls."""
        _assert_tenant(db, tenant_id)
        if body.confirmation != STEP1_RAW_RESET_CONFIRMATION_PHRASE:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Confirmation phrase does not match. Open the Step1 Raw admin tab for the "
                    "exact text — this only deletes Step 1 data, not OAuth or Step 2/3."
                ),
            )
        stats = wipe_step1_raw_for_tenant(db, tenant_id=tenant_id)
        db.commit()
        return AdminStep1RawResetResponse(
            deleted_raw_records=stats["deleted_raw_records"],
            deleted_ingestion_runs=stats["deleted_ingestion_runs"],
            deleted_sync_state_rows=stats["deleted_sync_state_rows"],
        )

    @r.post(
        "/tenants/{tenant_id}/projections/reset",
        response_model=AdminStep2ProjectionsResetResponse,
    )
    def reset_tenant_step2_projections(
        tenant_id: uuid.UUID,
        body: AdminStep2ProjectionsResetRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminStep2ProjectionsResetResponse:
        """Wipe Step 2 for tenant (GitHub + Linear projection tables + projection cursors)."""
        _assert_tenant(db, tenant_id)
        if body.confirmation != STEP2_PROJECTIONS_RESET_CONFIRMATION_PHRASE:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Confirmation phrase does not match. Open the Step2 Projections admin tab for "
                    "the exact text — this only deletes Step 2 data, not raw or canonical."
                ),
            )
        stats = wipe_step2_projections_for_tenant(db, tenant_id=tenant_id)
        db.commit()
        return AdminStep2ProjectionsResetResponse(
            deleted_github_projection_rows=stats["deleted_github_projection_rows"],
            deleted_linear_projection_rows=stats["deleted_linear_projection_rows"],
            deleted_connector_projection_progress_rows=stats[
                "deleted_connector_projection_progress_rows"
            ],
        )

    @r.post(
        "/tenants/{tenant_id}/canonical/reset",
        response_model=AdminStep3CanonicalResetResponse,
    )
    def reset_tenant_step3_canonical(
        tenant_id: uuid.UUID,
        body: AdminStep3CanonicalResetRequest,
        db: Annotated[Session, Depends(get_db)],
    ) -> AdminStep3CanonicalResetResponse:
        """Wipe Step 3 canonical ontology + Step3 cursors for tenant (all connections)."""
        _assert_tenant(db, tenant_id)
        if body.confirmation != STEP3_CANONICAL_RESET_CONFIRMATION_PHRASE:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Confirmation phrase does not match. Open the Step3 Canonical admin tab for "
                    "the exact text — this only deletes Step 3 data, not raw or projections."
                ),
            )
        stats = wipe_step3_canonical_for_tenant(db, tenant_id=tenant_id)
        db.commit()
        return AdminStep3CanonicalResetResponse(
            deleted_relationships=stats["deleted_relationships"],
            deleted_mapping_events=stats["deleted_mapping_events"],
            deleted_current_mappings=stats["deleted_current_mappings"],
            deleted_external_references=stats["deleted_external_references"],
            deleted_actor_external_identities=stats["deleted_actor_external_identities"],
            deleted_artifacts=stats["deleted_artifacts"],
            deleted_actors=stats["deleted_actors"],
            deleted_step3_canonical_cursors=stats["deleted_step3_canonical_cursors"],
        )

    @r.post("/tenants/{tenant_id}/ingestion/github-sync")
    def admin_trigger_github_step1_sync(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> JSONResponse:
        """Enqueue GitHub ingestion (same strategy as POST /connectors/github/sync)."""
        _assert_tenant(db, tenant_id)
        preflight_mock_connectors_reachable(settings)
        try:
            run = connector_sync.enqueue_github_poll_sync(db, tenant_id=tenant_id)
        except FetchFatalError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        db.commit()
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "run_id": str(run.id),
                "status": run.status,
                "error_summary": run.error_summary,
                "stats": run.stats,
            },
        )

    @r.post("/tenants/{tenant_id}/ingestion/linear-sync")
    def admin_trigger_linear_step1_sync(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
    ) -> JSONResponse:
        """Enqueue Linear ingestion (same strategy as POST /connectors/linear/sync)."""
        _assert_tenant(db, tenant_id)
        preflight_mock_connectors_reachable(settings)
        try:
            run = connector_sync.enqueue_linear_poll_sync(db, tenant_id=tenant_id)
        except FetchFatalError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        db.commit()
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "run_id": str(run.id),
                "status": run.status,
                "error_summary": run.error_summary,
                "stats": run.stats,
            },
        )

    @r.get(
        "/tenants/{tenant_id}/github/ingestion/runs",
        response_model=GithubIngestionRunsListResponse,
    )
    def list_github_runs(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
    ) -> GithubIngestionRunsListResponse:
        _assert_tenant(db, tenant_id)
        runs = ing_queries.list_github_ingestion_runs_for_tenant(
            db,
            tenant_id,
            limit=limit,
        )
        counts = ing_queries.record_counts_for_run_ids(db, [r.id for r in runs])
        items = [
            GithubIngestionRunListItem(
                id=run.id,
                connection_id=run.connection_id,
                status=run.status,
                source_trigger=run.source_trigger,
                started_at=run.started_at,
                finished_at=run.finished_at,
                error_summary=run.error_summary,
                stats=run.stats,
                records_written=counts.get(run.id, 0),
            )
            for run in runs
        ]
        return GithubIngestionRunsListResponse(items=items)

    @r.get(
        "/tenants/{tenant_id}/linear/ingestion/runs",
        response_model=LinearIngestionRunsListResponse,
    )
    def list_linear_runs(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
    ) -> LinearIngestionRunsListResponse:
        _assert_tenant(db, tenant_id)
        runs = ing_queries.list_linear_ingestion_runs_for_tenant(
            db,
            tenant_id,
            limit=limit,
        )
        counts = ing_queries.record_counts_for_run_ids(db, [r.id for r in runs])
        items = [
            LinearIngestionRunListItem(
                id=run.id,
                connection_id=run.connection_id,
                status=run.status,
                source_trigger=run.source_trigger,
                started_at=run.started_at,
                finished_at=run.finished_at,
                error_summary=run.error_summary,
                stats=run.stats,
                records_written=counts.get(run.id, 0),
            )
            for run in runs
        ]
        return LinearIngestionRunsListResponse(items=items)

    @r.get(
        "/tenants/{tenant_id}/projections/github/{connection_id}/rows",
        response_model=ProjectionRowsResponse,
    )
    def projection_rows(
        tenant_id: uuid.UUID,
        connection_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        entity: Annotated[str, Query(description="repositories | pull_requests | …")],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        q: Annotated[str | None, Query(description="Filter substring")] = None,
    ) -> ProjectionRowsResponse:
        _assert_tenant(db, tenant_id)
        if entity not in GITHUB_ENTITIES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown entity '{entity}'.",
            ) from None
        if not dbg.connection_belongs_to_tenant(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
        ):
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Connection not found for tenant.",
            ) from None
        listers: dict[str, Any] = {
            "repositories": dbg.list_github_repositories,
            "pull_requests": dbg.list_github_pull_requests,
            "issues": dbg.list_github_issues,
            "commits": dbg.list_github_commits,
            "users": dbg.list_github_users,
        }
        page = listers[entity](
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
            limit=limit,
            offset=offset,
            q=q,
        )
        items = [orm_to_dict(row) for row in page.items]
        return ProjectionRowsResponse(
            connector="github",
            connection_id=connection_id,
            entity=entity,
            total=page.total,
            limit=limit,
            offset=offset,
            items=items,
        )

    @r.get(
        "/tenants/{tenant_id}/projections/linear/{connection_id}/rows",
        response_model=ProjectionRowsResponse,
    )
    def linear_projection_rows(
        tenant_id: uuid.UUID,
        connection_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        entity: Annotated[str, Query(description="teams | projects | issues | …")],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        q: Annotated[str | None, Query(description="Filter substring")] = None,
    ) -> ProjectionRowsResponse:
        _assert_tenant(db, tenant_id)
        if entity not in LINEAR_ENTITIES:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown entity '{entity}'.",
            ) from None
        if not dbg.connection_belongs_to_tenant(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
        ):
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Connection not found for tenant.",
            ) from None
        listers: dict[str, Any] = {
            "teams": dbg.list_linear_teams,
            "projects": dbg.list_linear_projects,
            "issues": dbg.list_linear_issues,
            "users": dbg.list_linear_users,
            "issue_comments": dbg.list_linear_issue_comments,
        }
        page = listers[entity](
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
            limit=limit,
            offset=offset,
            q=q,
        )
        items = [orm_to_dict(row) for row in page.items]
        return ProjectionRowsResponse(
            connector="linear",
            connection_id=connection_id,
            entity=entity,
            total=page.total,
            limit=limit,
            offset=offset,
            items=items,
        )

    @r.get("/tenants/{tenant_id}/canonical/actors", response_model=PaginatedResponse)
    def list_actors(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        q: Annotated[str | None, Query()] = None,
    ) -> PaginatedResponse:
        _assert_tenant(db, tenant_id)
        page = cq.list_actors(db, tenant_id=tenant_id, limit=limit, offset=offset, q=q)
        items = [orm_to_dict(x) for x in page.items]
        return PaginatedResponse(total=page.total, limit=limit, offset=offset, items=items)

    @r.get("/tenants/{tenant_id}/canonical/artifacts", response_model=PaginatedResponse)
    def list_artifacts(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        artifact_kind_id: Annotated[int | None, Query()] = None,
        q: Annotated[str | None, Query()] = None,
    ) -> PaginatedResponse:
        _assert_tenant(db, tenant_id)
        page = cq.list_artifacts(
            db,
            tenant_id=tenant_id,
            artifact_kind_id=artifact_kind_id,
            limit=limit,
            offset=offset,
            q=q,
        )
        items = [orm_to_dict(x) for x in page.items]
        return PaginatedResponse(total=page.total, limit=limit, offset=offset, items=items)

    @r.get("/tenants/{tenant_id}/canonical/relationships", response_model=PaginatedResponse)
    def list_relationships(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        current_only: Annotated[bool, Query()] = True,
    ) -> PaginatedResponse:
        _assert_tenant(db, tenant_id)
        page = cq.list_relationships(
            db,
            tenant_id=tenant_id,
            current_only=current_only,
            limit=limit,
            offset=offset,
        )
        items = [orm_to_dict(x) for x in page.items]
        return PaginatedResponse(total=page.total, limit=limit, offset=offset, items=items)

    @r.get("/tenants/{tenant_id}/canonical/external-references", response_model=PaginatedResponse)
    def list_external_references(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> PaginatedResponse:
        _assert_tenant(db, tenant_id)
        page = cq.list_external_references(
            db,
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
        )
        items = [orm_to_dict(x) for x in page.items]
        return PaginatedResponse(total=page.total, limit=limit, offset=offset, items=items)

    @r.get("/tenants/{tenant_id}/canonical/mapping-events", response_model=PaginatedResponse)
    def list_mapping_events(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
        external_reference_id: Annotated[uuid.UUID | None, Query()] = None,
    ) -> PaginatedResponse:
        _assert_tenant(db, tenant_id)
        page = cq.list_mapping_events(
            db,
            tenant_id=tenant_id,
            external_reference_id=external_reference_id,
            limit=limit,
            offset=offset,
        )
        items = [orm_to_dict(x) for x in page.items]
        return PaginatedResponse(total=page.total, limit=limit, offset=offset, items=items)

    @r.get("/tenants/{tenant_id}/canonical/actors/{actor_id}")
    def get_actor(
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        _assert_tenant(db, tenant_id)
        detail = cq.actor_detail(db, tenant_id=tenant_id, actor_id=actor_id)
        if detail is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Actor not found.") from None
        return detail

    @r.get("/tenants/{tenant_id}/canonical/artifacts/{artifact_id}")
    def get_artifact(
        tenant_id: uuid.UUID,
        artifact_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        _assert_tenant(db, tenant_id)
        detail = cq.artifact_detail(db, tenant_id=tenant_id, artifact_id=artifact_id)
        if detail is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Artifact not found.") from None
        return detail

    @r.get("/tenants/{tenant_id}/canonical/relationships/{relationship_id}")
    def get_relationship(
        tenant_id: uuid.UUID,
        relationship_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        _assert_tenant(db, tenant_id)
        detail = cq.relationship_detail(
            db,
            tenant_id=tenant_id,
            relationship_id=relationship_id,
        )
        if detail is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="Relationship not found.",
            ) from None
        return detail

    @r.get("/tenants/{tenant_id}/canonical/external-references/{xref_id}")
    def get_external_reference(
        tenant_id: uuid.UUID,
        xref_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
    ) -> dict[str, Any]:
        _assert_tenant(db, tenant_id)
        detail = cq.external_reference_detail(db, tenant_id=tenant_id, xref_id=xref_id)
        if detail is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                detail="External reference not found.",
            ) from None
        return detail

    @r.get("/tenants/{tenant_id}/canonical/status", response_model=CanonicalStatusResponse)
    def canonical_status(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        connection_id: Annotated[uuid.UUID, Query()],
        connector: Annotated[str, Query()] = CONNECTOR_GITHUB,
    ) -> CanonicalStatusResponse:
        _assert_tenant(db, tenant_id)
        if not dbg.connection_belongs_to_tenant(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Connection not found.") from None
        lag, meta = count_canonical_lag(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=connector,
        )
        cursor_row = db.get(Step3CanonicalCursor, (connection_id, connector))
        ts = cursor_row.last_processed_at if cursor_row else None
        return CanonicalStatusResponse(
            tenant_id=tenant_id,
            connection_id=connection_id,
            connector=connector,
            step3_last_processed_replay_sequence=int(meta["step3_last_processed_replay_sequence"]),
            step3_last_processed_id=int(meta["step3_last_processed_id"]),
            step3_lag_rows=lag,
            step3_last_processed_timestamp=ts,
            step2_watermark_replay_sequence=int(meta["step2_watermark_replay_sequence"]),
            step2_watermark_id=int(meta["step2_watermark_id"]),
        )

    @r.get("/tenants/{tenant_id}/canonical/subgraph", response_model=SubgraphResponse)
    def subgraph(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        artifact_id: Annotated[uuid.UUID | None, Query()] = None,
        actor_id: Annotated[uuid.UUID | None, Query()] = None,
        depth: Annotated[int, Query(ge=0, le=5)] = 2,
        include_historical: Annotated[bool, Query()] = False,
    ) -> SubgraphResponse:
        _assert_tenant(db, tenant_id)
        if (artifact_id is None) == (actor_id is None):
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Provide exactly one of artifact_id or actor_id.",
            ) from None
        if artifact_id is not None:
            anchor_lit: Literal["artifact", "actor"] = "artifact"
            anchor_uuid: uuid.UUID = artifact_id
        else:
            anchor_lit = "actor"
            assert actor_id is not None
            anchor_uuid = actor_id
        nodes, edges, trunc, treason = cq.build_subgraph(
            db,
            tenant_id=tenant_id,
            anchor_type=anchor_lit,
            anchor_id=anchor_uuid,
            depth=min(depth, 5),
            max_nodes=400,
            current_only=not include_historical,
        )
        return SubgraphResponse(
            anchor=SubgraphAnchor(type=anchor_lit, id=anchor_uuid),
            depth=depth,
            nodes=[SubgraphNode.model_validate(n) for n in nodes],
            edges=[
                SubgraphEdge(
                    id=uuid.UUID(e["id"]),
                    source_id=uuid.UUID(e["source_id"]),
                    target_id=uuid.UUID(e["target_id"]),
                    relation_kind=e["relation_kind"],
                    directed=bool(e["directed"]),
                    valid_from=e["valid_from"],
                    valid_to=e["valid_to"],
                )
                for e in edges
            ],
            truncated=trunc,
            truncation_reason=treason,
        )

    @r.post("/tenants/{tenant_id}/canonical/drain")
    def trigger_canonical_drain(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        connection_id: Annotated[uuid.UUID, Query()],
        connector: Annotated[str, Query()] = CONNECTOR_GITHUB,
    ) -> dict[str, Any]:
        _assert_tenant(db, tenant_id)
        if not dbg.connection_belongs_to_tenant(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Connection not found.") from None
        if connector == CONNECTOR_GITHUB:
            m = drain_github_canonical(
                db,
                tenant_id=tenant_id,
                connection_id=connection_id,
            )
        elif connector == CONNECTOR_LINEAR:
            m = drain_linear_canonical(
                db,
                tenant_id=tenant_id,
                connection_id=connection_id,
            )
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported connector for canonical drain: {connector}",
            ) from None
        return {
            "raw_rows_processed": m.raw_rows_processed,
            "batches_committed": m.batches_committed,
        }

    @r.post("/tenants/{tenant_id}/canonical/reset-and-resync")
    def reset_and_resync_canonical(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(settings_dep)],
        connection_id: Annotated[uuid.UUID, Query()],
        confirm: Annotated[str, Query()],
        connector: Annotated[str, Query()] = CONNECTOR_GITHUB,
    ) -> dict[str, Any]:
        if connector != CONNECTOR_GITHUB:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Only '{CONNECTOR_GITHUB}' is supported.",
            ) from None
        if confirm.strip().upper() != "RESET":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Missing confirmation. Pass confirm=RESET.",
            ) from None
        _assert_tenant(db, tenant_id)
        if not dbg.connection_belongs_to_tenant(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Connection not found.") from None

        reset_github_pipeline_state(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        run = run_github_poll_ingestion_for_tenant(db, settings, tenant_id)
        if run.status == RUN_STATUS_SUCCEEDED:
            p = drain_github_projections(
                db,
                tenant_id=tenant_id,
                connection_id=run.connection_id,
            )
            c = drain_github_canonical(
                db,
                tenant_id=tenant_id,
                connection_id=run.connection_id,
            )
        else:
            p = None
            c = None
        return {
            "reset": True,
            "connection_id": str(connection_id),
            "ingestion_run_id": str(run.id),
            "ingestion_status": run.status,
            "projection_rows_processed": p.raw_rows_processed if p else 0,
            "canonical_rows_processed": c.raw_rows_processed if c else 0,
            "warning": (
                None
                if run.status == RUN_STATUS_SUCCEEDED
                else "Ingestion failed; projections/canonical not drained."
            ),
        }

    @r.post("/tenants/{tenant_id}/canonical/rebuild-from-step1")
    def rebuild_from_step1_github(
        tenant_id: uuid.UUID,
        db: Annotated[Session, Depends(get_db)],
        connection_id: Annotated[uuid.UUID, Query()],
        confirm: Annotated[str, Query()],
        connector: Annotated[str, Query()] = CONNECTOR_GITHUB,
    ) -> dict[str, Any]:
        if connector != CONNECTOR_GITHUB:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Only '{CONNECTOR_GITHUB}' is supported.",
            ) from None
        if confirm.strip().upper() != "REBUILD":
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Missing confirmation. Pass confirm=REBUILD.",
            ) from None
        _assert_tenant(db, tenant_id)
        if not dbg.connection_belongs_to_tenant(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
        ):
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Connection not found.") from None
        p, c = rebuild_derived_from_step1_github(
            db,
            tenant_id=tenant_id,
            connection_id=connection_id,
        )
        return {
            "rebuilt_from_step1": True,
            "connection_id": str(connection_id),
            "projection_rows_processed": p.raw_rows_processed,
            "canonical_rows_processed": c.raw_rows_processed,
        }

    return r
