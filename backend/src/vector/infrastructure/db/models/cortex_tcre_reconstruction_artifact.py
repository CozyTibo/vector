"""Phase 06 RUNTIME-01 — persisted TCRE receipt / edge / chain artifact."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob


class CortexTcreReconstructionArtifact(Base):
    __tablename__ = "cortex_tcre_reconstruction_artifacts"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_tcre_reconstruction_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_key: Mapped[str] = mapped_column(String(256), nullable=False)
    artifact_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    body_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    job: Mapped[CortexTcreReconstructionJob] = relationship(back_populates="artifacts")
