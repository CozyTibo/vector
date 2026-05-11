"""Tenant-scoped bundle pins (`phase-03-bundle-pinning-doctrine.md`)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.cortex_mapping_bundle import CortexMappingBundle
    from vector.infrastructure.db.models.tenant import Tenant


class CortexMappingBundlePin(Base):
    __tablename__ = "cortex_mapping_bundle_pins"

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
    scope_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_marker: Mapped[str] = mapped_column(String(256), nullable=False, server_default="")
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    policy_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    tenant: Mapped[Tenant] = relationship()
    bundle: Mapped[CortexMappingBundle] = relationship(back_populates="pins")
