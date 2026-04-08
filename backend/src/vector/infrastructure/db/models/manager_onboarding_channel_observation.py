"""Observed Slack channel with access validation status."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.manager_onboarding_session import ManagerOnboardingSession
    from vector.infrastructure.db.models.tenant import Tenant


class ManagerOnboardingChannelObservation(Base):
    __tablename__ = "manager_onboarding_channel_observations"

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
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    slack_channel_id: Mapped[str] = mapped_column(String(32), nullable=False)
    channel_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_status: Mapped[str] = mapped_column(String(32), nullable=False)
    bot_is_member: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    history_readable: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validation_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped[ManagerOnboardingSession] = relationship("ManagerOnboardingSession")
    tenant: Mapped[Tenant] = relationship("Tenant")
