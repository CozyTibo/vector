"""Phase 08 P08-06 — append-only synthesis job receipt / execution trace."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob


class CortexSynthesisJobReceipt(Base):
    __tablename__ = "cortex_synthesis_job_receipts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_synthesis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receipt_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    receipt_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    execution_trace_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB(),
        nullable=False,
        server_default="[]",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    job: Mapped[CortexSynthesisJob] = relationship(back_populates="receipts")
