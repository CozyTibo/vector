"""Recoverable dead-letter records for blocked substrate pipeline async gaps."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexSubstratePipelineDeadLetter(Base):
    __tablename__ = "cortex_substrate_pipeline_dead_letters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_substrate_pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase_id: Mapped[str] = mapped_column(String(64), nullable=False)
    async_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    failure_class: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    replay_safe: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default="true")
    recovery_actions: Mapped[list[Any]] = mapped_column(
        JSONB(),
        nullable=False,
        server_default="[]",
    )
    resume_receipt_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    auto_retry_count: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    dlq_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="open", index=True)
    failure_detail: Mapped[str | None] = mapped_column(Text(), nullable=True)
    detail_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(),
        nullable=False,
        server_default="{}",
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
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
