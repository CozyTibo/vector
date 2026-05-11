"""Phase 04 Step 14 — org-scoped multiplicity / unresolved-actor ambiguity receipts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexOrgAmbiguityRecord(Base):
    """Org-level ambiguity — not Phase 03 canonical mapping ambiguity."""

    __tablename__ = "cortex_org_ambiguity_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_ambiguity_class: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_key: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    involved_org_entity_ids: Mapped[list[Any]] = mapped_column(JSONB(), nullable=False, server_default="[]")
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    superseded_by_org_ambiguity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_org_ambiguity_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    operator_note: Mapped[str | None] = mapped_column(Text(), nullable=True)
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
