"""ingestion_scheduler_ticks — Celery Beat tick audit for Cortex ingestion only.

Revision ID: 20260527_0096
Revises: 20260526_0095
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260527_0096"
down_revision: Union[str, None] = "20260526_0095"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingestion_scheduler_ticks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("enqueued_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("beat_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("skip_reason", sa.String(length=128), nullable=True),
        sa.Column("enqueued_jobs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingestion_scheduler_ticks_started_at",
        "ingestion_scheduler_ticks",
        ["started_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ingestion_scheduler_ticks_started_at", table_name="ingestion_scheduler_ticks")
    op.drop_table("ingestion_scheduler_ticks")
