"""Phase 08.5 — per-tenant replay storm control state (**G-P085-ECON-02**)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexReplayStormControl(Base):
    __tablename__ = "cortex_replay_storm_controls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    storm_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default="false")
    exploration_partition_paused: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default="false"
    )
    pinned_retrieval_policy_digest: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    pinned_synthesis_policy_pack_digest: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    pinned_tcre_policy_bundle_digest: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    operator_acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    operator_acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    storm_detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    detail_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(), nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
