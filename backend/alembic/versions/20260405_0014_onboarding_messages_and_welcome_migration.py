"""Onboarding chat messages + migrate legacy WELCOME to CHAT_PROFILE.

Revision ID: 20260405_0014
Revises: 20260404_0013
Create Date: 2026-04-05

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260405_0014"
down_revision: Union[str, None] = "20260404_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "onboarding_messages",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_onboarding_messages_tenant_id", "onboarding_messages", ["tenant_id"])
    op.create_index("ix_onboarding_messages_user_id", "onboarding_messages", ["user_id"])

    op.execute(
        sa.text(
            "UPDATE onboarding_state SET current_step = 'CHAT_PROFILE' "
            "WHERE current_step IN ('WELCOME', 'COMPANY_INFO', 'TOOL_STACK_DISCOVERY', 'TOOLS_SELECTION')"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_onboarding_messages_user_id", table_name="onboarding_messages")
    op.drop_index("ix_onboarding_messages_tenant_id", table_name="onboarding_messages")
    op.drop_table("onboarding_messages")
