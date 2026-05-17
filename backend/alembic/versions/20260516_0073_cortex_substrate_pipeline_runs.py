"""Cortex substrate pipeline orchestration — durable phase runs.

Revision ID: 20260516_0073
Revises: 20260516_0072
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260516_0073"
down_revision: Union[str, None] = "20260516_0072"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_substrate_pipeline_runs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger_kind", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("bundle_id", sa.String(length=256), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("current_phase_id", sa.String(length=64), nullable=True),
        sa.Column(
            "summary_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("celery_root_task_id", sa.String(length=256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_cortex_substrate_pipeline_runs_tenant_id",
        "cortex_substrate_pipeline_runs",
        ["tenant_id"],
    )
    op.create_index(
        "ix_cortex_substrate_pipeline_runs_status",
        "cortex_substrate_pipeline_runs",
        ["status"],
    )
    op.create_index(
        "ix_cortex_substrate_pipeline_runs_idempotency_key",
        "cortex_substrate_pipeline_runs",
        ["idempotency_key"],
    )

    op.create_table(
        "cortex_substrate_phase_runs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("pipeline_run_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("phase_id", sa.String(length=64), nullable=False),
        sa.Column("phase_ordinal", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "output_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(length=256), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["cortex_substrate_pipeline_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_cortex_substrate_phase_runs_pipeline_run_id",
        "cortex_substrate_phase_runs",
        ["pipeline_run_id"],
    )
    op.create_index(
        "ix_cortex_substrate_phase_runs_tenant_id",
        "cortex_substrate_phase_runs",
        ["tenant_id"],
    )
    op.create_index(
        "ix_cortex_substrate_phase_runs_status",
        "cortex_substrate_phase_runs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("cortex_substrate_phase_runs")
    op.drop_table("cortex_substrate_pipeline_runs")
