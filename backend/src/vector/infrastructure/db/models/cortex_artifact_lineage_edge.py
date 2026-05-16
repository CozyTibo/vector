"""Phase 07 — deterministic artifact lineage edge."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexArtifactLineageEdge(Base):
    __tablename__ = "cortex_artifact_lineage_edges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lineage_edge_id: Mapped[str] = mapped_column(String(128), nullable=False)
    from_artifact_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    from_artifact_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    to_artifact_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    to_artifact_ref: Mapped[str] = mapped_column(String(256), nullable=False)
    edge_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    replay_identity: Mapped[str | None] = mapped_column(String(128), nullable=True)
    degradation_propagation: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, server_default="{}"
    )
    omission_summary: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
