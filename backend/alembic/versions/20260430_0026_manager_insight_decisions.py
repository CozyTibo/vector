"""§6 Step 30 — manager_insight_decisions table (coordination persistence, §5.1).

Revision ID: 20260430_0026
Revises: 20260430_0025
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260430_0026"
down_revision: Union[str, None] = "20260430_0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "manager_insight_decisions",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("gap_id", sa.Text(), nullable=False),
        sa.Column("gap_type", sa.Text(), nullable=False),
        sa.Column("decision_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "default_action",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "required_inputs",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "evidence_refs",
            pg.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "signal_refs",
            pg.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'proposed'"),
        ),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("slack_channel_id", sa.Text(), nullable=True),
        sa.Column("slack_message_ts", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column("receipt", pg.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_manager_insight_decisions_idempotency_key"),
    )
    op.create_index(
        "ix_manager_insight_decisions_tenant_id",
        "manager_insight_decisions",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_manager_insight_decisions_run_id",
        "manager_insight_decisions",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_manager_insight_decisions_tenant_gap_id",
        "manager_insight_decisions",
        ["tenant_id", "gap_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_manager_insight_decisions_tenant_gap_id", table_name="manager_insight_decisions")
    op.drop_index("ix_manager_insight_decisions_run_id", table_name="manager_insight_decisions")
    op.drop_index("ix_manager_insight_decisions_tenant_id", table_name="manager_insight_decisions")
    op.drop_table("manager_insight_decisions")
