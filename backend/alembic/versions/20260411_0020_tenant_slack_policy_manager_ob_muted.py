"""Tenant Slack policy flags + manager onboarding session muted.

Revision ID: 20260411_0020
Revises: 20260410_0019
Create Date: 2026-04-11

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260411_0020"
down_revision: Union[str, None] = "20260410_0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "slack_vector_paused",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "manager_slack_onboarding_disabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "manager_onboarding_sessions",
        sa.Column(
            "muted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("manager_onboarding_sessions", "muted")
    op.drop_column("tenants", "manager_slack_onboarding_disabled")
    op.drop_column("tenants", "slack_vector_paused")
