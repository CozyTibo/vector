"""Durable tenant convergence lease — authoritative substrate progression ownership.

Revision ID: 20260519_0086
Revises: 20260518_0085
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260519_0086"
down_revision: Union[str, None] = "20260518_0085"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_tenant_convergence_leases",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="idle"),
        sa.Column("obligation_epoch", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("target_epoch", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "pipeline_run_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("cortex_substrate_pipeline_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("phase_cursor", sa.String(length=64), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "detail_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_cortex_tenant_convergence_leases_status_next_attempt",
        "cortex_tenant_convergence_leases",
        ["status", "next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cortex_tenant_convergence_leases_status_next_attempt",
        table_name="cortex_tenant_convergence_leases",
    )
    op.drop_table("cortex_tenant_convergence_leases")
