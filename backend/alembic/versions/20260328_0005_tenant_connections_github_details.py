"""Spine tenant_connections + github_connection_details; drop github_connections.

Revision ID: 20260328_0005
Revises: 20260327_0004
Create Date: 2026-03-28

"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260328_0005"
down_revision: Union[str, None] = "20260327_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant_connections",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("connected_by_user_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
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
        sa.UniqueConstraint(
            "tenant_id",
            "provider",
            name="uq_tenant_connections_tenant_provider",
        ),
    )
    op.create_index(
        "ix_tenant_connections_tenant_id",
        "tenant_connections",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_tenant_connections_provider",
        "tenant_connections",
        ["provider"],
        unique=False,
    )
    op.create_index(
        "ix_tenant_connections_connected_by_user_id",
        "tenant_connections",
        ["connected_by_user_id"],
        unique=False,
    )

    op.create_table(
        "github_connection_details",
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("installation_id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("account_login", sa.String(length=255), nullable=False),
        sa.Column("account_type", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["tenant_connections.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("connection_id"),
        sa.UniqueConstraint(
            "installation_id",
            name="uq_github_connection_details_installation_id",
        ),
    )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            """
            SELECT tenant_id, installation_id, account_id, account_login, account_type,
                   connected_by_user_id, created_at, updated_at
            FROM github_connections
            """
        ),
    ).mappings().all()

    for r in rows:
        new_id = uuid.uuid4()
        conn.execute(
            sa.text(
                """
                INSERT INTO tenant_connections (
                    id, tenant_id, provider, status, connected_by_user_id, display_name,
                    created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, 'github', 'active', :connected_by_user_id, NULL,
                    :created_at, :updated_at
                )
                """
            ),
            {
                "id": new_id,
                "tenant_id": r["tenant_id"],
                "connected_by_user_id": r["connected_by_user_id"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            },
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO github_connection_details (
                    connection_id, installation_id, account_id, account_login, account_type
                ) VALUES (
                    :connection_id, :installation_id, :account_id, :account_login, :account_type
                )
                """
            ),
            {
                "connection_id": new_id,
                "installation_id": r["installation_id"],
                "account_id": r["account_id"],
                "account_login": r["account_login"],
                "account_type": r["account_type"],
            },
        )

    op.drop_index("ix_github_connections_installation_id", table_name="github_connections")
    op.drop_index("ix_github_connections_tenant_id", table_name="github_connections")
    op.drop_table("github_connections")


def downgrade() -> None:
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

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            """
            SELECT tc.id, tc.tenant_id, gd.installation_id, gd.account_id, gd.account_login,
                   gd.account_type, tc.connected_by_user_id, tc.created_at, tc.updated_at
            FROM tenant_connections tc
            JOIN github_connection_details gd ON gd.connection_id = tc.id
            WHERE tc.provider = 'github'
            """
        ),
    ).mappings().all()

    for r in rows:
        conn.execute(
            sa.text(
                """
                INSERT INTO github_connections (
                    id, tenant_id, installation_id, account_id, account_login, account_type,
                    connected_by_user_id, created_at, updated_at
                ) VALUES (
                    :id, :tenant_id, :installation_id, :account_id, :account_login, :account_type,
                    :connected_by_user_id, :created_at, :updated_at
                )
                """
            ),
            dict(r),
        )

    op.drop_table("github_connection_details")
    op.drop_index(
        "ix_tenant_connections_connected_by_user_id",
        table_name="tenant_connections",
    )
    op.drop_index("ix_tenant_connections_provider", table_name="tenant_connections")
    op.drop_index("ix_tenant_connections_tenant_id", table_name="tenant_connections")
    op.drop_table("tenant_connections")
