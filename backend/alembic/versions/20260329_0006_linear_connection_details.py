"""Linear OAuth connection details (1:1 with tenant_connections).

Revision ID: 20260329_0006
Revises: 20260328_0005
Create Date: 2026-03-29

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260329_0006"
down_revision: Union[str, None] = "20260328_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "linear_connection_details",
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column(
            "token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("linear_organization_id", sa.String(length=64), nullable=True),
        sa.Column("linear_organization_name", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["tenant_connections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("connection_id"),
    )


def downgrade() -> None:
    op.drop_table("linear_connection_details")
