"""Cortex Phase 01 Step 3 — replay-safe run metadata, raw lineage, replay idempotency.

Revision ID: 20260508_0031
Revises: 20260508_0030

- Runs carry ``sync_mode``, ``replay_mode``, optional ``replay_job_id``, ``replay_version``.
- Raw rows carry optional ``replay_job_id`` / ``replay_version`` for lineage.
- Partial unique index dedupes replay writes for the same job + idempotency key (live rows
  keep ``replay_job_id`` NULL and use existing per-run uniqueness).

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260508_0031"
down_revision: Union[str, None] = "20260508_0030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ingestion_runs",
        sa.Column(
            "sync_mode",
            sa.String(length=32),
            nullable=False,
            server_default="incremental",
        ),
    )
    op.add_column(
        "ingestion_runs",
        sa.Column(
            "replay_mode",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "ingestion_runs",
        sa.Column("replay_job_id", pg.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "ingestion_runs",
        sa.Column(
            "replay_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.create_index(
        "ix_ingestion_runs_replay_job_started",
        "ingestion_runs",
        ["replay_job_id", "started_at"],
        unique=False,
        postgresql_where=sa.text("replay_job_id IS NOT NULL"),
    )

    op.add_column(
        "raw_ingestion_records",
        sa.Column("replay_job_id", pg.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("raw_ingestion_records", sa.Column("replay_version", sa.Integer(), nullable=True))
    op.create_index(
        "uq_raw_ingestion_replay_job_idempotency",
        "raw_ingestion_records",
        ["replay_job_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("replay_job_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_raw_ingestion_replay_job_idempotency", table_name="raw_ingestion_records")
    op.drop_column("raw_ingestion_records", "replay_version")
    op.drop_column("raw_ingestion_records", "replay_job_id")

    op.drop_index("ix_ingestion_runs_replay_job_started", table_name="ingestion_runs")
    op.drop_column("ingestion_runs", "replay_version")
    op.drop_column("ingestion_runs", "replay_job_id")
    op.drop_column("ingestion_runs", "replay_mode")
    op.drop_column("ingestion_runs", "sync_mode")
