"""CRUD for onboarding_state (one row per tenant)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import asc, desc, inspect, select
from sqlalchemy.orm import Session

from vector.domains.onboarding.constants import STATUS_IN_PROGRESS, STEP_CHAT_PROFILE
from vector.infrastructure.db.models.onboarding_message import OnboardingMessage
from vector.infrastructure.db.models.onboarding_state import OnboardingState


def get_onboarding_for_tenant(session: Session, tenant_id: uuid.UUID) -> OnboardingState | None:
    stmt = select(OnboardingState).where(OnboardingState.tenant_id == tenant_id)
    return session.scalar(stmt)


def get_or_create_onboarding(session: Session, tenant_id: uuid.UUID) -> OnboardingState:
    row = get_onboarding_for_tenant(session, tenant_id)
    if row is not None:
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
    row = OnboardingMessage(
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        content=content,
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
        .order_by(desc(OnboardingMessage.created_at))
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
        .order_by(asc(OnboardingMessage.created_at))
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
