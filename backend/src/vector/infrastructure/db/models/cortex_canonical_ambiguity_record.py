"""Phase 03 Step 7 — durable ambiguity records (unresolved / contested canonicalization)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

class CortexCanonicalAmbiguityRecord(Base):
    """One ambiguity receipt; lifecycle transitions update status (no row deletion)."""

    __tablename__ = "cortex_canonical_ambiguity_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bundle_id: Mapped[str] = mapped_column(
        String(256),
        ForeignKey("cortex_mapping_bundles.bundle_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ambiguity_class: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(512), nullable=False)
    record_handle: Mapped[str | None] = mapped_column(String(256), nullable=True)
    raw_record_ids: Mapped[list[Any]] = mapped_column(JSONB(), nullable=False)
    rule_ids_involved: Mapped[list[Any]] = mapped_column(JSONB(), nullable=False, server_default="[]")
    primary_connector: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    primary_resource_type: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersession_note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    superseded_by_ambiguity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_canonical_ambiguity_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    evidence_payload: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    engine_build_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    lifecycle_events: Mapped[list["CortexCanonicalAmbiguityLifecycleEvent"]] = relationship(
        back_populates="ambiguity_record",
        cascade="all, delete-orphan",
    )
