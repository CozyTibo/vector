"""Phase 04 Step 10 — L-class receipt for an org link replay job."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob


class CortexOrgLinkReplayJobReceipt(Base):
    __tablename__ = "cortex_org_link_replay_job_receipts"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_org_link_replay_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    receipt_class: Mapped[str] = mapped_column(String(8), nullable=False)
    detail_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    job: Mapped[CortexOrgLinkReplayJob] = relationship(back_populates="receipts")
