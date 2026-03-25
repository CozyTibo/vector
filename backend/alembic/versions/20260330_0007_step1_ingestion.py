"""Step 1 ingestion: runs, raw append-only records (replay_sequence), sync state.

Revision ID: 20260330_0007
Revises: 20260329_0006
Create Date: 2026-03-30

Replay ordering (normalization / consumers): ORDER BY replay_sequence ASC, id ASC.

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260330_0007"
down_revision: Union[str, None] = "20260329_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("CREATE SEQUENCE IF NOT EXISTS raw_ingestion_replay_seq"))

    op.create_table(
        "ingestion_runs",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connector", sa.String(length=32), nullable=False),
        sa.Column("source_trigger", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("stats", pg.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["connection_id"], ["tenant_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingestion_runs_connection_started",
        "ingestion_runs",
        ["connection_id", "started_at"],
        unique=False,
        postgresql_ops={"started_at": "DESC"},
    )
    op.create_index(
        "ix_ingestion_runs_tenant_started",
        "ingestion_runs",
        ["tenant_id", "started_at"],
        unique=False,
        postgresql_ops={"started_at": "DESC"},
    )

    op.create_table(
        "raw_ingestion_records",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "replay_sequence",
            sa.BigInteger(),
            server_default=sa.text("nextval('raw_ingestion_replay_seq')"),
            nullable=False,
        ),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connector", sa.String(length=32), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=512), nullable=False),
        sa.Column("api_endpoint", sa.String(length=512), nullable=False),
        sa.Column("query_params", pg.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_body", pg.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("run_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("source_trigger", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["ingestion_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "idempotency_key", name="uq_raw_ingestion_records_run_idempotency"),
    )
    op.create_index("ix_raw_ingestion_records_run_id", "raw_ingestion_records", ["run_id"])
    op.create_index(
        "ix_raw_ingestion_records_conn_resource_fetched",
        "raw_ingestion_records",
        ["connection_id", "resource_type", "fetched_at"],
        unique=False,
        postgresql_ops={"fetched_at": "DESC"},
    )
    op.create_index(
        "ix_raw_ingestion_records_conn_external_fetched",
        "raw_ingestion_records",
        ["connection_id", "external_id", "fetched_at"],
        unique=False,
        postgresql_ops={"fetched_at": "DESC"},
    )
    op.create_index(
        "ix_raw_ingestion_records_replay_order",
        "raw_ingestion_records",
        ["replay_sequence", "id"],
        unique=False,
    )

    op.create_table(
        "connector_sync_state",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connector", sa.String(length=32), nullable=False),
        sa.Column("scope_key", sa.String(length=512), nullable=False),
        sa.Column("state", pg.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["connection_id"], ["tenant_connections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tenant_id", "connection_id", "connector", "scope_key"),
    )


def downgrade() -> None:
    op.drop_table("connector_sync_state")
    op.drop_index("ix_raw_ingestion_records_replay_order", table_name="raw_ingestion_records")
    op.drop_index("ix_raw_ingestion_records_conn_external_fetched", table_name="raw_ingestion_records")
    op.drop_index("ix_raw_ingestion_records_conn_resource_fetched", table_name="raw_ingestion_records")
    op.drop_index("ix_raw_ingestion_records_run_id", table_name="raw_ingestion_records")
    op.drop_table("raw_ingestion_records")
    op.drop_index("ix_ingestion_runs_tenant_started", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_connection_started", table_name="ingestion_runs")
    op.drop_table("ingestion_runs")
    op.execute(sa.text("DROP SEQUENCE IF EXISTS raw_ingestion_replay_seq"))
