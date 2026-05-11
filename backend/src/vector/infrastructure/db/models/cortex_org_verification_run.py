"""Phase 04 Step 15 — persisted Phase 04 gate slice from canonical verification (P04-15)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexOrgVerificationRun(Base):
    """Tenant-scoped Phase 04 verification slice (G-P04-* gates only)."""

    __tablename__ = "cortex_org_verification_runs"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    engine_schema_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    gates_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
