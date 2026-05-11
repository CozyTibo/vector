"""Cortex Phase 04 Step 10 — org link continuity replay jobs + L-class receipts.

Revision ID: 20260510_0058
Revises: 20260510_0057
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260510_0058"
down_revision: Union[str, None] = "20260510_0057"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_org_link_replay_jobs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("job_kind", sa.String(length=32), nullable=False),
        sa.Column("pinned_rule_version", sa.String(length=256), nullable=True),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "scope_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "summary_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
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
        "ix_cortex_org_link_replay_jobs_tenant",
        "cortex_org_link_replay_jobs",
        ["tenant_id"],
    )
    op.create_index(
        "ix_cortex_org_link_replay_jobs_tenant_created",
        "cortex_org_link_replay_jobs",
        ["tenant_id", "created_at"],
    )

    op.create_table(
        "cortex_org_link_replay_job_receipts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("job_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_class", sa.String(length=8), nullable=False),
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
        sa.ForeignKeyConstraint(["job_id"], ["cortex_org_link_replay_jobs.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_cortex_org_link_replay_rcpt_job",
        "cortex_org_link_replay_job_receipts",
        ["job_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_cortex_org_link_replay_rcpt_job", table_name="cortex_org_link_replay_job_receipts")
    op.drop_table("cortex_org_link_replay_job_receipts")
    op.drop_index("ix_cortex_org_link_replay_jobs_tenant_created", table_name="cortex_org_link_replay_jobs")
    op.drop_index("ix_cortex_org_link_replay_jobs_tenant", table_name="cortex_org_link_replay_jobs")
    op.drop_table("cortex_org_link_replay_jobs")
