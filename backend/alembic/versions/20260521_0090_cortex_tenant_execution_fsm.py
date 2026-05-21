"""Tenant execution FSM columns + append-only transition log (M5).

Revision ID: 20260521_0090
Revises: 20260520_0089
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260521_0090"
down_revision: Union[str, None] = "20260520_0089"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cortex_tenant_convergence_leases",
        sa.Column("fsm_state", sa.String(length=64), nullable=False, server_default="IDLE"),
    )
    op.add_column(
        "cortex_tenant_convergence_leases",
        sa.Column("block_reason_code", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "cortex_tenant_convergence_leases",
        sa.Column("block_detail", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_cortex_tenant_convergence_leases_fsm_state",
        "cortex_tenant_convergence_leases",
        ["fsm_state"],
    )

    op.create_table(
        "cortex_execution_transition_log",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "pipeline_run_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("cortex_substrate_pipeline_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("from_state", sa.String(length=64), nullable=False),
        sa.Column("to_state", sa.String(length=64), nullable=False),
        sa.Column("trigger", sa.String(length=128), nullable=False),
        sa.Column("gate_result", sa.String(length=32), nullable=True),
        sa.Column("receipt_hash", sa.String(length=128), nullable=True),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_cortex_execution_transition_log_tenant_created",
        "cortex_execution_transition_log",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cortex_execution_transition_log_tenant_created",
        table_name="cortex_execution_transition_log",
    )
    op.drop_table("cortex_execution_transition_log")
    op.drop_index(
        "ix_cortex_tenant_convergence_leases_fsm_state",
        table_name="cortex_tenant_convergence_leases",
    )
    op.drop_column("cortex_tenant_convergence_leases", "block_detail")
    op.drop_column("cortex_tenant_convergence_leases", "block_reason_code")
    op.drop_column("cortex_tenant_convergence_leases", "fsm_state")
