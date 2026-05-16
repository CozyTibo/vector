"""Phase 06 RUNTIME-01 — durable TCRE reconstruction / replay job row."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.cortex_tcre_reconstruction_artifact import (
        CortexTcreReconstructionArtifact,
    )


class CortexTcreReconstructionJob(Base):
    __tablename__ = "cortex_tcre_reconstruction_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default="false")
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    tcre_policy_bundle_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    reasoning_rule_pack_id: Mapped[str] = mapped_column(String(256), nullable=False)
    parent_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_tcre_reconstruction_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    error_detail: Mapped[str | None] = mapped_column(Text(), nullable=True)
    engine_build_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)

    artifacts: Mapped[list[CortexTcreReconstructionArtifact]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
