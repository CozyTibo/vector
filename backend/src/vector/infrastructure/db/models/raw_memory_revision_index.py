"""Temporal revision index for Phase 02 Step 3 continuity semantics."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class RawMemoryRevisionIndex(Base):
    __tablename__ = "raw_memory_revision_index"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    connector: Mapped[str] = mapped_column(String(32), primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_identity_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    source_revision_key: Mapped[str] = mapped_column(String(128), primary_key=True)

    raw_id: Mapped[int] = mapped_column(BigInteger(), nullable=False, unique=True)
    provider_event_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_source_revision_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_deleted_observed: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    replay_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    replay_version: Mapped[int | None] = mapped_column(Integer(), nullable=True)
