"""Cortex identity lane Celery Beat tick audit row."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class IdentitySchedulerTick(Base):
    __tablename__ = "identity_scheduler_ticks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    enqueued_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    candidate_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    beat_interval_seconds: Mapped[int] = mapped_column(Integer(), nullable=False)
    skip_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    enqueued_tenant_ids: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
