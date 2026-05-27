"""Cortex canon v1 phase 1 — pass runs and materialization cursors.

Revision ID: 20260528_0098
Revises: 20260528_0097
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260528_0098"
down_revision: Union[str, None] = "20260528_0097"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "canon_pass_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_trigger", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_canon_pass_runs_tenant_id", "canon_pass_runs", ["tenant_id"])

    op.create_table(
        "canon_materialization_cursors",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_key", sa.String(length=64), nullable=False),
        sa.Column("last_raw_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("mapper_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tenant_id", "scope_key"),
    )


def downgrade() -> None:
    op.drop_table("canon_materialization_cursors")
    op.drop_index("ix_canon_pass_runs_tenant_id", table_name="canon_pass_runs")
    op.drop_table("canon_pass_runs")
