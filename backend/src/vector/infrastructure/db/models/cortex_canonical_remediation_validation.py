"""Phase 03 Step 14 — auditable remediation validation ledger."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexCanonicalRemediationValidation(Base):
    __tablename__ = "cortex_canonical_remediation_validations"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    failure_case_gap_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("cortex_canonical_failure_cases.gap_id", ondelete="SET NULL"),
        nullable=True,
    )
    remediation_class: Mapped[str] = mapped_column(String(64), nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    confirm_execution: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    result_status: Mapped[str] = mapped_column(String(32), nullable=False)
    result_detail_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
