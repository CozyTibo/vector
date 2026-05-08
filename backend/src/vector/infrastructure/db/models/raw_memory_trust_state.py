"""Current trust annotation snapshot for Phase 02 Step 8."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class RawMemoryTrustState(Base):
    __tablename__ = "raw_memory_trust_state"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    trust_state: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(8), nullable=False)
    state_reason_codes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    gate_results: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    blocking: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    continuity_gaps: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    verification: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
