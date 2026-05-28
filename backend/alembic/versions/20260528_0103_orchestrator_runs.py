"""orchestrator_runs — unified Cortex orchestrator tick audit.

Revision ID: 20260528_0103
Revises: 20260528_0102
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260528_0103"
down_revision = "20260528_0102"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orchestrator_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("beat_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("ingestion_enqueued", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passes_planned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passes_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detail_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_summary", sa.String(length=512), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orchestrator_runs_started_at", "orchestrator_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_orchestrator_runs_started_at", table_name="orchestrator_runs")
    op.drop_table("orchestrator_runs")
