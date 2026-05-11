"""Phase 04 Step 12 — persisted execution primitive envelope bound to an org entity (P04-12)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexOrgPrimitiveInstance(Base):
    """Phase 3.5 execution primitive envelope materialized under Phase 04 org identity."""

    __tablename__ = "cortex_org_primitive_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_org_entities.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    primitive_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    primitive_key: Mapped[str] = mapped_column(String(64), nullable=False)
    envelope_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False, server_default="active")
    engine_build_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
