"""Cortex substrate pipeline dead-letter queue (P085-07 / G-P085-DLQ-01).

Revision ID: 20260518_0083
Revises: 20260517_0082
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260518_0083"
down_revision: Union[str, None] = "20260517_0082"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_substrate_pipeline_dead_letters",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_run_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("phase_id", sa.String(length=64), nullable=False),
        sa.Column("async_job_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("failure_class", sa.String(length=64), nullable=False),
        sa.Column("replay_safe", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "recovery_actions",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("resume_receipt_hash", sa.String(length=128), nullable=True),
        sa.Column("auto_retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dlq_status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("failure_detail", sa.Text(), nullable=True),
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
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["cortex_substrate_pipeline_runs.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_cortex_substrate_dlq_tenant_status",
        "cortex_substrate_pipeline_dead_letters",
        ["tenant_id", "dlq_status"],
    )
    op.create_index(
        "ix_cortex_substrate_dlq_receipt_hash",
        "cortex_substrate_pipeline_dead_letters",
        ["resume_receipt_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_cortex_substrate_dlq_receipt_hash")
    op.drop_index("ix_cortex_substrate_dlq_tenant_status")
    op.drop_table("cortex_substrate_pipeline_dead_letters")
