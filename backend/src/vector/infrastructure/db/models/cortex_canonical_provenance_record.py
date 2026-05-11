"""Phase 03 Step 11 — durable provenance envelope + forward raw→canonical index (`phase-03-provenance-traceability-doctrine.md`)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
        CortexCanonicalTransformMaterialization,
    )


class CortexCanonicalProvenanceRecord(Base):
    """One row per transform materialization: primary evidence multiset + derivation metadata."""

    __tablename__ = "cortex_canonical_provenance_records"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    materialization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_canonical_transform_materializations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bundle_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    raw_record_id: Mapped[int] = mapped_column(
        BigInteger(),
        ForeignKey("raw_ingestion_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    canonical_object_kind: Mapped[str] = mapped_column(String(128), nullable=False)
    logical_key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_shape: Mapped[str] = mapped_column(String(32), nullable=False, server_default="1:1")
    primary_raw_record_ids: Mapped[list[Any]] = mapped_column(JSONB(), nullable=False)
    rule_ids_involved: Mapped[list[Any]] = mapped_column(JSONB(), nullable=False)
    derivation_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False)
    parent_materialization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_canonical_transform_materializations.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    materialization: Mapped[CortexCanonicalTransformMaterialization] = relationship(
        foreign_keys=[materialization_id],
    )
