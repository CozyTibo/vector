"""Remove manager_slack_onboarding_disabled tenant flag.

Revision ID: 20260412_0021
Revises: 20260411_0020
Create Date: 2026-04-12

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260412_0021"
down_revision: Union[str, None] = "20260411_0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("tenants", "manager_slack_onboarding_disabled")


def downgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "manager_slack_onboarding_disabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
