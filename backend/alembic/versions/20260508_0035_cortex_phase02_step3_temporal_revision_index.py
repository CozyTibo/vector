"""Cortex Phase 02 Step 3 — temporal revision/supersession index.

Revision ID: 20260508_0035
Revises: 20260508_0034
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260508_0035"
down_revision: Union[str, None] = "20260508_0034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "raw_memory_revision_index",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connector", sa.String(length=32), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("source_identity_key", sa.String(length=255), nullable=False),
        sa.Column("source_revision_key", sa.String(length=128), nullable=False),
        sa.Column("raw_id", sa.BigInteger(), nullable=False),
        sa.Column("provider_event_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_source_revision_key", sa.String(length=128), nullable=True),
        sa.Column("is_deleted_observed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("run_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("replay_job_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("replay_version", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["ingestion_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "tenant_id",
            "connection_id",
            "connector",
            "resource_type",
            "source_identity_key",
            "source_revision_key",
        ),
        sa.UniqueConstraint("raw_id", name="uq_raw_memory_revision_raw_id"),
    )
    op.create_index(
        "ix_raw_memory_revision_identity_order",
        "raw_memory_revision_index",
        [
            "tenant_id",
            "connection_id",
            "connector",
            "resource_type",
            "source_identity_key",
            "fetched_at",
            "raw_id",
        ],
        unique=False,
    )
    op.create_index(
        "ix_raw_memory_revision_provider_ts",
        "raw_memory_revision_index",
        ["tenant_id", "provider_event_timestamp"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO raw_memory_revision_index (
                tenant_id,
                connection_id,
                connector,
                resource_type,
                source_identity_key,
                source_revision_key,
                raw_id,
                provider_event_timestamp,
                fetched_at,
                supersedes_source_revision_key,
                is_deleted_observed,
                run_id,
                replay_job_id,
                replay_version
            )
            SELECT
                r.tenant_id,
                r.connection_id,
                r.connector,
                r.resource_type,
                r.source_identity_key,
                r.source_revision_key,
                r.id AS raw_id,
                NULL::timestamptz AS provider_event_timestamp,
                r.fetched_at,
                LAG(r.source_revision_key) OVER (
                    PARTITION BY r.tenant_id, r.connection_id, r.connector, r.resource_type, r.source_identity_key
                    ORDER BY r.fetched_at ASC, r.id ASC
                ) AS supersedes_source_revision_key,
                false AS is_deleted_observed,
                r.run_id,
                r.replay_job_id,
                r.replay_version
            FROM raw_ingestion_records r
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_raw_memory_revision_provider_ts", table_name="raw_memory_revision_index")
    op.drop_index("ix_raw_memory_revision_identity_order", table_name="raw_memory_revision_index")
    op.drop_table("raw_memory_revision_index")
