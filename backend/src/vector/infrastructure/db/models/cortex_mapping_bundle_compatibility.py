"""Directed compatibility / supersession edges between bundle IDs."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.cortex_mapping_bundle import CortexMappingBundle

class CortexMappingBundleCompatibilityEdge(Base):
    __tablename__ = "cortex_mapping_bundle_compatibility"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    from_bundle_id: Mapped[str] = mapped_column(
        String(256),
        ForeignKey("cortex_mapping_bundles.bundle_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    to_bundle_id: Mapped[str] = mapped_column(
        String(256),
        ForeignKey("cortex_mapping_bundles.bundle_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    edge_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    is_breaking: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text(), nullable=True)
    declared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    from_bundle: Mapped["CortexMappingBundle"] = relationship(
        "CortexMappingBundle",
        foreign_keys=[from_bundle_id],
    )
    to_bundle: Mapped["CortexMappingBundle"] = relationship(
        "CortexMappingBundle",
        foreign_keys=[to_bundle_id],
    )
