"""Declared domain projection row (one per declared work container seed)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class DeclaredDomain(Base):
    __tablename__ = "declared_domains"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    declared_container_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    seed_canon_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canon_entities.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    seed_connector: Mapped[str] = mapped_column(String(32), nullable=False)
    seed_resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    extractor_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
