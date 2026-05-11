"""Cortex Phase 03 Step 10 — canonical replay / rebuild jobs + C0–C5 divergence receipts.

Revision ID: 20260508_0044
Revises: 20260508_0043
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260508_0044"
down_revision: Union[str, None] = "20260508_0043"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_canonical_replay_jobs",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "pinned_bundle_id",
            sa.String(length=256),
            sa.ForeignKey("cortex_mapping_bundles.bundle_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("job_kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "source_bundle_id",
            sa.String(length=256),
            sa.ForeignKey("cortex_mapping_bundles.bundle_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("scope_raw_record_ids", pg.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("resolved_pin_json", pg.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
        sa.Column(
            "summary_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cortex_canonical_replay_jobs_tenant_created",
        "cortex_canonical_replay_jobs",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "cortex_canonical_replay_job_receipts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "job_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("cortex_canonical_replay_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "raw_record_id",
            sa.BigInteger(),
            sa.ForeignKey("raw_ingestion_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("divergence_class", sa.String(length=8), nullable=False),
        sa.Column("detail_json", pg.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("materialize_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cortex_canonical_replay_job_receipts_job",
        "cortex_canonical_replay_job_receipts",
        ["job_id"],
        unique=False,
    )
    op.add_column(
        "cortex_canonical_transform_materializations",
        sa.Column(
            "last_replay_job_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("cortex_canonical_replay_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_cortex_canonical_transform_mat_last_replay_job",
        "cortex_canonical_transform_materializations",
        ["last_replay_job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cortex_canonical_transform_mat_last_replay_job",
        table_name="cortex_canonical_transform_materializations",
    )
    op.drop_column("cortex_canonical_transform_materializations", "last_replay_job_id")
    op.drop_index("ix_cortex_canonical_replay_job_receipts_job", table_name="cortex_canonical_replay_job_receipts")
    op.drop_table("cortex_canonical_replay_job_receipts")
    op.drop_index("ix_cortex_canonical_replay_jobs_tenant_created", table_name="cortex_canonical_replay_jobs")
    op.drop_table("cortex_canonical_replay_jobs")
