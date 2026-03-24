"""GitHub App installation linked to tenant (connect-only).

Revision ID: 20260327_0004
Revises: 20260326_0003
Create Date:2026-03-27

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260327_0004"
down_revision: Union[str, None] = "20260326_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "github_connections",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("installation_id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("account_login", sa.String(length=255), nullable=False),
        sa.Column("account_type", sa.String(length=32), nullable=False),
        sa.Column("connected_by_user_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["connected_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_github_connections_tenant_id"),
        sa.UniqueConstraint("installation_id", name="uq_github_connections_installation_id"),
    )
    op.create_index(
        "ix_github_connections_tenant_id",
        "github_connections",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_github_connections_installation_id",
        "github_connections",
        ["installation_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_github_connections_installation_id", table_name="github_connections")
    op.drop_index("ix_github_connections_tenant_id", table_name="github_connections")
    op.drop_table("github_connections")
