"""Durable provenance/lineage index for Phase 02 raw memory."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class RawMemoryLineageIndex(Base):
    __tablename__ = "raw_memory_lineage_index"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        primary_key=True,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    connector: Mapped[str] = mapped_column(String(32), primary_key=True)
    resource_type: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_identity_key: Mapped[str] = mapped_column(String(255), primary_key=True)

    provenance_chain_id: Mapped[str] = mapped_column(String(512), nullable=False)

    first_seen_raw_id: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    latest_seen_raw_id: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latest_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    latest_source_revision_key: Mapped[str] = mapped_column(String(128), nullable=False)
    latest_payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    latest_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    latest_replay_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    latest_replay_version: Mapped[int | None] = mapped_column(Integer(), nullable=True)
