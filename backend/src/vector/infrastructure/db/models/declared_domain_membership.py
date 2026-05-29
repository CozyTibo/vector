"""Artifact membership in a declared domain."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base

STATUS_ACTIVE = "active"
STATUS_SUPERSEDED = "superseded"


class DeclaredDomainMembership(Base):
    __tablename__ = "declared_domain_memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    declared_domain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("declared_domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    canon_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canon_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    extractor_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    extractor_rule: Mapped[str] = mapped_column(String(128), nullable=False)
    expansion_level: Mapped[str] = mapped_column(String(16), nullable=False)
    evidence_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    seed_distance: Mapped[int] = mapped_column(SmallInteger(), nullable=False, default=0)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=STATUS_ACTIVE)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
