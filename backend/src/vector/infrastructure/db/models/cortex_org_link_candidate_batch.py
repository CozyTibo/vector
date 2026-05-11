"""Phase 04 Step 5 — one deterministic candidate regeneration batch."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexOrgLinkCandidateBatch(Base):
    __tablename__ = "cortex_org_link_candidate_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_version: Mapped[str] = mapped_column(String(128), nullable=False)
    link_rule_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_link_rule_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    candidate_set_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    engine_build_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
