"""Provenance link from canon entity to raw ingestion row."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CanonEntitySource(Base):
    __tablename__ = "canon_entity_sources"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    canon_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("canon_entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    raw_id: Mapped[int] = mapped_column(
        BigInteger(),
        ForeignKey("raw_ingestion_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connector: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str] = mapped_column(String(512), nullable=False)
    source_identity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_revision_key: Mapped[str] = mapped_column(String(128), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_latest: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    mapper_version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
