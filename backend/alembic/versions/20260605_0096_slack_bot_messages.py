"""Slack bot DM conversation layer: user-tenant map + message log.

Revision ID: 20260605_0096
Revises: 20260529_0107
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260605_0096"
down_revision: Union[str, None] = "20260529_0107"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "slack_user_tenant_map",
        sa.Column("slack_team_id", sa.String(length=32), nullable=False),
        sa.Column("slack_user_id", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("slack_team_id", "slack_user_id"),
    )

    op.create_table(
        "slack_bot_messages",
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("slack_team_id", sa.String(length=32), nullable=False),
        sa.Column("slack_user_id", sa.String(length=32), nullable=False),
        sa.Column("slack_channel_id", sa.String(length=32), nullable=False),
        sa.Column("slack_ts", sa.String(length=32), nullable=False),
        sa.Column("thread_ts", sa.String(length=32), nullable=True),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("slack_event_id", sa.String(length=64), nullable=True),
        sa.Column("outbound_idempotency_key", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "direction IN ('outbound', 'inbound')",
            name="ck_slack_bot_messages_direction",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slack_event_id", name="uq_slack_bot_messages_slack_event_id"),
        sa.UniqueConstraint(
            "outbound_idempotency_key",
            name="uq_slack_bot_messages_outbound_idempotency_key",
        ),
    )
    op.create_index(
        "ix_slack_bot_messages_tenant_slack_user",
        "slack_bot_messages",
        ["tenant_id", "slack_user_id"],
    )
    op.create_index(
        "ix_slack_bot_messages_slack_ts",
        "slack_bot_messages",
        ["slack_ts"],
    )


def downgrade() -> None:
    op.drop_index("ix_slack_bot_messages_slack_ts", table_name="slack_bot_messages")
    op.drop_index("ix_slack_bot_messages_tenant_slack_user", table_name="slack_bot_messages")
    op.drop_table("slack_bot_messages")
    op.drop_table("slack_user_tenant_map")
