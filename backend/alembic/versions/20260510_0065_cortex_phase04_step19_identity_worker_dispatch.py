"""Cortex Phase 04 Step 19 — identity worker dispatch visibility (P04-19).

Revision ID: 20260510_0065
Revises: 20260510_0064
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260510_0065"
down_revision: Union[str, None] = "20260510_0064"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cortex_org_link_replay_jobs",
        sa.Column("celery_task_id", sa.String(length=256), nullable=True),
    )
    op.create_index(
        "ix_cortex_org_link_replay_jobs_celery_task_id",
        "cortex_org_link_replay_jobs",
        ["celery_task_id"],
        unique=False,
    )

    op.create_table(
        "cortex_identity_celery_dispatches",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("celery_task_id", sa.String(length=256), nullable=False),
        sa.Column("task_name", sa.String(length=128), nullable=False),
        sa.Column(
            "request_summary_json",
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
        "ix_cortex_identity_celery_dispatches_tenant",
        "cortex_identity_celery_dispatches",
        ["tenant_id"],
    )
    op.create_index(
        "uq_cortex_identity_celery_dispatches_task_id",
        "cortex_identity_celery_dispatches",
        ["celery_task_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_cortex_identity_celery_dispatches_task_id", table_name="cortex_identity_celery_dispatches")
    op.drop_index("ix_cortex_identity_celery_dispatches_tenant", table_name="cortex_identity_celery_dispatches")
    op.drop_table("cortex_identity_celery_dispatches")
    op.drop_index("ix_cortex_org_link_replay_jobs_celery_task_id", table_name="cortex_org_link_replay_jobs")
    op.drop_column("cortex_org_link_replay_jobs", "celery_task_id")
