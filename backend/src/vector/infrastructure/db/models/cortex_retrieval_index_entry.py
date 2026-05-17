"""Phase 07 — lawful replay-safe retrieval index entry."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexRetrievalIndexEntry(Base):
    __tablename__ = "cortex_retrieval_index_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    retrieval_lookup_id: Mapped[str] = mapped_column(String(128), nullable=False)
    index_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    index_key: Mapped[str] = mapped_column(String(256), nullable=False)
    replay_identity: Mapped[str] = mapped_column(String(128), nullable=False)
    traversal_epoch: Mapped[str | None] = mapped_column(String(128), nullable=True)
    index_epoch: Mapped[str | None] = mapped_column(String(128), nullable=True)
    chronology_legality_class: Mapped[str] = mapped_column(String(64), nullable=False)
    causal_legality_class: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieval_legality_class: Mapped[str] = mapped_column(String(64), nullable=False)
    degradation_posture: Mapped[str] = mapped_column(String(64), nullable=False)
    continuity_posture: Mapped[str] = mapped_column(String(64), nullable=False)
    artifact_ref_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    omission_summary: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    retrieval_policy_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
