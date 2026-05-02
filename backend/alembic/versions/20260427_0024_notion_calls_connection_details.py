"""Add Notion and Calls connection detail tables.

Revision ID: 20260427_0024
Revises: 20260422_0023
Create Date: 2026-04-27
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "20260427_0024"
down_revision: Union[str, None] = "20260422_0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table("notion_connection_details"):
        op.create_table(
            "notion_connection_details",
            sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("access_token", sa.Text(), nullable=False),
            sa.Column("token_type", sa.String(length=32), nullable=True),
            sa.Column("workspace_id", sa.String(length=128), nullable=True),
            sa.Column("workspace_name", sa.String(length=255), nullable=True),
            sa.Column("workspace_icon", sa.Text(), nullable=True),
            sa.Column("owner_user_id", sa.String(length=128), nullable=True),
            sa.Column("bot_id", sa.String(length=128), nullable=True),
            sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["connection_id"], ["tenant_connections.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("connection_id"),
        )
    if not insp.has_table("calls_connection_details"):
        op.create_table(
            "calls_connection_details",
            sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("access_token", sa.Text(), nullable=False),
            sa.Column("refresh_token", sa.Text(), nullable=True),
            sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("provider_user_id", sa.String(length=255), nullable=True),
            sa.Column("provider_email", sa.String(length=320), nullable=True),
            sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["connection_id"], ["tenant_connections.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("connection_id"),
        )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS calls_connection_details"))
    op.execute(sa.text("DROP TABLE IF EXISTS notion_connection_details"))
