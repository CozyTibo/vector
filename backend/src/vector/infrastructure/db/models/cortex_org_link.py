"""Phase 04 Step 4 — authoritative org-meaning link ledger rows."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexOrgLink(Base):
    """Typed org link between two org entities — not Phase 03 topology."""

    __tablename__ = "cortex_org_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    link_type: Mapped[str] = mapped_column(String(128), nullable=False)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_org_entities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_org_entities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence_raw_record_ids: Mapped[list[Any]] = mapped_column(
        JSONB(),
        nullable=False,
        server_default="[]",
    )
    rule_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    confidence_class: Mapped[str] = mapped_column(String(64), nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersedes_link_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_org_links.id", ondelete="SET NULL"),
        nullable=True,
    )
    promoted_from_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_org_link_candidates.id", ondelete="RESTRICT"),
        nullable=True,
    )
    promotion_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_org_link_promotion_policies.id", ondelete="RESTRICT"),
        nullable=True,
    )
    link_authority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="authoritative",
    )
    link_class: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default="authoritative",
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
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
