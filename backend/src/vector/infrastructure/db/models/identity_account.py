"""Links one canon actor entity to one resolved identity."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class IdentityAccount(Base):
    __tablename__ = "identity_accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "canon_entity_id", name="uq_identity_accounts_tenant_canon_entity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    identity_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("identity_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    canon_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canon_entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connector: Mapped[str] = mapped_column(String(32), nullable=False)
    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant_connections.id", ondelete="CASCADE"),
        nullable=False,
    )
    link_tier: Mapped[str] = mapped_column(String(16), nullable=False, default="seed")
    link_rule: Mapped[str] = mapped_column(String(64), nullable=False, default="seed_actor")
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="low")
    evidence_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    unlinked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

