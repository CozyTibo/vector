"""canon_scheduler_ticks and identity_scheduler_ticks — Beat tick audit per lane.

Revision ID: 20260528_0101
Revises: 20260528_0100
Create Date: 2026-05-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260528_0101"
down_revision = "20260528_0100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "canon_scheduler_ticks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("enqueued_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("beat_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("skip_reason", sa.String(length=128), nullable=True),
        sa.Column("enqueued_tenant_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_canon_scheduler_ticks_started_at",
        "canon_scheduler_ticks",
        ["started_at"],
    )
    op.create_table(
        "identity_scheduler_ticks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("enqueued_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("beat_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("skip_reason", sa.String(length=128), nullable=True),
        sa.Column("enqueued_tenant_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_identity_scheduler_ticks_started_at",
        "identity_scheduler_ticks",
        ["started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_identity_scheduler_ticks_started_at", table_name="identity_scheduler_ticks")
    op.drop_table("identity_scheduler_ticks")
    op.drop_index("ix_canon_scheduler_ticks_started_at", table_name="canon_scheduler_ticks")
    op.drop_table("canon_scheduler_ticks")
