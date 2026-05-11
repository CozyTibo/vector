"""Append-only raw fetch rows for Cortex ingestion (replay-ordered)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class RawIngestionRecord(Base):
    __tablename__ = "raw_ingestion_records"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    replay_sequence: Mapped[int] = mapped_column(
        BigInteger(),
        nullable=False,
        server_default=text("nextval('raw_ingestion_replay_seq')"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    connector: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)
    api_endpoint: Mapped[str] = mapped_column(String(512), nullable=False)
    query_params: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_body: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    http_status: Mapped[int] = mapped_column(Integer(), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingestion_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    replay_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    replay_version: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    source_trigger: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source_identity_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_revision_key: Mapped[str] = mapped_column(String(128), nullable=False)
