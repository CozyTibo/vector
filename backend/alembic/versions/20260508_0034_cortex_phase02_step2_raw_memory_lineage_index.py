"""Cortex Phase 02 Step 2 — raw memory lineage/provenance index.

Revision ID: 20260508_0034
Revises: 20260508_0033
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260508_0034"
down_revision: Union[str, None] = "20260508_0033"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "raw_memory_lineage_index",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connector", sa.String(length=32), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("source_identity_key", sa.String(length=255), nullable=False),
        sa.Column("provenance_chain_id", sa.String(length=512), nullable=False),
        sa.Column("first_seen_raw_id", sa.BigInteger(), nullable=False),
        sa.Column("latest_seen_raw_id", sa.BigInteger(), nullable=False),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_source_revision_key", sa.String(length=128), nullable=False),
        sa.Column("latest_payload_hash", sa.String(length=128), nullable=False),
        sa.Column("latest_run_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("latest_replay_job_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("latest_replay_version", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["latest_run_id"], ["ingestion_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint(
            "tenant_id",
            "connection_id",
            "connector",
            "resource_type",
            "source_identity_key",
        ),
    )
    op.create_index(
        "ix_raw_memory_lineage_tenant_connector_latest",
        "raw_memory_lineage_index",
        ["tenant_id", "connector", "latest_observed_at"],
        unique=False,
        postgresql_ops={"latest_observed_at": "DESC"},
    )
    op.create_index(
        "ix_raw_memory_lineage_tenant_replay_job",
        "raw_memory_lineage_index",
        ["tenant_id", "latest_replay_job_id"],
        unique=False,
        postgresql_where=sa.text("latest_replay_job_id IS NOT NULL"),
    )

    # Seed lineage index from existing raw rows so rollout is non-disruptive.
    op.execute(
        sa.text(
            """
            WITH base AS (
                SELECT
                    r.*,
                    LEFT(
                        r.tenant_id::text || ':' || r.connection_id::text || ':' || r.connector || ':'
                        || r.resource_type || ':' || r.source_identity_key,
                        512
                    ) AS provenance_chain_id_calc
                FROM raw_ingestion_records r
            ),
            firsts AS (
                SELECT DISTINCT ON (tenant_id, connection_id, connector, resource_type, source_identity_key)
                    tenant_id,
                    connection_id,
                    connector,
                    resource_type,
                    source_identity_key,
                    provenance_chain_id_calc,
                    id AS first_seen_raw_id,
                    fetched_at AS first_observed_at
                FROM base
                ORDER BY tenant_id, connection_id, connector, resource_type, source_identity_key, fetched_at ASC, id ASC
            ),
            lasts AS (
                SELECT DISTINCT ON (tenant_id, connection_id, connector, resource_type, source_identity_key)
                    tenant_id,
                    connection_id,
                    connector,
                    resource_type,
                    source_identity_key,
                    id AS latest_seen_raw_id,
                    fetched_at AS latest_observed_at,
                    source_revision_key AS latest_source_revision_key,
                    payload_hash AS latest_payload_hash,
                    run_id AS latest_run_id,
                    replay_job_id AS latest_replay_job_id,
                    replay_version AS latest_replay_version
                FROM base
                ORDER BY tenant_id, connection_id, connector, resource_type, source_identity_key, fetched_at DESC, id DESC
            )
            INSERT INTO raw_memory_lineage_index (
                tenant_id,
                connection_id,
                connector,
                resource_type,
                source_identity_key,
                provenance_chain_id,
                first_seen_raw_id,
                latest_seen_raw_id,
                first_observed_at,
                latest_observed_at,
                latest_source_revision_key,
                latest_payload_hash,
                latest_run_id,
                latest_replay_job_id,
                latest_replay_version
            )
            SELECT
                f.tenant_id,
                f.connection_id,
                f.connector,
                f.resource_type,
                f.source_identity_key,
                f.provenance_chain_id_calc,
                f.first_seen_raw_id,
                l.latest_seen_raw_id,
                f.first_observed_at,
                l.latest_observed_at,
                l.latest_source_revision_key,
                l.latest_payload_hash,
                l.latest_run_id,
                l.latest_replay_job_id,
                l.latest_replay_version
            FROM firsts f
            JOIN lasts l
              ON l.tenant_id = f.tenant_id
             AND l.connection_id = f.connection_id
             AND l.connector = f.connector
             AND l.resource_type = f.resource_type
             AND l.source_identity_key = f.source_identity_key
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_raw_memory_lineage_tenant_replay_job", table_name="raw_memory_lineage_index")
    op.drop_index("ix_raw_memory_lineage_tenant_connector_latest", table_name="raw_memory_lineage_index")
    op.drop_table("raw_memory_lineage_index")
