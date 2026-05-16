"""Cortex Phase 06 RUNTIME-01 — TCRE reconstruction jobs + persisted artifacts.

Revision ID: 20260516_0069
Revises: 20260511_0068
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260516_0069"
down_revision: Union[str, None] = "20260511_0068"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_tcre_reconstruction_jobs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("job_kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        sa.Column("tcre_policy_bundle_digest", sa.String(length=128), nullable=False),
        sa.Column("reasoning_rule_pack_id", sa.String(length=256), nullable=False),
        sa.Column("parent_job_id", pg.UUID(as_uuid=True), nullable=True),
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
        sa.Column("celery_task_id", sa.String(length=256), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_job_id"],
            ["cortex_tcre_reconstruction_jobs.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_cortex_tcre_recon_jobs_tenant",
        "cortex_tcre_reconstruction_jobs",
        ["tenant_id"],
    )
    op.create_index(
        "ix_cortex_tcre_recon_jobs_tenant_created",
        "cortex_tcre_reconstruction_jobs",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_cortex_tcre_recon_jobs_tenant_status",
        "cortex_tcre_reconstruction_jobs",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_cortex_tcre_recon_jobs_celery_task_id",
        "cortex_tcre_reconstruction_jobs",
        ["celery_task_id"],
    )

    op.create_table(
        "cortex_tcre_reconstruction_artifacts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("job_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_kind", sa.String(length=64), nullable=False),
        sa.Column("artifact_key", sa.String(length=256), nullable=False),
        sa.Column("artifact_digest", sa.String(length=128), nullable=False),
        sa.Column(
            "body_json",
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
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["cortex_tcre_reconstruction_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "job_id",
            "artifact_kind",
            "artifact_key",
            name="uq_cortex_tcre_recon_artifact_job_kind_key",
        ),
    )
    op.create_index(
        "ix_cortex_tcre_recon_art_job",
        "cortex_tcre_reconstruction_artifacts",
        ["job_id"],
    )
    op.create_index(
        "ix_cortex_tcre_recon_art_tenant_kind",
        "cortex_tcre_reconstruction_artifacts",
        ["tenant_id", "artifact_kind"],
    )


def downgrade() -> None:
    op.drop_index("ix_cortex_tcre_recon_art_tenant_kind", table_name="cortex_tcre_reconstruction_artifacts")
    op.drop_index("ix_cortex_tcre_recon_art_job", table_name="cortex_tcre_reconstruction_artifacts")
    op.drop_table("cortex_tcre_reconstruction_artifacts")
    op.drop_index("ix_cortex_tcre_recon_jobs_celery_task_id", table_name="cortex_tcre_reconstruction_jobs")
    op.drop_index("ix_cortex_tcre_recon_jobs_tenant_status", table_name="cortex_tcre_reconstruction_jobs")
    op.drop_index("ix_cortex_tcre_recon_jobs_tenant_created", table_name="cortex_tcre_reconstruction_jobs")
    op.drop_index("ix_cortex_tcre_recon_jobs_tenant", table_name="cortex_tcre_reconstruction_jobs")
    op.drop_table("cortex_tcre_reconstruction_jobs")
