"""Phase 03 Step 10 — per-raw divergence receipt for a canonical replay job."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.cortex_canonical_replay_job import CortexCanonicalReplayJob


class CortexCanonicalReplayJobReceipt(Base):
    __tablename__ = "cortex_canonical_replay_job_receipts"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_canonical_replay_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_record_id: Mapped[int] = mapped_column(
        BigInteger(),
        ForeignKey("raw_ingestion_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    divergence_class: Mapped[str] = mapped_column(String(8), nullable=False)
    detail_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False)
    materialize_error: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    job: Mapped[CortexCanonicalReplayJob] = relationship(back_populates="receipts")
