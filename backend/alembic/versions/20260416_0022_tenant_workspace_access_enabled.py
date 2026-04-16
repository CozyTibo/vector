"""Add tenants.workspace_access_enabled (waitlist gate).

Revision ID: 20260416_0022
Revises: 20260412_0021
Create Date: 2026-04-16

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260416_0022"
down_revision: str | None = "20260412_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "workspace_access_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.alter_column(
        "tenants",
        "workspace_access_enabled",
        server_default=sa.text("false"),
    )


def downgrade() -> None:
    op.drop_column("tenants", "workspace_access_enabled")
