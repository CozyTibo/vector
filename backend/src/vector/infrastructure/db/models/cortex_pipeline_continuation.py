"""Durable async-gap continuation state for substrate pipeline orchestration."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexPipelineContinuationState(Base):
    __tablename__ = "cortex_pipeline_continuation_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    substrate_pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_substrate_pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    current_phase: Mapped[str] = mapped_column(String(64), nullable=False)
    waiting_on: Mapped[str | None] = mapped_column(String(64), nullable=True)
    async_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    async_job_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    continuation_status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    continuation_nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    resume_identity_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resume_receipt_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    recovery_required: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default="false")
    failure_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detail_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, server_default="{}"
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
