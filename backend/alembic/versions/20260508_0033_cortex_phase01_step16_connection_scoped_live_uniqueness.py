"""Cortex Phase 01 Step 16 — connection-scoped live uniqueness semantics.

Revision ID: 20260508_0033
Revises: 20260508_0032

Live idempotency uniqueness moves from tenant+connector scope to
tenant+connection+connector scope so multi-connection tenants do not
silently suppress valid rows across active connections.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260508_0033"
down_revision: Union[str, None] = "20260508_0032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("uq_raw_ingestion_live_identity_revision", table_name="raw_ingestion_records")
    op.create_index(
        "uq_raw_ingestion_live_connection_identity_revision",
        "raw_ingestion_records",
        [
            "tenant_id",
            "connection_id",
            "connector",
            "resource_type",
            "source_identity_key",
            "source_revision_key",
        ],
        unique=True,
        postgresql_where=sa.text("replay_job_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_raw_ingestion_live_connection_identity_revision", table_name="raw_ingestion_records")
    op.create_index(
        "uq_raw_ingestion_live_identity_revision",
        "raw_ingestion_records",
        ["tenant_id", "connector", "resource_type", "source_identity_key", "source_revision_key"],
        unique=True,
        postgresql_where=sa.text("replay_job_id IS NULL"),
    )
