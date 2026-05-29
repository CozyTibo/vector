"""Notion work container pins for declared domain seeds.

Revision ID: 20260529_0107
Revises: 20260529_0106
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260529_0107"
down_revision = "20260529_0106"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notion_connection_details",
        sa.Column(
            "work_container_pins",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("notion_connection_details", "work_container_pins")
