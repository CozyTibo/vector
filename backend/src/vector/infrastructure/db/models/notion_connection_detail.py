"""Notion OAuth token + workspace metadata (1:1 with TenantConnection)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.tenant_connection import TenantConnection


class NotionConnectionDetail(Base):
    __tablename__ = "notion_connection_details"

    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant_connections.id", ondelete="CASCADE"),
        primary_key=True,
    )
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    token_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    workspace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    workspace_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workspace_icon: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    bot_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    work_container_pins: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    connection: Mapped[TenantConnection] = relationship("TenantConnection")
