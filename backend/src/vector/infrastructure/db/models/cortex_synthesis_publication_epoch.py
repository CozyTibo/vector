"""Phase 08 — per-tenant synthesis publication epoch barrier."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexSynthesisPublicationEpoch(Base):
    __tablename__ = "cortex_synthesis_publication_epochs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    synthesis_publication_epoch: Mapped[str] = mapped_column(String(128), nullable=False)
    published_index_epoch: Mapped[str | None] = mapped_column(String(128), nullable=True)
    artifact_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    substrate_pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
