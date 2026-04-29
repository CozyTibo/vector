"""CRUD for onboarding_state (one row per tenant)."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import asc, delete, desc, inspect, select
from sqlalchemy.orm import Session

from vector.domains.onboarding.constants import (
    PROFILE_PHASE_NAME,
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STEP_CHAT_PROFILE,
    STEP_SCANNING,
)
from vector.domains.onboarding.onboarding_flow import _first_connect_step
from vector.infrastructure.db.models.onboarding_message import OnboardingMessage
from vector.infrastructure.db.models.onboarding_state import OnboardingState

log = logging.getLogger("app")


def get_onboarding_for_tenant(session: Session, tenant_id: uuid.UUID) -> OnboardingState | None:
    stmt = select(OnboardingState).where(OnboardingState.tenant_id == tenant_id)
    return session.scalar(stmt)


def get_onboarding_for_tenant_for_update(session: Session, tenant_id: uuid.UUID) -> OnboardingState | None:
    stmt = select(OnboardingState).where(OnboardingState.tenant_id == tenant_id).with_for_update()
    return session.scalar(stmt)


# Historical `current_step` values that may still exist in DB rows (never valid for new PATCHes).
_LEGACY_DB_ONBOARDING_STEPS = frozenset({"CONNECT_GITHUB", "CONNECT_LINEAR"})
_ALLOWED_CONNECT_QUEUE_IDS = frozenset({"slack", "comm_placeholder", "linear", "github"})


def normalize_onboarding_row_removed_steps(row: OnboardingState) -> None:
    """Coerce legacy connector step names and strip unknown ``connect_queue`` ids."""
    if row.status == STATUS_COMPLETED:
        return
    answers = dict(row.answers_json or {})
    changed = False
    for key in ("connect_queue", "connect_plan"):
        raw = answers.get(key)
        if not isinstance(raw, list):
            continue
        cleaned = [x for x in raw if isinstance(x, str) and x in _ALLOWED_CONNECT_QUEUE_IDS]
        if cleaned != raw:
            answers[key] = cleaned
            changed = True
    if row.current_step in _LEGACY_DB_ONBOARDING_STEPS:
        cq = answers.get("connect_queue")
        allowed = [
            x
            for x in (cq if isinstance(cq, list) else [])
            if isinstance(x, str) and x in _ALLOWED_CONNECT_QUEUE_IDS
        ]
        row.current_step = _first_connect_step(allowed) if allowed else STEP_SCANNING
        changed = True
    if changed:
        row.answers_json = answers
        row.version = int(row.version) + 1


def get_or_create_onboarding(
    session: Session, tenant_id: uuid.UUID, *, with_for_update: bool = False
) -> OnboardingState:
    row = (
        get_onboarding_for_tenant_for_update(session, tenant_id)
        if with_for_update
        else get_onboarding_for_tenant(session, tenant_id)
    )
    if row is not None:
        normalize_onboarding_row_removed_steps(row)
        return row
    now = datetime.now(UTC)
    row = OnboardingState(
        tenant_id=tenant_id,
        status=STATUS_IN_PROGRESS,
        current_step=STEP_CHAT_PROFILE,
        answers_json={},
        version=1,
        started_at=now,
    )
    session.add(row)
    session.flush()
    return row


_NESTED_ANSWER_KEYS = frozenset({"profile", "company", "tools"})


def deep_merge_answers_json(existing: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(existing)
    for k, v in patch.items():
        if k in _NESTED_ANSWER_KEYS and isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = {**out[k], **v}
        elif k in _NESTED_ANSWER_KEYS and isinstance(v, dict):
            out[k] = dict(v)
        else:
            out[k] = v
    return out


def normalize_slack_stakeholders_in_place(answers: dict[str, Any]) -> None:
    """Dedupe slack_user_ids (first wins); keep mention_labels aligned when present."""
    ss = answers.get("slack_stakeholders")
    if not isinstance(ss, dict):
        return
    ids = ss.get("slack_user_ids")
    if not isinstance(ids, list):
        return
    id_strs = [str(x) for x in ids if isinstance(x, str)]
    raw_labels = ss.get("mention_labels")
    label_strs: list[str] | None = None
    if isinstance(raw_labels, list):
        label_strs = [str(x) for x in raw_labels if isinstance(x, str)]
        if len(label_strs) != len(id_strs):
            label_strs = None
    seen: set[str] = set()
    out_ids: list[str] = []
    out_labels: list[str] = []
    for i, uid in enumerate(id_strs):
        if uid in seen:
            continue
        seen.add(uid)
        out_ids.append(uid)
        if label_strs is not None and i < len(label_strs):
            out_labels.append(label_strs[i])
        else:
            out_labels.append(uid)
    ss["slack_user_ids"] = out_ids
    if label_strs is not None:
        ss["mention_labels"] = out_labels
    elif "mention_labels" in ss:
        del ss["mention_labels"]


def normalize_slack_collaborators_in_place(answers: dict[str, Any]) -> None:
    """Keep ``slack_collaborators.members`` as deduped dict rows with string fields."""
    raw = answers.get("slack_collaborators")
    if not isinstance(raw, dict):
        return
    members = raw.get("members")
    if not isinstance(members, list):
        return
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for m in members:
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
        username = un.strip().lstrip("@") if isinstance(un, str) else uid
        lab = m.get("label")
        label = lab.strip() if isinstance(lab, str) and lab.strip() else username
        out.append(
            {
                "slack_user_id": uid,
                "username": username,
                "label": label,
            }
        )
    raw["members"] = out


def normalize_slack_team_members_in_place(answers: dict[str, Any]) -> None:
    """Same shape as ``slack_collaborators.members`` under ``slack_team_members``."""
    raw = answers.get("slack_team_members")
    if not isinstance(raw, dict):
        return
    members = raw.get("members")
    if not isinstance(members, list):
        return
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for m in members:
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
        username = un.strip().lstrip("@") if isinstance(un, str) else uid
        lab = m.get("label")
        label = lab.strip() if isinstance(lab, str) and lab.strip() else username
        out.append(
            {
                "slack_user_id": uid,
                "username": username,
                "label": label,
            }
        )
    raw["members"] = out


def normalize_slack_watch_channels_in_place(answers: dict[str, Any]) -> None:
    """Dedupe ``slack_watch_channels.channels`` by ``channel_id``."""
    raw = answers.get("slack_watch_channels")
    if not isinstance(raw, dict):
        return
    channels = raw.get("channels")
    if not isinstance(channels, list):
        return
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for ch in channels:
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
        out.append({"channel_id": cid, "name": name})
    raw["channels"] = out


_SLACK_INTRODUCE_MANAGERS_CONSENT_VALUES = frozenset({"yes", "later", "not_applicable"})


def normalize_slack_introduce_managers_consent_in_place(answers: dict[str, Any]) -> None:
    """Coerce ``slack_introduce_managers_consent`` to yes | later | not_applicable or drop."""
    raw = answers.get("slack_introduce_managers_consent")
    if raw is None:
        return
    if not isinstance(raw, str):
        answers.pop("slack_introduce_managers_consent", None)
        return
    v = raw.strip().lower()
    if v in ("yes", "y", "allow", "sure", "ok", "okay"):
        answers["slack_introduce_managers_consent"] = "yes"
        return
    if v in ("later", "defer", "maybe_later", "not_now", "skip"):
        answers["slack_introduce_managers_consent"] = "later"
        return
    if v in ("not_applicable", "na", "skipped", "none", "n/a"):
        answers["slack_introduce_managers_consent"] = "not_applicable"
        return
    if v in _SLACK_INTRODUCE_MANAGERS_CONSENT_VALUES:
        answers["slack_introduce_managers_consent"] = v
        return
    answers.pop("slack_introduce_managers_consent", None)


def normalize_workspace_manager_teams_in_place(answers: dict[str, Any]) -> None:
    """Product workspace page: teams of Slack-backed managers (post-onboarding)."""
    raw = answers.get("workspace_manager_teams")
    if not isinstance(raw, dict):
        answers.pop("workspace_manager_teams", None)
        return
    teams = raw.get("teams")
    if not isinstance(teams, list):
        answers.pop("workspace_manager_teams", None)
        return
    out_teams: list[dict[str, Any]] = []
    for t in teams:
        if not isinstance(t, dict):
            continue
        tid_raw = t.get("id")
        try:
            tid = str(uuid.UUID(str(tid_raw))) if tid_raw else str(uuid.uuid4())
        except (ValueError, TypeError):
            tid = str(uuid.uuid4())
        name = str(t.get("name") or "").strip() or "Team"
        members_raw = t.get("members")
        seen: set[str] = set()
        members_out: list[dict[str, str]] = []
        if isinstance(members_raw, list):
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
                members_out.append(
                    {
                        "slack_user_id": uid,
                        "username": username,
                        "label": label,
                    },
                )
        member_ids = {m["slack_user_id"] for m in members_out}
        mgr_raw = t.get("manager_slack_user_id")
        manager_out: str | None = None
        if isinstance(mgr_raw, str) and mgr_raw.strip() in member_ids:
            manager_out = mgr_raw.strip()
        row: dict[str, Any] = {"id": tid, "name": name, "members": members_out}
        if manager_out is not None:
            row["manager_slack_user_id"] = manager_out
        out_teams.append(row)
    raw["teams"] = out_teams


def hard_reset_onboarding_progress(session: Session, *, tenant_id: uuid.UUID) -> OnboardingState:
    """Delete persisted chat rows and reset onboarding answers/step to a fresh chat-profile start.

    Seeds ``profile_phase`` so admin and the chat FSM match a day-one name prompt. Connectors stay
    linked. Display name copied from onboarding is cleared in ``POST /onboarding/restart``.
    """
    try:
        session.execute(delete(OnboardingMessage).where(OnboardingMessage.tenant_id == tenant_id))
    except Exception:
        log.debug("onboarding_messages delete skipped for %s", tenant_id, exc_info=True)
    row = get_onboarding_for_tenant(session, tenant_id)
    now = datetime.now(UTC)
    if row is None:
        row = get_or_create_onboarding(session, tenant_id)
        row.answers_json = {"profile_phase": PROFILE_PHASE_NAME}
        return row
    row.status = STATUS_IN_PROGRESS
    row.current_step = STEP_CHAT_PROFILE
    row.answers_json = {"profile_phase": PROFILE_PHASE_NAME}
    row.completed_at = None
    row.abandoned_at = None
    row.started_at = now
    row.version = int(row.version) + 1
    return row


def merge_answers_json(existing: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """PATCH /onboarding merges nested profile/company/tools like chat."""
    return deep_merge_answers_json(existing, patch)


def onboarding_messages_table_exists(session: Session) -> bool:
    bind = session.get_bind()
    if bind is None:
        return False
    try:
        return inspect(bind).has_table("onboarding_messages")
    except Exception:
        return False


def append_onboarding_message(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
    content: str,
) -> OnboardingMessage:
    # Use a fresh clock time per row. PostgreSQL ``now()`` / ``server_default`` is fixed for the
    # whole transaction, so user + assistant lines from one /onboarding/chat commit would otherwise
    # share identical ``created_at``; tie-breaking by UUID is not insertion order and scrambles the
    # transcript (admin + product history).
    row = OnboardingMessage(
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        content=content,
        created_at=datetime.now(UTC),
    )
    session.add(row)
    session.flush()
    return row


def list_recent_onboarding_messages(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    limit: int = 50,
) -> list[OnboardingMessage]:
    stmt = (
        select(OnboardingMessage)
        .where(OnboardingMessage.tenant_id == tenant_id)
        .order_by(desc(OnboardingMessage.created_at), desc(OnboardingMessage.id))
        .limit(limit)
    )
    return list(session.scalars(stmt).all())


def list_onboarding_messages_chronological(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    limit: int = 200,
) -> list[OnboardingMessage]:
    stmt = (
        select(OnboardingMessage)
        .where(OnboardingMessage.tenant_id == tenant_id)
        .order_by(asc(OnboardingMessage.created_at), asc(OnboardingMessage.id))
        .limit(limit)
    )
    return list(session.scalars(stmt).all())


def list_onboarding_for_tenants(
    session: Session,
    tenant_ids: list[uuid.UUID],
) -> dict[uuid.UUID, OnboardingState]:
    if not tenant_ids:
        return {}
    stmt = select(OnboardingState).where(OnboardingState.tenant_id.in_(tenant_ids))
    rows = list(session.scalars(stmt).all())
    return {r.tenant_id: r for r in rows}
