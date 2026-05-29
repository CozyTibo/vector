"""Denormalized rollup stats for a declared domain."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base

EXPANSION_DIRECT = "direct"
EXPANSION_PARTIAL_GRAPH = "partial_graph"
EXPANSION_GRAPH_CURRENT = "graph_current"


class DeclaredDomainStats(Base):
    __tablename__ = "declared_domain_stats"

    declared_domain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("declared_domains.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_counts_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    participant_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    events_7d: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    events_prior_7d: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    activity_delta_7d: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    momentum_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    mass_total: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    expansion_level: Mapped[str] = mapped_column(String(32), nullable=False, default=EXPANSION_DIRECT)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
