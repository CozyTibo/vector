"""Materialized graph connected-component snapshot (async operator inspect — R4)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexAdminGraphComponentSnapshot(Base):
    __tablename__ = "cortex_admin_graph_component_snapshot"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    captured_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    component_count: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    component_sizes_top_20: Mapped[list[Any]] = mapped_column(
        JSONB(),
        nullable=False,
        server_default="[]",
    )
    job_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="idle")
    error_detail: Mapped[str | None] = mapped_column(Text(), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
