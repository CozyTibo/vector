"""Durable Cortex substrate pipeline orchestration run (tenant-scoped)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base


class CortexSubstratePipelineRun(Base):
    __tablename__ = "cortex_substrate_pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trigger_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    bundle_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    current_phase_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, server_default="{}"
    )
    error_detail: Mapped[str | None] = mapped_column(Text(), nullable=True)
    celery_root_task_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    phase_runs: Mapped[list["CortexSubstratePhaseRun"]] = relationship(
        back_populates="pipeline_run",
        cascade="all, delete-orphan",
        order_by="CortexSubstratePhaseRun.phase_ordinal",
    )


class CortexSubstratePhaseRun(Base):
    __tablename__ = "cortex_substrate_phase_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_substrate_pipeline_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    phase_id: Mapped[str] = mapped_column(String(64), nullable=False)
    phase_ordinal: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(nullable=False, server_default="0")
    output_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, server_default="{}"
    )
    error_detail: Mapped[str | None] = mapped_column(Text(), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    pipeline_run: Mapped[CortexSubstratePipelineRun] = relationship(back_populates="phase_runs")
