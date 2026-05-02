"""Persisted coordination decision row (§5.1 / §6 Step 30 migration)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Text as SaText, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class ManagerInsightDecision(Base):
    """ORM for ``manager_insight_decisions`` (Alembic ``20260430_0026``)."""

    __tablename__ = "manager_insight_decisions"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_manager_insight_decisions_idempotency_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    gap_id: Mapped[str] = mapped_column(SaText(), nullable=False)
    gap_type: Mapped[str] = mapped_column(SaText(), nullable=False)
    decision_type: Mapped[str] = mapped_column(SaText(), nullable=False)
    title: Mapped[str] = mapped_column(SaText(), nullable=False)
    rationale: Mapped[str] = mapped_column(SaText(), nullable=False, default="")
    default_action: Mapped[dict[str, Any]] = mapped_column(JSONB(astext_type=SaText()), nullable=False)
    required_inputs: Mapped[dict[str, Any]] = mapped_column(JSONB(astext_type=SaText()), nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(ARRAY(SaText()), nullable=False)
    signal_refs: Mapped[list[str]] = mapped_column(ARRAY(SaText()), nullable=False)
    status: Mapped[str] = mapped_column(SaText(), nullable=False, default="proposed")
    rank: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    slack_channel_id: Mapped[str | None] = mapped_column(SaText(), nullable=True)
    slack_message_ts: Mapped[str | None] = mapped_column(SaText(), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(SaText(), nullable=True)
    receipt: Mapped[dict[str, Any] | None] = mapped_column(JSONB(astext_type=SaText()), nullable=True)
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
