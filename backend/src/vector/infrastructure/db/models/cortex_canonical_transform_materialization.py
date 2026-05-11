"""Phase 03 Step 6 — one deterministic transform run (logical key + emitted snapshot hashes)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.cortex_canonical_field_lineage import CortexCanonicalFieldLineage


class CortexCanonicalTransformMaterialization(Base):
    """Summary row for a bundle-scoped materialization of one raw record."""

    __tablename__ = "cortex_canonical_transform_materializations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "bundle_id",
            "raw_record_id",
            name="uq_cortex_canonical_transform_mat_scope",
        ),
    )

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
    raw_record_id: Mapped[int] = mapped_column(
        BigInteger(),
        ForeignKey("raw_ingestion_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    canonical_object_kind: Mapped[str] = mapped_column(String(128), nullable=False)
    logical_key_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False)
    logical_key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    emitted_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False)
    emitted_snapshot_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    engine_build_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canonical_processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_revision_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    temporal_ordering_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_replay_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_canonical_replay_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    field_lineage: Mapped[list[CortexCanonicalFieldLineage]] = relationship(
        back_populates="materialization",
        cascade="all, delete-orphan",
    )
