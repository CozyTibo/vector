"""Cortex Phase 02 Step 6 — storage/retention archive catalog + audit events.

Revision ID: 20260508_0036
Revises: 20260508_0035
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260508_0036"
down_revision: Union[str, None] = "20260508_0035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "raw_memory_archive_catalog",
        sa.Column("raw_id", sa.BigInteger(), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connector", sa.String(length=32), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("source_identity_key", sa.String(length=255), nullable=False),
        sa.Column("source_revision_key", sa.String(length=128), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("storage_tier", sa.String(length=16), nullable=False),
        sa.Column("archive_pointer", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retention_class", sa.String(length=64), nullable=False),
        sa.Column("retention_policy_version", sa.Integer(), nullable=False),
        sa.Column("retain_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", pg.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["raw_id"], ["raw_ingestion_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("raw_id"),
    )
    op.create_index(
        "ix_raw_memory_archive_catalog_tenant_tier",
        "raw_memory_archive_catalog",
        ["tenant_id", "storage_tier"],
        unique=False,
    )
    op.create_index(
        "ix_raw_memory_archive_catalog_tenant_connector",
        "raw_memory_archive_catalog",
        ["tenant_id", "connector", "resource_type"],
        unique=False,
    )

    op.create_table(
        "raw_memory_retention_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_id", sa.BigInteger(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("detail", pg.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_raw_memory_retention_events_tenant_created",
        "raw_memory_retention_events",
        ["tenant_id", "created_at"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO raw_memory_archive_catalog (
                raw_id,
                tenant_id,
                connection_id,
                connector,
                resource_type,
                source_identity_key,
                source_revision_key,
                payload_hash,
                storage_tier,
                archive_pointer,
                archived_at,
                retention_class,
                retention_policy_version,
                retain_until,
                metadata_json
            )
            SELECT
                r.id,
                r.tenant_id,
                r.connection_id,
                r.connector,
                r.resource_type,
                r.source_identity_key,
                r.source_revision_key,
                r.payload_hash,
                'hot',
                NULL,
                NULL,
                CASE
                    WHEN r.resource_type IN ('calls.transcript', 'calls.transcript_segment') THEN 'audit_long_horizon'
                    WHEN r.resource_type LIKE '%.scope_ping' OR r.resource_type IN ('scope_ping', 'viewer_ping', 'linear.viewer_ping')
                        THEN 'operational_replay'
                    ELSE 'operational_replay'
                END,
                1,
                NULL,
                '{}'::jsonb
            FROM raw_ingestion_records r
            ON CONFLICT (raw_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_raw_memory_retention_events_tenant_created", table_name="raw_memory_retention_events")
    op.drop_table("raw_memory_retention_events")
    op.drop_index("ix_raw_memory_archive_catalog_tenant_connector", table_name="raw_memory_archive_catalog")
    op.drop_index("ix_raw_memory_archive_catalog_tenant_tier", table_name="raw_memory_archive_catalog")
    op.drop_table("raw_memory_archive_catalog")
