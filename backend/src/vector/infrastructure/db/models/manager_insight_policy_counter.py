"""Sliding-window policy counters for coordination learning (§5.3 / §6 Step 39)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text as SaText
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class ManagerInsightPolicyCounter(Base):
    """ORM for ``manager_insight_policy_counters`` (composite PK)."""

    __tablename__ = "manager_insight_policy_counters"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    dimension: Mapped[str] = mapped_column(SaText(), primary_key=True, nullable=False)
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        nullable=False,
    )
    false_positive_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    suppress_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
