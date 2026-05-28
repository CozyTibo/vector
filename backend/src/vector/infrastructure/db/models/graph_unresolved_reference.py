"""Unresolved reference token from deterministic text extraction."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base

STATUS_UNRESOLVED = "unresolved"
STATUS_RESOLVED = "resolved"
STATUS_IGNORED = "ignored"


class GraphUnresolvedReference(Base):
    __tablename__ = "graph_unresolved_references"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canon_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_raw_id: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    reference_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_text: Mapped[str] = mapped_column(String(512), nullable=False)
    extractor_rule: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=STATUS_UNRESOLVED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
