"""CRUD for manager Slack onboarding."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.manager_onboarding_channel_observation import (
    ManagerOnboardingChannelObservation,
)
from vector.infrastructure.db.models.manager_onboarding_invitation import (
    ManagerOnboardingInvitation,
)
from vector.infrastructure.db.models.manager_onboarding_message import ManagerOnboardingMessage
from vector.infrastructure.db.models.manager_onboarding_parse_artifact import (
    ManagerOnboardingParseArtifact,
)
from vector.infrastructure.db.models.manager_onboarding_session import ManagerOnboardingSession
from vector.infrastructure.db.models.manager_onboarding_slack_event_dedup import (
    ManagerOnboardingSlackEventDedup,
)


def get_session_for_tenant_slack_user(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    slack_user_id: str,
) -> ManagerOnboardingSession | None:
    uid = slack_user_id.strip()
    if not uid:
        return None
    stmt = select(ManagerOnboardingSession).where(
        ManagerOnboardingSession.tenant_id == tenant_id,
        ManagerOnboardingSession.slack_user_id == uid,
    )
    return session.scalar(stmt)


def create_session(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    slack_team_id: str,
    slack_user_id: str,
    app_user_id: uuid.UUID | None = None,
    parent_session_id: uuid.UUID | None = None,
    initial_step: str,
    status: str,
) -> ManagerOnboardingSession:
    row = ManagerOnboardingSession(
        tenant_id=tenant_id,
        slack_team_id=slack_team_id.strip(),
        slack_user_id=slack_user_id.strip(),
        app_user_id=app_user_id,
        parent_session_id=parent_session_id,
        status=status,
        current_step=initial_step,
        answers_json={},
        context_json={},
    )
    session.add(row)
    session.flush()
    return row


def append_message(
    session: Session,
    *,
    session_id: uuid.UUID,
    direction: str,
    role: str,
    text: str,
    slack_channel_id: str | None = None,
    slack_ts: str | None = None,
    thread_ts: str | None = None,
    slack_event_id: str | None = None,
    ingestion_kind: str = "message",
    outbound_idempotency_key: str | None = None,
) -> ManagerOnboardingMessage:
    row = ManagerOnboardingMessage(
        session_id=session_id,
        direction=direction,
        role=role,
        text=text,
        slack_channel_id=slack_channel_id,
        slack_ts=slack_ts,
        thread_ts=thread_ts,
        slack_event_id=slack_event_id,
        ingestion_kind=ingestion_kind,
        outbound_idempotency_key=outbound_idempotency_key,
    )
    session.add(row)
    session.flush()
    return row


def try_claim_slack_event(session: Session, event_id: str) -> bool:
    """Return True if this event_id was newly claimed (should process)."""
    eid = event_id.strip()
    if not eid:
        return True
    try:
        with session.begin_nested():
            session.add(ManagerOnboardingSlackEventDedup(event_id=eid))
            session.flush()
        return True
    except IntegrityError:
        return False


def get_outbound_by_idempotency_key(
    session: Session,
    key: str,
) -> ManagerOnboardingMessage | None:
    k = key.strip()
    if not k:
        return None
    stmt = select(ManagerOnboardingMessage).where(
        ManagerOnboardingMessage.outbound_idempotency_key == k,
    )
    return session.scalar(stmt)


def delete_messages_for_session(session: Session, session_id: uuid.UUID) -> None:
    session.execute(
        delete(ManagerOnboardingMessage).where(ManagerOnboardingMessage.session_id == session_id),
    )


def delete_channel_observations_for_session(session: Session, session_id: uuid.UUID) -> None:
    session.execute(
        delete(ManagerOnboardingChannelObservation).where(
            ManagerOnboardingChannelObservation.session_id == session_id,
        ),
    )


def delete_parse_artifacts_for_session(session: Session, session_id: uuid.UUID) -> None:
    session.execute(
        delete(ManagerOnboardingParseArtifact).where(
            ManagerOnboardingParseArtifact.session_id == session_id,
        ),
    )


def _message_transcript_order_key(m: ManagerOnboardingMessage) -> tuple[float, str]:
    """Slack ``ts`` is authoritative; fall back to insert time for legacy rows."""
    raw = (m.slack_ts or "").strip()
    if raw:
        try:
            return (float(raw), str(m.id))
        except ValueError:
            pass
    if m.created_at is not None:
        return (m.created_at.timestamp(), str(m.id))
    return (0.0, str(m.id))


def list_messages_chronological(
    session: Session,
    session_id: uuid.UUID,
    *,
    limit: int = 500,
) -> list[ManagerOnboardingMessage]:
    stmt = select(ManagerOnboardingMessage).where(
        ManagerOnboardingMessage.session_id == session_id,
    )
    rows = list(session.scalars(stmt).all())
    rows.sort(key=_message_transcript_order_key)
    return rows[:limit]


def list_sessions_for_tenant(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    limit: int = 200,
) -> list[ManagerOnboardingSession]:
    stmt = (
        select(ManagerOnboardingSession)
        .where(ManagerOnboardingSession.tenant_id == tenant_id)
        .order_by(ManagerOnboardingSession.updated_at.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt).all())


def list_all_sessions(
    session: Session,
    *,
    limit: int = 200,
) -> list[ManagerOnboardingSession]:
    stmt = (
        select(ManagerOnboardingSession)
        .order_by(ManagerOnboardingSession.updated_at.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt).all())


def list_parse_artifacts_for_session(
    session: Session,
    session_id: uuid.UUID,
    *,
    limit: int = 100,
) -> list[ManagerOnboardingParseArtifact]:
    stmt = (
        select(ManagerOnboardingParseArtifact)
        .where(ManagerOnboardingParseArtifact.session_id == session_id)
        .order_by(ManagerOnboardingParseArtifact.created_at.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt).all())


def list_channel_observations_for_tenant(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    limit: int = 500,
) -> list[ManagerOnboardingChannelObservation]:
    stmt = (
        select(ManagerOnboardingChannelObservation)
        .where(ManagerOnboardingChannelObservation.tenant_id == tenant_id)
        .order_by(ManagerOnboardingChannelObservation.slack_channel_id.asc())
        .limit(limit)
    )
    return list(session.scalars(stmt).all())


def list_channel_observations_for_session(
    session: Session,
    session_id: uuid.UUID,
) -> list[ManagerOnboardingChannelObservation]:
    stmt = (
        select(ManagerOnboardingChannelObservation)
        .where(ManagerOnboardingChannelObservation.session_id == session_id)
        .order_by(ManagerOnboardingChannelObservation.slack_channel_id.asc())
    )
    return list(session.scalars(stmt).all())


def count_invitations_for_tenant(session: Session, tenant_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(ManagerOnboardingInvitation)
        .where(ManagerOnboardingInvitation.tenant_id == tenant_id)
    )
    return int(session.scalar(stmt) or 0)


def upsert_channel_observation(
    session: Session,
    *,
    session_id: uuid.UUID,
    tenant_id: uuid.UUID,
    slack_channel_id: str,
    channel_name: str | None,
    access_status: str,
    bot_is_member: bool,
    history_readable: bool | None,
    validation_error: str | None = None,
) -> ManagerOnboardingChannelObservation:
    cid = slack_channel_id.strip()
    stmt = select(ManagerOnboardingChannelObservation).where(
        ManagerOnboardingChannelObservation.session_id == session_id,
        ManagerOnboardingChannelObservation.slack_channel_id == cid,
    )
    existing = session.scalar(stmt)
    if existing is not None:
        existing.channel_name = channel_name
        existing.access_status = access_status
        existing.bot_is_member = bot_is_member
        existing.history_readable = history_readable
        existing.validation_error = validation_error
        session.flush()
        return existing
    row = ManagerOnboardingChannelObservation(
        session_id=session_id,
        tenant_id=tenant_id,
        slack_channel_id=cid,
        channel_name=channel_name,
        access_status=access_status,
        bot_is_member=bot_is_member,
        history_readable=history_readable,
        validation_error=validation_error,
    )
    session.add(row)
    session.flush()
    return row
