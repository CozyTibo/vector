"""Append-only changelog entries per mapping bundle."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.cortex_mapping_bundle import CortexMappingBundle


class CortexMappingBundleChangelogEntry(Base):
    __tablename__ = "cortex_mapping_bundle_changelog"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    bundle_id: Mapped[str] = mapped_column(
        String(256),
        ForeignKey("cortex_mapping_bundles.bundle_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    summary: Mapped[str] = mapped_column(Text(), nullable=False)
    breaking_classification: Mapped[str] = mapped_column(String(32), nullable=False)
    artifact_delta: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    oracle_vector_refs: Mapped[list[Any]] = mapped_column(JSONB(), nullable=False, server_default="[]")
    compatibility_edges_delta: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    invalidation_scope: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    ci_report_refs: Mapped[list[Any]] = mapped_column(JSONB(), nullable=False, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    bundle: Mapped[CortexMappingBundle] = relationship(back_populates="changelog_entries")
