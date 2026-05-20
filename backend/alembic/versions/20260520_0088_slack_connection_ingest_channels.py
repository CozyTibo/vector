"""Persist admin-selected Slack channels for ingest + join policy.

Revision ID: 20260520_0088
Revises: 20260519_0087
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260520_0088"
down_revision: Union[str, None] = "20260519_0087"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "slack_connection_details",
        sa.Column(
            "ingest_channels_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{\"channels\":[]}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("slack_connection_details", "ingest_channels_json")
