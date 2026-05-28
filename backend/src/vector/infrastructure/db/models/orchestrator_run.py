"""Cortex unified orchestrator Beat tick audit."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class OrchestratorRun(Base):
    __tablename__ = "orchestrator_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    beat_interval_seconds: Mapped[int] = mapped_column(Integer(), nullable=False)
    ingestion_enqueued: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    passes_planned: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    passes_processed: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    detail_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(String(512), nullable=True)
