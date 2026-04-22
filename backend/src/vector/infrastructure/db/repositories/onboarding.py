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
