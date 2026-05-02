"""Persisted coordination outcome row (§5.2 / §6 Step 39)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, Text as SaText, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class ManagerInsightOutcome(Base):
    """ORM for ``manager_insight_outcomes``."""

    __tablename__ = "manager_insight_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("manager_insight_decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    outcome_type: Mapped[str] = mapped_column(SaText(), nullable=False)
    false_positive: Mapped[bool | None] = mapped_column(Boolean(), nullable=True)
    ground_truth: Mapped[dict[str, Any]] = mapped_column(
        JSONB(astext_type=SaText()),
        nullable=False,
        server_default=sa.text("'{}'::jsonb"),
    )
    user_attribution: Mapped[str | None] = mapped_column(SaText(), nullable=True)
