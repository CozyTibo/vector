"""Phase 03 Step 9 — provider-scoped canonical identity anchor + Phase 04 boundary hooks."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexCanonicalIdentityAnchor(Base):
    """Stable canonical entity id per provider identity tuple under a mapping bundle (replay-stable)."""

    __tablename__ = "cortex_canonical_identity_anchors"

    canonical_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
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
    canonical_object_kind: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    provider_identity_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_identity_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False)
    logical_key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    materialization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_canonical_transform_materializations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_record_id: Mapped[int] = mapped_column(
        BigInteger(),
        ForeignKey("raw_ingestion_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connector: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    phase04_boundary_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
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
