"""Incremental canon scan cursor per tenant scope."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CanonMaterializationCursor(Base):
    __tablename__ = "canon_materialization_cursors"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    scope_key: Mapped[str] = mapped_column(String(64), primary_key=True, default="live")
    last_raw_id: Mapped[int] = mapped_column(BigInteger(), nullable=False, default=0)
    mapper_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
