"""Design-partner onboarding — state in onboarding_state; connectors unchanged."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from vector.api.http.deps import get_db, get_session_claims
from vector.contracts.onboarding import (
    OnboardingChatRequest,
    OnboardingChatResponse,
    OnboardingCompleteResponse,
    OnboardingGetResponse,
    OnboardingMessageItem,
    OnboardingPatchBody,
    SlackMembersResponse,
    SlackWorkspaceMemberItem,
)
from vector.domains.connectors.slack.onboarding_dm import (
    SLACK_HANDOFF_WELCOME_DM_SENT_FOR_USER_KEY,
    send_slack_handoff_welcome_dm,
)
from vector.domains.connectors.slack.workspace_members import list_slack_workspace_members
from vector.domains.identity_access.errors import NoMembershipError
from vector.domains.identity_access.services.me_read import assert_membership
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.domains.onboarding.constants import (
    ONBOARDING_STEPS,
    STATUS_COMPLETED,
    STEP_ADMIN_ACCESS,
    STEP_THANK_YOU,
)
from vector.domains.onboarding.onboarding_service import process_onboarding_chat
from vector.infrastructure.db.models.onboarding_state import OnboardingState
from vector.infrastructure.db.repositories import github_connection as gh_repo
from vector.infrastructure.db.repositories import linear_connection as linear_repo
from vector.infrastructure.db.repositories import onboarding as ob_repo
from vector.infrastructure.db.repositories import slack_connection as slack_repo
from vector.infrastructure.db.repositories import tenancy as tenancy_repo

_logger = logging.getLogger("app")


def _manager_ob_intro_already_sent(db: Session, tenant_id: uuid.UUID, slack_user_id: str) -> bool:
    """True when a manager OB session exists and the Slack intro was already posted."""
    from vector.infrastructure.db.repositories import manager_onboarding as mo_repo

    sess = mo_repo.get_session_for_tenant_slack_user(
        db,
        tenant_id=tenant_id,
        slack_user_id=slack_user_id,
    )
    if sess is None:
        return False
    ctx = dict(sess.context_json or {})
    return bool(ctx.get("intro_sent"))


def _enqueue_manager_slack_onboarding_intro_if_needed(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    slack_user_id: str,
) -> None:
    """Queue Celery intro when the feature flag is on and we have not posted intro yet."""
    try:
        from vector.settings import get_settings

        if not get_settings().manager_slack_onboarding_enabled:
            return
        if _manager_ob_intro_already_sent(db, tenant_id, slack_user_id):
            return
        from app.tasks.manager_onboarding import send_manager_onboarding_intro_task

        send_manager_onboarding_intro_task.delay(str(tenant_id), slack_user_id)
    except Exception as exc:
        _logger.warning(
            "Could not enqueue manager Slack onboarding intro tenant=%s: %s",
            tenant_id,
            exc,
        )


def _slack_stakeholders_user_chat_line(ss: Any) -> str | None:
    """Readable line to persist as a user chat turn (matches what the Slack composer shows)."""
    if not isinstance(ss, dict):
        return None
    raw = ss.get("raw_text")
    if isinstance(raw, str):
        t = raw.strip()
        if t:
            return t
    labels = ss.get("mention_labels")
    if isinstance(labels, list) and labels:
        parts: list[str] = []
        for x in labels:
            if not isinstance(x, str):
                continue
            lab = x.strip()
            if not lab:
                continue
            parts.append(lab if lab.startswith("@") else f"@{lab}")
        if parts:
            return " ".join(parts)
    ids = ss.get("slack_user_ids")
    if isinstance(ids, list) and ids:
        id_strs = [str(x) for x in ids if x]
        if id_strs:
            return " ".join(id_strs)
    return None


def _load_onboarding_messages(db: Session, tenant_id: uuid.UUID) -> list[OnboardingMessageItem]:
    if not ob_repo.onboarding_messages_table_exists(db):
        return []
    rows = ob_repo.list_onboarding_messages_chronological(db, tenant_id, limit=200)
    return [
        OnboardingMessageItem(
            id=r.id,
            role=r.role,
            content=r.content,
            created_at=r.created_at,
        )
        for r in rows
    ]


def _row_to_response(
    row: OnboardingState,
    *,
    github_connected: bool,
    linear_connected: bool,
    slack_connected: bool,
    messages: list[OnboardingMessageItem],
) -> OnboardingGetResponse:
    return OnboardingGetResponse(
        id=row.id,
        status=row.status,
        current_step=row.current_step,
        answers=dict(row.answers_json or {}),
        version=row.version,
        started_at=row.started_at,
        completed_at=row.completed_at,
        abandoned_at=row.abandoned_at,
        messages=messages,
        github_connected=github_connected,
        linear_connected=linear_connected,
        slack_connected=slack_connected,
    )


def _apply_profile_patch(session: Session, user_id: uuid.UUID, patch: dict[str, Any]) -> None:
    nested = patch.get("profile")
    if not isinstance(nested, dict):
        return
    raw = nested.get("name")
    if not isinstance(raw, str):
        return
    name = raw.strip()
    if not name:
        return
    user = tenancy_repo.get_user_by_id(session, user_id)
    if user is None:
        return
    user.full_name = name


def _apply_company_patch(session: Session, tenant_id: uuid.UUID, patch: dict[str, Any]) -> None:
    tenant = tenancy_repo.get_tenant_by_id(session, tenant_id)
    if tenant is None:
        return
    raw = patch.get("company_name")
    if isinstance(raw, str):
        name = raw.strip()
        if name:
            tenant.company_name = name
    nested = patch.get("company")
    if isinstance(nested, dict):
        n = nested.get("name")
        if isinstance(n, str):
            name2 = n.strip()
            if name2:
                tenant.company_name = name2


def _maybe_send_slack_handoff_welcome_dm(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    merged_answers: dict[str, Any],
) -> None:
    """DM the mapped Slack user as soon as handoff is saved (before /onboarding/complete)."""
    sl = slack_repo.get_slack_connection_for_tenant(db, tenant_id)
    if sl is None:
        return
    ss = merged_answers.get("slack_stakeholders")
    if not isinstance(ss, dict):
        return
    ids = ss.get("slack_user_ids")
    if not isinstance(ids, list) or not ids:
        return
    primary = str(ids[0]).strip()
    if not primary:
        return
    if merged_answers.get(SLACK_HANDOFF_WELCOME_DM_SENT_FOR_USER_KEY) == primary:
        # Welcome DM was already sent; still enqueue manager OB if the flag was turned on later
        # (intro enqueue used to run only after the first Hi, so it was skipped forever).
        _enqueue_manager_slack_onboarding_intro_if_needed(
            db,
            tenant_id=tenant_id,
            slack_user_id=primary,
        )
        return
    try:
        send_slack_handoff_welcome_dm(sl.detail.bot_access_token, primary)
    except Exception as e:
        _logger.warning(
            "Slack onboarding handoff welcome DM failed for tenant=%s slack_user=%s: %s",
            tenant_id,
            primary,
            e,
        )
        return
    merged_answers[SLACK_HANDOFF_WELCOME_DM_SENT_FOR_USER_KEY] = primary
    _enqueue_manager_slack_onboarding_intro_if_needed(
        db,
        tenant_id=tenant_id,
        slack_user_id=primary,
    )


def build_onboarding_router() -> APIRouter:
    r = APIRouter(prefix="/onboarding", tags=["onboarding"])

    @r.get("", response_model=OnboardingGetResponse)
    def get_onboarding(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> OnboardingGetResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        row = ob_repo.get_or_create_onboarding(db, claims.tenant_id)
        db.commit()
        db.refresh(row)
        gh = gh_repo.get_github_connection_for_tenant(db, claims.tenant_id)
        lin = linear_repo.get_linear_connection_for_tenant(db, claims.tenant_id)
        sl = slack_repo.get_slack_connection_for_tenant(db, claims.tenant_id)
        msgs = _load_onboarding_messages(db, claims.tenant_id)
        return _row_to_response(
            row,
            github_connected=gh is not None,
            linear_connected=lin is not None,
            slack_connected=sl is not None,
            messages=msgs,
        )

    @r.post("/restart", response_model=OnboardingGetResponse)
    def restart_onboarding(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> OnboardingGetResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        row = ob_repo.hard_reset_onboarding_progress(db, tenant_id=claims.tenant_id)
        first_user = tenancy_repo.get_first_user_for_tenant(db, claims.tenant_id)
        if first_user is not None:
            first_user.full_name = None
        db.commit()
        db.refresh(row)
        gh = gh_repo.get_github_connection_for_tenant(db, claims.tenant_id)
        lin = linear_repo.get_linear_connection_for_tenant(db, claims.tenant_id)
        sl = slack_repo.get_slack_connection_for_tenant(db, claims.tenant_id)
        msgs = _load_onboarding_messages(db, claims.tenant_id)
        return _row_to_response(
            row,
            github_connected=gh is not None,
            linear_connected=lin is not None,
            slack_connected=sl is not None,
            messages=msgs,
        )

    @r.patch("", response_model=OnboardingGetResponse)
    def patch_onboarding(
        body: OnboardingPatchBody,
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> OnboardingGetResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        row = ob_repo.get_or_create_onboarding(db, claims.tenant_id)
        if row.status == STATUS_COMPLETED:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Onboarding already completed.",
            ) from None
        if body.current_step is not None:
            if body.current_step not in ONBOARDING_STEPS:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid current_step: {body.current_step!r}.",
                ) from None
            row.current_step = body.current_step
        merged_snapshot: dict[str, Any] | None = None
        if body.answers is not None:
            merged = ob_repo.deep_merge_answers_json(row.answers_json or {}, body.answers)
            ob_repo.normalize_slack_stakeholders_in_place(merged)
            row.answers_json = merged
            merged_snapshot = merged
            _apply_profile_patch(db, claims.user_id, body.answers)
            _apply_company_patch(db, claims.tenant_id, body.answers)

        if (
            body.current_step == STEP_ADMIN_ACCESS
            and body.answers is not None
            and "slack_stakeholders" in body.answers
            and merged_snapshot is not None
        ):
            if ob_repo.onboarding_messages_table_exists(db):
                line = _slack_stakeholders_user_chat_line(merged_snapshot.get("slack_stakeholders"))
                if line:
                    prior = ob_repo.list_onboarding_messages_chronological(
                        db, claims.tenant_id, limit=200
                    )
                    last = prior[-1] if prior else None
                    if not (last is not None and last.role == "user" and last.content == line):
                        ob_repo.append_onboarding_message(
                            db,
                            tenant_id=claims.tenant_id,
                            user_id=claims.user_id,
                            role="user",
                            content=line,
                        )

            _maybe_send_slack_handoff_welcome_dm(
                db,
                tenant_id=claims.tenant_id,
                merged_answers=merged_snapshot,
            )

        row.version = int(row.version) + 1
        db.commit()
        db.refresh(row)
        gh = gh_repo.get_github_connection_for_tenant(db, claims.tenant_id)
        lin = linear_repo.get_linear_connection_for_tenant(db, claims.tenant_id)
        sl = slack_repo.get_slack_connection_for_tenant(db, claims.tenant_id)
        msgs = _load_onboarding_messages(db, claims.tenant_id)
        return _row_to_response(
            row,
            github_connected=gh is not None,
            linear_connected=lin is not None,
            slack_connected=sl is not None,
            messages=msgs,
        )

    @r.post("/chat", response_model=OnboardingChatResponse)
    def post_onboarding_chat(
        body: OnboardingChatRequest,
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> OnboardingChatResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        return process_onboarding_chat(db, claims, body)

    @r.get("/slack-members", response_model=SlackMembersResponse)
    def get_slack_workspace_members(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> SlackMembersResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        link = slack_repo.get_slack_connection_for_tenant(db, claims.tenant_id)
        if link is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Slack is not connected for this workspace.",
            ) from None
        try:
            raw = list_slack_workspace_members(link.detail.bot_access_token)
        except Exception as e:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not load Slack members: {e!s}",
            ) from e
        items = [
            SlackWorkspaceMemberItem(
                id=str(m["id"]),
                label=str(m["label"]),
                username=str(m.get("username") or m["id"]),
                email=m.get("email") if isinstance(m.get("email"), str) else None,
                image_48=m.get("image_48"),
            )
            for m in raw
            if isinstance(m, dict) and m.get("id") and m.get("label")
        ]
        return SlackMembersResponse(members=items)

    @r.post("/complete", response_model=OnboardingCompleteResponse)
    def complete_onboarding(
        db: Annotated[Session, Depends(get_db)],
        claims: Annotated[SessionClaims, Depends(get_session_claims)],
    ) -> OnboardingCompleteResponse:
        try:
            assert_membership(db, claims)
        except NoMembershipError as e:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail=str(e)) from e
        row = ob_repo.get_or_create_onboarding(db, claims.tenant_id)
        now = datetime.now(UTC)
        if row.status != STATUS_COMPLETED:
            # Second chance if PATCH → ADMIN_ACCESS missed the DM (transient Slack error, etc.).
            merged = dict(row.answers_json or {})
            _maybe_send_slack_handoff_welcome_dm(
                db,
                tenant_id=claims.tenant_id,
                merged_answers=merged,
            )
            row.answers_json = merged
            row.status = STATUS_COMPLETED
            row.current_step = STEP_THANK_YOU
            row.completed_at = now
            row.version = int(row.version) + 1
            db.commit()
        db.refresh(row)
        return OnboardingCompleteResponse(
            status=row.status,
            current_step=row.current_step,
            completed_at=row.completed_at or now,
        )

    return r
