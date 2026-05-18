"""Cortex Phase 08 Step 33 — durable store indexes + retention audit.

Revision ID: 20260517_0081
Revises: 20260517_0080
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260517_0081"
down_revision: Union[str, None] = "20260517_0080"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_cortex_synthesis_jobs_tenant_status_created",
        "cortex_synthesis_jobs",
        ["tenant_id", "status", "created_at"],
    )
    op.create_index(
        "ix_cortex_synthesis_jobs_tenant_pipeline",
        "cortex_synthesis_jobs",
        ["tenant_id", "substrate_pipeline_run_id"],
    )
    op.create_index(
        "uq_cortex_synthesis_jobs_tenant_idem_digest_completed",
        "cortex_synthesis_jobs",
        ["tenant_id", "idempotency_key", "envelope_digest"],
        unique=True,
        postgresql_where=sa.text(
            "status = 'completed' AND idempotency_key IS NOT NULL",
        ),
    )
    op.create_index(
        "ix_cortex_synthesis_job_receipts_tenant_created",
        "cortex_synthesis_job_receipts",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_cortex_synthesis_artifacts_tenant_published_created",
        "cortex_synthesis_artifacts",
        ["tenant_id", "published", "created_at"],
    )
    op.create_index(
        "ix_cortex_synthesis_publication_epochs_tenant_published_at",
        "cortex_synthesis_publication_epochs",
        ["tenant_id", "published_at"],
    )

    op.create_table(
        "cortex_synthesis_retention_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("detail", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cortex_synthesis_retention_events_tenant_id"),
        "cortex_synthesis_retention_events",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_cortex_synthesis_retention_events_tenant_created",
        "cortex_synthesis_retention_events",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cortex_synthesis_retention_events_tenant_created",
        table_name="cortex_synthesis_retention_events",
    )
    op.drop_index(
        op.f("ix_cortex_synthesis_retention_events_tenant_id"),
        table_name="cortex_synthesis_retention_events",
    )
    op.drop_table("cortex_synthesis_retention_events")
    op.drop_index(
        "ix_cortex_synthesis_publication_epochs_tenant_published_at",
        table_name="cortex_synthesis_publication_epochs",
    )
    op.drop_index(
        "ix_cortex_synthesis_artifacts_tenant_published_created",
        table_name="cortex_synthesis_artifacts",
    )
    op.drop_index(
        "ix_cortex_synthesis_job_receipts_tenant_created",
        table_name="cortex_synthesis_job_receipts",
    )
    op.drop_index(
        "uq_cortex_synthesis_jobs_tenant_idem_digest_completed",
        table_name="cortex_synthesis_jobs",
    )
    op.drop_index("ix_cortex_synthesis_jobs_tenant_pipeline", table_name="cortex_synthesis_jobs")
    op.drop_index(
        "ix_cortex_synthesis_jobs_tenant_status_created",
        table_name="cortex_synthesis_jobs",
    )
