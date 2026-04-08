"""Dedupe Slack event_id retries (Events API)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class ManagerOnboardingSlackEventDedup(Base):
    __tablename__ = "manager_onboarding_slack_event_dedup"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
