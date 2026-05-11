"""Phase 04 Step 9 — tenant-scoped equivalence between two mapping bundle pins."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexBundleEquivalenceDeclaration(Base):
    """Explicit cross-bundle equivalence (ordered bundle pair per tenant)."""

    __tablename__ = "cortex_bundle_equivalence_declarations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    left_bundle_id: Mapped[str] = mapped_column(
        String(256),
        ForeignKey("cortex_mapping_bundles.bundle_id", ondelete="RESTRICT"),
        nullable=False,
    )
    right_bundle_id: Mapped[str] = mapped_column(
        String(256),
        ForeignKey("cortex_mapping_bundles.bundle_id", ondelete="RESTRICT"),
        nullable=False,
    )
    replay_ordinal: Mapped[int] = mapped_column(Integer(), nullable=False)
    evidence_raw_record_ids: Mapped[list[Any]] = mapped_column(
        JSONB(),
        nullable=False,
        server_default="[]",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    engine_build_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
