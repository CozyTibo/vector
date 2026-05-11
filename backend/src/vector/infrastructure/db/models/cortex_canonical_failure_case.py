"""Phase 03 Step 14 — durable canonical failure / degradation registry."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexCanonicalFailureCase(Base):
    __tablename__ = "cortex_canonical_failure_cases"

    gap_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    failure_class: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    degradation_state: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    detail_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
