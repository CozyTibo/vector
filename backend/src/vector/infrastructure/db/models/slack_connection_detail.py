"""Slack OAuth bot token + workspace metadata (1:1 with TenantConnection)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vector.infrastructure.db.base import Base

if TYPE_CHECKING:
    from vector.infrastructure.db.models.tenant_connection import TenantConnection


class SlackConnectionDetail(Base):
    __tablename__ = "slack_connection_details"

    connection_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenant_connections.id", ondelete="CASCADE"),
        primary_key=True,
    )
    bot_access_token: Mapped[str] = mapped_column(Text, nullable=False)
    team_id: Mapped[str] = mapped_column(String(32), nullable=False)
    team_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingest_channels_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB(),
        nullable=False,
        server_default='{"channels":[]}',
    )

    connection: Mapped[TenantConnection] = relationship("TenantConnection")
