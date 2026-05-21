"""Durable tenant execution ownership per tenant (Postgres-authoritative; M5 FSM)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexTenantConvergenceLease(Base):
    """Per-tenant execution lease row (table name retained for migration compatibility)."""

    __tablename__ = "cortex_tenant_convergence_leases"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="idle")
    obligation_epoch: Mapped[int] = mapped_column(BigInteger(), nullable=False, server_default="0")
    target_epoch: Mapped[int] = mapped_column(BigInteger(), nullable=False, server_default="0")
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_substrate_pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    phase_cursor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fsm_state: Mapped[str] = mapped_column(String(64), nullable=False, server_default="IDLE")
    block_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    block_detail: Mapped[str | None] = mapped_column(Text(), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text(), nullable=True)
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


# M5 alias — plan target name; ORM maps to cortex_tenant_convergence_leases until table rename.
CortexTenantExecution = CortexTenantConvergenceLease
