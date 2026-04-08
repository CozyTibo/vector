"""Transcript row for manager Slack onboarding."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.manager_onboarding_session import ManagerOnboardingSession


class ManagerOnboardingMessage(Base):
    __tablename__ = "manager_onboarding_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("manager_onboarding_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    slack_channel_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    slack_ts: Mapped[str | None] = mapped_column(String(32), nullable=True)
    thread_ts: Mapped[str | None] = mapped_column(String(32), nullable=True)
    slack_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ingestion_kind: Mapped[str] = mapped_column(String(24), nullable=False, default="message")
    outbound_idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    parse_artifact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    session: Mapped[ManagerOnboardingSession] = relationship(
        "ManagerOnboardingSession",
        back_populates="messages",
    )
