"""Phase 03 Step 12 — append-only supersession ledger when a materialization replaces prior projection."""

from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexCanonicalTemporalSupersession(Base):
    __tablename__ = "cortex_canonical_temporal_supersessions"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bundle_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    predecessor_materialization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    predecessor_logical_key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    successor_materialization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_canonical_transform_materializations.id", ondelete="SET NULL"),
        nullable=True,
    )
    causing_raw_record_id: Mapped[int] = mapped_column(
        BigInteger(),
        ForeignKey("raw_ingestion_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    engine_build_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
