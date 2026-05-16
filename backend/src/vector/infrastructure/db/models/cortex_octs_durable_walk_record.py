"""Phase 07 — durable OCTS walk record (restart-safe replay identity)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexOctsDurableWalkRecord(Base):
    __tablename__ = "cortex_octs_durable_walk_records"

    walk_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    request_body: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    walk_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB(), nullable=True)
    job_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    walk_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    traversal_receipt_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    traversal_epoch: Mapped[str | None] = mapped_column(String(128), nullable=True)
    replay_identity: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    permutation_profile: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    continuity_proof_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    frontier_boundaries: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    replay_legality_posture: Mapped[str | None] = mapped_column(String(64), nullable=True)
    degradation_classes: Mapped[list[Any]] = mapped_column(JSONB(), nullable=False, server_default="[]")
    parent_walk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cortex_octs_durable_walk_records.walk_id", ondelete="SET NULL"),
        nullable=True,
    )
    engine_build_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
