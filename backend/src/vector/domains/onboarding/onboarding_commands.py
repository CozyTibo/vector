"""HTTP-facing onboarding orchestration (state PATCH/GET/restart/complete, Slack members)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.contracts.onboarding import (
    OnboardingCompleteResponse,
    OnboardingGetResponse,
    OnboardingMessageItem,
    OnboardingPatchBody,
    SlackChannelItem,
    SlackChannelsResponse,
    SlackMembersResponse,
    SlackWorkspaceMemberItem,
)
from vector.domains.cortex.connectors.slack.onboarding_dm import (
    SLACK_HANDOFF_WELCOME_DM_SENT_FOR_USER_KEY,
    send_slack_handoff_welcome_dm,
)
from vector.domains.cortex.connectors.slack.workspace_channels import list_slack_workspace_public_channels
from vector.domains.cortex.connectors.slack.workspace_members import list_slack_workspace_members
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.domains.onboarding.constants import (
    ONBOARDING_STEPS,
    STATUS_COMPLETED,
    STEP_ADMIN_ACCESS,
    STEP_SLACK_COLLABORATORS_CONFIRM,
    STEP_SLACK_WATCH_CHANNELS,
    STEP_THANK_YOU,
)
from vector.domains.onboarding.errors import (
    InvalidOnboardingStepError,
    OnboardingAlreadyCompletedError,
    SlackMembersLoadError,
    SlackNotConnectedForWorkspaceError,
    WorkspaceSettingsForbiddenError,
)
from vector.domains.onboarding.onboarding_service import apply_patch_answers_to_profile_and_company
from vector.infrastructure.db.models.onboarding_state import OnboardingState
from vector.infrastructure.db.repositories import github_connection as gh_repo
from vector.infrastructure.db.repositories import linear_connection as linear_repo
from vector.infrastructure.db.repositories import notion_connection as notion_repo
from vector.infrastructure.db.repositories import onboarding as ob_repo
from vector.infrastructure.db.repositories import slack_connection as slack_repo
from vector.infrastructure.db.repositories import tenancy as tenancy_repo

_logger = logging.getLogger("app")


def _slack_stakeholders_user_chat_line(ss: Any) -> str | None:
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


def _slack_collaborators_structured_chat_content(raw: Any) -> str | None:
    """JSON user row for chat UI (same pattern as ``tools_selected``)."""
    if not isinstance(raw, dict):
        return None
    members = raw.get("members")
    if not isinstance(members, list) or not members:
        return None
    payload_members: list[dict[str, str]] = []
    for m in members:
        if not isinstance(m, dict):
            continue
        uid = m.get("slack_user_id")
        if not isinstance(uid, str) or not uid.strip():
            continue
        uid = uid.strip()
        un = m.get("username")
        username = un.strip().lstrip("@") if isinstance(un, str) and un.strip() else uid
        lab = m.get("label")
        label = lab.strip() if isinstance(lab, str) and lab.strip() else username
        payload_members.append(
            {"slack_user_id": uid, "username": username, "label": label},
        )
    if not payload_members:
        return None
    return json.dumps(
        {"type": "slack_collaborators_selected", "members": payload_members},
        separators=(",", ":"),
    )


def _slack_team_members_structured_chat_content(raw: Any) -> str | None:
    """JSON user row for team picks (same member shape as collaborators)."""
    if not isinstance(raw, dict):
        return None
    members = raw.get("members")
    if not isinstance(members, list) or not members:
        return None
    payload_members: list[dict[str, str]] = []
    for m in members:
        if not isinstance(m, dict):
            continue
        uid = m.get("slack_user_id")
        if not isinstance(uid, str) or not uid.strip():
            continue
        uid = uid.strip()
        un = m.get("username")
        username = un.strip().lstrip("@") if isinstance(un, str) and un.strip() else uid
        lab = m.get("label")
        label = lab.strip() if isinstance(lab, str) and lab.strip() else username
        payload_members.append(
            {"slack_user_id": uid, "username": username, "label": label},
        )
    if not payload_members:
        return None
    return json.dumps(
        {"type": "slack_team_members_selected", "members": payload_members},
        separators=(",", ":"),
    )


def _slack_manager_intro_consent_chat_content(raw: Any) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    choice = raw.strip().lower()
    if choice not in ("yes", "later", "not_applicable"):
        return None
    return json.dumps(
        {"type": "slack_manager_intro_consent", "choice": choice},
        separators=(",", ":"),
    )


def _slack_watch_channels_structured_chat_content(raw: Any) -> str | None:
    if not isinstance(raw, dict):
        return None
    channels = raw.get("channels")
    if not isinstance(channels, list) or not channels:
        return None
    payload: list[dict[str, str]] = []
    for ch in channels:
        if not isinstance(ch, dict):
            continue
        cid = ch.get("channel_id")
        if not isinstance(cid, str) or not cid.strip():
            continue
        cid = cid.strip()
        nm = ch.get("name")
        name = nm.strip().lstrip("#") if isinstance(nm, str) and nm.strip() else cid
        payload.append({"channel_id": cid, "name": name})
    if not payload:
        return None
    return json.dumps(
        {"type": "slack_watch_channels_selected", "channels": payload},
        separators=(",", ":"),
    )


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
    notion_connected: bool,
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
        notion_connected=notion_connected,
    )


def _maybe_send_slack_handoff_welcome_dm(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    merged_answers: dict[str, Any],
) -> bool:
    """Send optional short Slack handoff DM; return True if ``answers_json`` changed.

    Call only from ``complete_onboarding`` (not PATCH) so we never double-send when the client saves
    stakeholders and completes in the same flow.

    In-place JSON mutations on ``OnboardingState.answers_json`` are not always detected by SQLAlchemy;
    callers should assign ``row.answers_json = merged`` after this returns True.
    """
    sl = slack_repo.get_slack_connection_for_tenant(db, tenant_id)
    if sl is None:
        return False
    ss = merged_answers.get("slack_stakeholders")
    if not isinstance(ss, dict):
        return False
    ids = ss.get("slack_user_ids")
    if not isinstance(ids, list) or not ids:
        return False
    primary = str(ids[0]).strip()
    if not primary:
        return False
    if merged_answers.get(SLACK_HANDOFF_WELCOME_DM_SENT_FOR_USER_KEY) == primary:
        return False
    try:
        send_slack_handoff_welcome_dm(sl.detail.bot_access_token, primary)
    except Exception as e:
        _logger.warning(
            "Slack onboarding handoff welcome DM failed for tenant=%s slack_user=%s: %s",
            tenant_id,
            primary,
            e,
        )
        return False
    merged_answers[SLACK_HANDOFF_WELCOME_DM_SENT_FOR_USER_KEY] = primary
    return True


def _get_response_bundle(
    db: Session,
    tenant_id: uuid.UUID,
    row: OnboardingState,
) -> OnboardingGetResponse:
    gh = gh_repo.get_github_connection_for_tenant(db, tenant_id)
    lin = linear_repo.get_linear_connection_for_tenant(db, tenant_id)
    sl = slack_repo.get_slack_connection_for_tenant(db, tenant_id)
    nt = notion_repo.get_notion_connection_for_tenant(db, tenant_id)
    msgs = _load_onboarding_messages(db, tenant_id)
    return _row_to_response(
        row,
        github_connected=gh is not None,
        linear_connected=lin is not None,
        slack_connected=sl is not None,
        notion_connected=nt is not None,
        messages=msgs,
    )


def get_onboarding_state(db: Session, claims: SessionClaims) -> OnboardingGetResponse:
    row = ob_repo.get_or_create_onboarding(db, claims.tenant_id)
    db.commit()
    db.refresh(row)
    return _get_response_bundle(db, claims.tenant_id, row)


def restart_onboarding(db: Session, claims: SessionClaims) -> OnboardingGetResponse:
    row = ob_repo.hard_reset_onboarding_progress(db, tenant_id=claims.tenant_id)
    first_user = tenancy_repo.get_first_user_for_tenant(db, claims.tenant_id)
    if first_user is not None:
        first_user.full_name = None
    db.commit()
    db.refresh(row)
    return _get_response_bundle(db, claims.tenant_id, row)


def patch_onboarding(
    db: Session,
    claims: SessionClaims,
    body: OnboardingPatchBody,
) -> OnboardingGetResponse:
    row = ob_repo.get_or_create_onboarding(db, claims.tenant_id)
    if row.status == STATUS_COMPLETED:
        # Post-onboarding: owners may update workspace manager teams only (no step / chat side effects).
        if body.current_step is not None or body.answers is None:
            raise OnboardingAlreadyCompletedError
        keys = set(body.answers.keys())
        allowed_post_onboarding = frozenset(
            {"workspace_manager_teams", "vector_manager_access_mode", "vector_company_wide_users"}
        )
        if not keys or not keys.issubset(allowed_post_onboarding):
            raise OnboardingAlreadyCompletedError
        membership = tenancy_repo.get_membership_for_user_tenant(db, claims.user_id, claims.tenant_id)
        if membership is None or str(membership.role).strip().lower() != "owner":
            raise WorkspaceSettingsForbiddenError
        merged = ob_repo.deep_merge_answers_json(row.answers_json or {}, body.answers)
        ob_repo.normalize_workspace_manager_teams_in_place(merged)
        ob_repo.normalize_vector_manager_access_mode_in_place(merged)
        ob_repo.normalize_vector_company_wide_users_in_place(merged)
        row.answers_json = merged
        row.version = int(row.version) + 1
        db.commit()
        db.refresh(row)
        return _get_response_bundle(db, claims.tenant_id, row)
    if body.current_step is not None:
        if body.current_step not in ONBOARDING_STEPS:
            raise InvalidOnboardingStepError(body.current_step)
        row.current_step = body.current_step
    merged_snapshot: dict[str, Any] | None = None
    if body.answers is not None:
        merged = ob_repo.deep_merge_answers_json(row.answers_json or {}, body.answers)
        ob_repo.normalize_slack_stakeholders_in_place(merged)
        ob_repo.normalize_slack_collaborators_in_place(merged)
        ob_repo.normalize_slack_team_members_in_place(merged)
        ob_repo.normalize_slack_watch_channels_in_place(merged)
        ob_repo.normalize_slack_introduce_managers_consent_in_place(merged)
        ob_repo.normalize_vector_manager_access_mode_in_place(merged)
        ob_repo.normalize_vector_company_wide_users_in_place(merged)
        row.answers_json = merged
        merged_snapshot = merged
        apply_patch_answers_to_profile_and_company(
            db,
            user_id=claims.user_id,
            tenant_id=claims.tenant_id,
            answers=body.answers,
        )

    if body.current_step == STEP_SLACK_WATCH_CHANNELS and ob_repo.onboarding_messages_table_exists(db):
        snap_watch: dict[str, Any] = (
            merged_snapshot if merged_snapshot is not None else dict(row.answers_json or {})
        )
        team_line = _slack_team_members_structured_chat_content(snap_watch.get("slack_team_members"))
        if team_line:
            prior_tm = ob_repo.list_onboarding_messages_chronological(
                db,
                claims.tenant_id,
                limit=200,
            )
            last_tm = prior_tm[-1] if prior_tm else None
            if not (last_tm is not None and last_tm.role == "user" and last_tm.content == team_line):
                ob_repo.append_onboarding_message(
                    db,
                    tenant_id=claims.tenant_id,
                    user_id=claims.user_id,
                    role="user",
                    content=team_line,
                )

    if body.current_step == STEP_SLACK_COLLABORATORS_CONFIRM and ob_repo.onboarding_messages_table_exists(
        db
    ):
        snap_collab: dict[str, Any] = (
            merged_snapshot if merged_snapshot is not None else dict(row.answers_json or {})
        )
        collab_line = _slack_collaborators_structured_chat_content(snap_collab.get("slack_collaborators"))
        if collab_line:
            prior_collab = ob_repo.list_onboarding_messages_chronological(
                db,
                claims.tenant_id,
                limit=200,
            )
            last_collab = prior_collab[-1] if prior_collab else None
            if not (
                last_collab is not None
                and last_collab.role == "user"
                and last_collab.content == collab_line
            ):
                ob_repo.append_onboarding_message(
                    db,
                    tenant_id=claims.tenant_id,
                    user_id=claims.user_id,
                    role="user",
                    content=collab_line,
                )

    if body.current_step == STEP_ADMIN_ACCESS and ob_repo.onboarding_messages_table_exists(db):
        snap: dict[str, Any] = (
            merged_snapshot if merged_snapshot is not None else dict(row.answers_json or {})
        )
        for line in (
            _slack_stakeholders_user_chat_line(snap.get("slack_stakeholders")),
            _slack_watch_channels_structured_chat_content(snap.get("slack_watch_channels")),
        ):
            if not line:
                continue
            prior = ob_repo.list_onboarding_messages_chronological(
                db,
                claims.tenant_id,
                limit=200,
            )
            last = prior[-1] if prior else None
            if last is not None and last.role == "user" and last.content == line:
                continue
            ob_repo.append_onboarding_message(
                db,
                tenant_id=claims.tenant_id,
                user_id=claims.user_id,
                role="user",
                content=line,
            )

    if merged_snapshot is not None and ob_repo.onboarding_messages_table_exists(db):
        consent_line = _slack_manager_intro_consent_chat_content(
            merged_snapshot.get("slack_introduce_managers_consent"),
        )
        if consent_line:
            prior_c = ob_repo.list_onboarding_messages_chronological(
                db,
                claims.tenant_id,
                limit=200,
            )
            last_c = prior_c[-1] if prior_c else None
            if not (
                last_c is not None
                and last_c.role == "user"
                and last_c.content == consent_line
            ):
                ob_repo.append_onboarding_message(
                    db,
                    tenant_id=claims.tenant_id,
                    user_id=claims.user_id,
                    role="user",
                    content=consent_line,
                )

    row.version = int(row.version) + 1
    db.commit()
    db.refresh(row)
    return _get_response_bundle(db, claims.tenant_id, row)


def list_slack_workspace_members_for_onboarding(
    db: Session,
    claims: SessionClaims,
) -> SlackMembersResponse:
    link = slack_repo.get_slack_connection_for_tenant(db, claims.tenant_id)
    if link is None:
        raise SlackNotConnectedForWorkspaceError
    try:
        raw = list_slack_workspace_members(link.detail.bot_access_token)
    except Exception as e:
        raise SlackMembersLoadError(f"Could not load Slack members: {e!s}") from e
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


def list_slack_workspace_channels_for_onboarding(
    db: Session,
    claims: SessionClaims,
) -> SlackChannelsResponse:
    link = slack_repo.get_slack_connection_for_tenant(db, claims.tenant_id)
    if link is None:
        raise SlackNotConnectedForWorkspaceError
    try:
        raw = list_slack_workspace_public_channels(link.detail.bot_access_token)
    except Exception as e:
        raise SlackMembersLoadError(f"Could not load Slack channels: {e!s}") from e
    items = [
        SlackChannelItem(
            id=str(ch["id"]),
            name=str(ch.get("name") or ch["id"]),
        )
        for ch in raw
        if isinstance(ch, dict) and ch.get("id")
    ]
    return SlackChannelsResponse(channels=items)


def complete_onboarding(db: Session, claims: SessionClaims) -> OnboardingCompleteResponse:
    row = ob_repo.get_or_create_onboarding(db, claims.tenant_id, with_for_update=True)
    now = datetime.now(UTC)
    if row.status != STATUS_COMPLETED:
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


def dev_force_complete_website_onboarding_for_tenant(
    db: Session,
    *,
    tenant_id: uuid.UUID,
) -> OnboardingCompleteResponse:
    """Mark website onboarding completed without Slack handoff (admin / local dev only).

    Call sites must enforce ``ENV=development``; does not send Slack DMs.
    """
    row = ob_repo.get_or_create_onboarding(db, tenant_id)
    now = datetime.now(UTC)
    if row.status != STATUS_COMPLETED:
        row.status = STATUS_COMPLETED
        row.current_step = STEP_THANK_YOU
        row.completed_at = now
        row.version = int(row.version) + 1
    db.flush()
    db.refresh(row)
    return OnboardingCompleteResponse(
        status=row.status,
        current_step=row.current_step,
        completed_at=row.completed_at or now,
    )
