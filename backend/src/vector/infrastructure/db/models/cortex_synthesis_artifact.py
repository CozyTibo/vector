"""Phase 08 P08-14 — durable ``SynthesisIntelligenceArtifactV1`` row."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob


class CortexSynthesisArtifact(Base):
    __tablename__ = "cortex_synthesis_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_synthesis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    synthesis_legality_class: Mapped[str] = mapped_column(String(64), nullable=False)
    published: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default="false")
    synthesis_publication_epoch: Mapped[str | None] = mapped_column(String(128), nullable=True)
    retrieval_lookup_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    retrieval_query_replay_identity: Mapped[str | None] = mapped_column(String(128), nullable=True)
    body_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    job: Mapped[CortexSynthesisJob] = relationship(back_populates="artifacts")
