"""Phase 04 Step 20 — audit row for canonical-anchor → org-entity backfill (P04-20)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexOrgIdentityBackfillRun(Base):
    __tablename__ = "cortex_org_identity_backfill_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dry_run: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default="false")
    anchors_scanned: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    entities_upserted: Mapped[int] = mapped_column(Integer(), nullable=False, server_default="0")
    backfill_set_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    engine_build_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
