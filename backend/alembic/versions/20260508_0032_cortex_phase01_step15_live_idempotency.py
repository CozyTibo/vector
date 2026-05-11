"""Cortex Phase 01 Step 15 — live logical idempotency + revision key columns.

Revision ID: 20260508_0032
Revises: 20260508_0031

- Add ``source_identity_key`` / ``source_revision_key`` on raw rows.
- Backfill existing rows from connector/resource/external_id and payload_hash.
- Add live-lane unique index for deterministic conflict-ignore insertion.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260508_0032"
down_revision: Union[str, None] = "20260508_0031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "raw_ingestion_records",
        sa.Column("source_identity_key", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "raw_ingestion_records",
        sa.Column("source_revision_key", sa.String(length=128), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE raw_ingestion_records
            SET
                source_identity_key = LEFT(connector || ':' || resource_type || ':' || external_id, 255),
                source_revision_key = LEFT('hash:' || payload_hash, 128)
            WHERE source_identity_key IS NULL OR source_revision_key IS NULL
            """
        )
    )

    op.alter_column("raw_ingestion_records", "source_identity_key", nullable=False)
    op.alter_column("raw_ingestion_records", "source_revision_key", nullable=False)

    # Existing live-lane history can contain duplicate logical revisions from the
    # pre-Step15 era. Keep the earliest row per deterministic identity+revision
    # key so the new unique index can be created safely.
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY tenant_id, connector, resource_type, source_identity_key, source_revision_key
                        ORDER BY fetched_at ASC, id ASC
                    ) AS rn
                FROM raw_ingestion_records
                WHERE replay_job_id IS NULL
            )
            DELETE FROM raw_ingestion_records r
            USING ranked
            WHERE r.id = ranked.id
              AND ranked.rn > 1
            """
        )
    )

    op.create_index(
        "ix_raw_ingestion_records_source_identity",
        "raw_ingestion_records",
        ["source_identity_key"],
        unique=False,
    )
    op.create_index(
        "uq_raw_ingestion_live_identity_revision",
        "raw_ingestion_records",
        ["tenant_id", "connector", "resource_type", "source_identity_key", "source_revision_key"],
        unique=True,
        postgresql_where=sa.text("replay_job_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_raw_ingestion_live_identity_revision", table_name="raw_ingestion_records")
    op.drop_index("ix_raw_ingestion_records_source_identity", table_name="raw_ingestion_records")
    op.drop_column("raw_ingestion_records", "source_revision_key")
    op.drop_column("raw_ingestion_records", "source_identity_key")
