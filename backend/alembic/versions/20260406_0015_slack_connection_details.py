"""Slack OAuth connection details (1:1 with tenant_connections).

Revision ID: 20260406_0015
Revises: 20260405_0014
Create Date: 2026-04-06

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260406_0015"
down_revision: Union[str, None] = "20260405_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "slack_connection_details",
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("bot_access_token", sa.Text(), nullable=False),
        sa.Column("team_id", sa.String(length=32), nullable=False),
        sa.Column("team_name", sa.String(length=255), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["tenant_connections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("connection_id"),
    )


def downgrade() -> None:
    op.drop_table("slack_connection_details")
