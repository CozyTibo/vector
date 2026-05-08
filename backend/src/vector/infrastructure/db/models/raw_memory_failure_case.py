"""Failure case representation for Phase 02 Step 7."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class RawMemoryFailureCase(Base):
    __tablename__ = "raw_memory_failure_cases"

    gap_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    failure_class: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    gap_type: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_connector: Mapped[str | None] = mapped_column(String(32), nullable=True)
    scope_resource_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scope_source_identity_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    window_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    window_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_state_impact: Mapped[str] = mapped_column(String(64), nullable=False)
    recoverability_class: Mapped[str] = mapped_column(String(64), nullable=False)
    recovery_status: Mapped[str] = mapped_column(String(64), nullable=False, default="pending")
    last_validation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
