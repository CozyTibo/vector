"""Manager Slack onboarding session (one row per manager in Slack)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.manager_onboarding_message import ManagerOnboardingMessage
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User


class ManagerOnboardingSession(Base):
    __tablename__ = "manager_onboarding_sessions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "slack_user_id",
            name="uq_manager_ob_sessions_tenant_slack_user",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slack_team_id: Mapped[str] = mapped_column(String(32), nullable=False)
    slack_user_id: Mapped[str] = mapped_column(String(32), nullable=False)
    app_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("manager_onboarding_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_step: Mapped[str] = mapped_column(String(64), nullable=False)
    answers_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timezone_source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    muted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped[Tenant] = relationship("Tenant")
    messages: Mapped[list[ManagerOnboardingMessage]] = relationship(
        "ManagerOnboardingMessage",
        back_populates="session",
        cascade="all, delete-orphan",
    )
