"""Phase 08 synthesis scope activation audit (per pipeline run)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexSynthesisActivationAudit(Base):
    __tablename__ = "cortex_synthesis_activation_audits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_substrate_pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scopes_generated: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    scopes_skipped: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    workloads_applied: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    synthesis_jobs_enqueued: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    synthesis_jobs_started: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    synthesis_jobs_completed: Mapped[int] = mapped_column(
        Integer(), nullable=False, server_default="0"
    )
    empty_scope_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    audit_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
