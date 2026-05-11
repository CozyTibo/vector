"""Phase 03 Step 10 — orchestrated canonical rebuild / regeneration job."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.cortex_canonical_replay_job_receipt import CortexCanonicalReplayJobReceipt


class CortexCanonicalReplayJob(Base):
    __tablename__ = "cortex_canonical_replay_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pinned_bundle_id: Mapped[str] = mapped_column(String(256), nullable=False)
    job_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    source_bundle_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default="false")
    scope_raw_record_ids: Mapped[list[Any]] = mapped_column(JSONB(), nullable=False)
    resolved_pin_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False)
    engine_build_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, default=dict)
    error_detail: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    receipts: Mapped[list[CortexCanonicalReplayJobReceipt]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
