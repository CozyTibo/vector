"""Phase 03 Step 5 — mapping bundle registry records (`phase-03-mapping-bundle-registry.md`)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.cortex_mapping_bundle_changelog import CortexMappingBundleChangelogEntry
    from vector.infrastructure.db.models.cortex_mapping_bundle_pin import CortexMappingBundlePin


class CortexMappingBundle(Base):
    """Immutable bundle identity row (artifacts addressed by manifest hash)."""

    __tablename__ = "cortex_mapping_bundles"

    bundle_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    lifecycle_state: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    manifest_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_team: Mapped[str] = mapped_column(String(256), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    predecessor_bundle_id: Mapped[str | None] = mapped_column(
        String(256),
        ForeignKey("cortex_mapping_bundles.bundle_id", ondelete="SET NULL"),
        nullable=True,
    )
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

    changelog_entries: Mapped[list[CortexMappingBundleChangelogEntry]] = relationship(
        back_populates="bundle",
        cascade="all, delete-orphan",
    )
    pins: Mapped[list[CortexMappingBundlePin]] = relationship(back_populates="bundle")
