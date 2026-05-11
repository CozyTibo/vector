"""Phase 04 Step 19 — tenant-scoped Celery dispatch rows for worker visibility (P04-19)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from vector.infrastructure.db.base import Base


class CortexIdentityCeleryDispatch(Base):
    __tablename__ = "cortex_identity_celery_dispatches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    celery_task_id: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    task_name: Mapped[str] = mapped_column(String(128), nullable=False)
    request_summary_json: Mapped[dict[str, Any]] = mapped_column(JSONB(), nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
