"""Projected execution relationship between canon entities."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base

STATUS_ACTIVE = "active"
STATUS_SUPERSEDED = "superseded"


class GraphRelationship(Base):
    __tablename__ = "graph_relationships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    from_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canon_entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canon_entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_identity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity_entities.id", ondelete="SET NULL"),
        nullable=True,
    )
    to_identity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity_entities.id", ondelete="SET NULL"),
        nullable=True,
    )
    identity_resolver_version_at_enrich: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default="directed")
    confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    extractor_version: Mapped[int] = mapped_column(Integer(), nullable=False)
    extractor_rule: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    evidence_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    source_raw_id: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    source_canon_source_id: Mapped[int | None] = mapped_column(
        BigInteger(),
        ForeignKey("canon_entity_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_relationships.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
