"""cortex_passes — DB-authoritative pass work queue.

Revision ID: 20260528_0102
Revises: 20260528_0101
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260528_0102"
down_revision = "20260528_0101"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cortex_passes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pass_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=256), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("source_trigger", sa.String(length=64), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("stats_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cortex_passes_tenant_id", "cortex_passes", ["tenant_id"])
    op.create_index("ix_cortex_passes_pass_type", "cortex_passes", ["pass_type"])
    op.create_index("ix_cortex_passes_status", "cortex_passes", ["status"])
    op.create_index("ix_cortex_passes_scheduled_at", "cortex_passes", ["scheduled_at"])
    op.create_index(
        "ix_cortex_passes_status_scheduled",
        "cortex_passes",
        ["status", "scheduled_at"],
    )
    op.execute(
        """
        CREATE UNIQUE INDEX ux_cortex_passes_tenant_type_active
        ON cortex_passes (tenant_id, pass_type)
        WHERE status IN ('pending', 'running')
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_cortex_passes_tenant_type_active")
    op.drop_index("ix_cortex_passes_status_scheduled", table_name="cortex_passes")
    op.drop_index("ix_cortex_passes_scheduled_at", table_name="cortex_passes")
    op.drop_index("ix_cortex_passes_status", table_name="cortex_passes")
    op.drop_index("ix_cortex_passes_pass_type", table_name="cortex_passes")
    op.drop_index("ix_cortex_passes_tenant_id", table_name="cortex_passes")
    op.drop_table("cortex_passes")
