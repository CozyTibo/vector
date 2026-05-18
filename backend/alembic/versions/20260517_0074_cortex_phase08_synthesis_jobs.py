"""Cortex Phase 08 Step 06 — synthesis jobs + append-only receipts.

Revision ID: 20260517_0074
Revises: 20260516_0073
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260517_0074"
down_revision: Union[str, None] = "20260516_0073"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_synthesis_jobs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("envelope_json", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column("envelope_digest", sa.String(length=128), nullable=False),
        sa.Column("synthesis_workload_class", sa.String(length=64), nullable=False),
        sa.Column("synthesis_intent", sa.String(length=64), nullable=False),
        sa.Column("execution_partition", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=256), nullable=True),
        sa.Column("synthesis_policy_pack_id", sa.String(length=256), nullable=False),
        sa.Column("synthesis_orchestrator_build_id", sa.String(length=128), nullable=False),
        sa.Column("retrieval_ingress_digest", sa.String(length=128), nullable=True),
        sa.Column("synthesis_job_replay_identity", sa.String(length=128), nullable=True),
        sa.Column("receipt_digest", sa.String(length=128), nullable=True),
        sa.Column("receipt_json", pg.JSONB(), nullable=True),
        sa.Column("execution_trace_json", pg.JSONB(), nullable=True),
        sa.Column("substrate_pipeline_run_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("celery_task_id", sa.String(length=256), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["substrate_pipeline_run_id"],
            ["cortex_substrate_pipeline_runs.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_cortex_synthesis_jobs_tenant_created",
        "cortex_synthesis_jobs",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_cortex_synthesis_jobs_tenant_idempotency",
        "cortex_synthesis_jobs",
        ["tenant_id", "idempotency_key"],
    )

    op.create_table(
        "cortex_synthesis_job_receipts",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_digest", sa.String(length=128), nullable=False),
        sa.Column("receipt_json", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column("execution_trace_json", pg.JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["cortex_synthesis_jobs.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_cortex_synthesis_job_receipts_job_created",
        "cortex_synthesis_job_receipts",
        ["job_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("cortex_synthesis_job_receipts")
    op.drop_table("cortex_synthesis_jobs")
