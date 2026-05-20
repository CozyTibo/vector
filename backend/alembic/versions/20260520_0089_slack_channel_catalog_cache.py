"""Cache Slack channel catalog for admin picker (avoid live pagination every open).

Revision ID: 20260520_0089
Revises: 20260520_0088
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260520_0089"
down_revision: Union[str, None] = "20260520_0088"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "slack_connection_details",
        sa.Column(
            "channel_catalog_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{\"channels\":[]}'::jsonb"),
        ),
    )
    op.add_column(
        "slack_connection_details",
        sa.Column("channel_catalog_fetched_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("slack_connection_details", "channel_catalog_fetched_at")
    op.drop_column("slack_connection_details", "channel_catalog_json")
