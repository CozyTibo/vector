"""Structured retrieval index materialization diagnostics (per pipeline run)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexRetrievalMaterializationReport(Base):
    __tablename__ = "cortex_retrieval_materialization_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_substrate_pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    retrieval_epoch: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tcre_candidates: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    walks_candidates: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    org_link_candidates: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    accepted_rows: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    rejected_rows: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    skipped_rows: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    skip_reasons_json: Mapped[list[Any]] = mapped_column(
        JSONB(), nullable=False, server_default="[]"
    )
    report_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
