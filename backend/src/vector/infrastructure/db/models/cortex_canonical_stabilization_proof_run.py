"""Phase 03 Step 17 — persisted stabilization / economics proof snapshots."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexCanonicalStabilizationProofRun(Base):
    __tablename__ = "cortex_canonical_stabilization_proof_runs"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proof_schema_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    probes_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
