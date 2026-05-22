"""P2-C — persisted execution island registry per tenant."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexExecutionIslandRegistry(Base):
    __tablename__ = "cortex_execution_island_registry"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "island_scope_id",
            name="uq_cortex_execution_island_registry_tenant_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    island_scope_id: Mapped[str] = mapped_column(String(16), nullable=False)
    entity_count: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    authoritative_edge_count: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    entity_ids: Mapped[list[Any]] = mapped_column(JSONB(), nullable=False, server_default="[]")
    last_walk_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_retrieval_epoch: Mapped[str | None] = mapped_column(String(128), nullable=True)
    registry_snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    detail_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
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
