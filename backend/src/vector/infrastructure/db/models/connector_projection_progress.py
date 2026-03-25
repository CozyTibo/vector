"""Projection worker cursor + lease (per connection + connector)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class ConnectorProjectionProgress(Base):
    __tablename__ = "connector_projection_progress"

    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    connector: Mapped[str] = mapped_column(String(32), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    last_replay_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    lock_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    lock_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
