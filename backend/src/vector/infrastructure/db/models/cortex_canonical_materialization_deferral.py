"""Durable deferral state for topology-blocked canonical materialization."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexCanonicalMaterializationDeferral(Base):
    __tablename__ = "cortex_canonical_materialization_deferrals"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    bundle_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    raw_record_id: Mapped[int] = mapped_column(BigInteger(), primary_key=True)
    connector: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(128), nullable=False)
    deferral_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    queue: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_raw_record_id: Mapped[int | None] = mapped_column(BigInteger(), nullable=True)
    missing_parent_ref: Mapped[str | None] = mapped_column(Text(), nullable=True)
    pass_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    retry_ready_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deferred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detail_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, server_default="{}"
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
