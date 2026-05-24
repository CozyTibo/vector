"""Materialized admin continuity snapshot (operator overview reader — R1)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexAdminContinuitySnapshot(Base):
    __tablename__ = "cortex_admin_continuity_snapshot"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    captured_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    graph_summary_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(),
        nullable=False,
        server_default="{}",
    )
    retrieval_summary_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(),
        nullable=False,
        server_default="{}",
    )
    synthesis_summary_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(),
        nullable=False,
        server_default="{}",
    )
    identity_summary_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(),
        nullable=False,
        server_default="{}",
    )
    schema_version: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="1")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
