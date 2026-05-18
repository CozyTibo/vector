"""Phase 08 P08-06 — durable synthesis job row."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
    from vector.infrastructure.db.models.cortex_synthesis_job_receipt import CortexSynthesisJobReceipt


class CortexSynthesisJob(Base):
    __tablename__ = "cortex_synthesis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    envelope_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    envelope_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    synthesis_workload_class: Mapped[str] = mapped_column(String(64), nullable=False)
    synthesis_intent: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_partition: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    synthesis_policy_pack_id: Mapped[str] = mapped_column(String(256), nullable=False)
    synthesis_orchestrator_build_id: Mapped[str] = mapped_column(String(128), nullable=False)
    retrieval_ingress_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    synthesis_job_replay_identity: Mapped[str | None] = mapped_column(String(128), nullable=True)
    synthesis_legality_class: Mapped[str | None] = mapped_column(String(64), nullable=True)
    receipt_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    receipt_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    execution_trace_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB(), nullable=True)
    retrieval_subqueries_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB(),
        nullable=True,
    )
    substrate_pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_substrate_pipeline_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    celery_task_id: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    error_detail: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    receipts: Mapped[list[CortexSynthesisJobReceipt]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
    artifacts: Mapped[list[CortexSynthesisArtifact]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )
