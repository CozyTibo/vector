"""§6 Step 39 — manager_insight_outcomes + manager_insight_policy_counters (§5.2–§5.3).

Revision ID: 20260430_0027
Revises: 20260430_0026
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260430_0027"
down_revision: Union[str, None] = "20260430_0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "manager_insight_outcomes",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("decision_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("outcome_type", sa.Text(), nullable=False),
        sa.Column("false_positive", sa.Boolean(), nullable=True),
        sa.Column(
            "ground_truth",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("user_attribution", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["decision_id"],
            ["manager_insight_decisions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_manager_insight_outcomes_tenant_id",
        "manager_insight_outcomes",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_manager_insight_outcomes_decision_id",
        "manager_insight_outcomes",
        ["decision_id"],
        unique=False,
    )
    op.create_index(
        "ix_manager_insight_outcomes_tenant_observed_at",
        "manager_insight_outcomes",
        ["tenant_id", "observed_at"],
        unique=False,
    )

    op.create_table(
        "manager_insight_policy_counters",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("dimension", sa.Text(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "false_positive_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("suppress_until", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tenant_id", "dimension", "window_start"),
    )


def downgrade() -> None:
    op.drop_table("manager_insight_policy_counters")
    op.drop_index(
        "ix_manager_insight_outcomes_tenant_observed_at",
        table_name="manager_insight_outcomes",
    )
    op.drop_index(
        "ix_manager_insight_outcomes_decision_id",
        table_name="manager_insight_outcomes",
    )
    op.drop_index(
        "ix_manager_insight_outcomes_tenant_id",
        table_name="manager_insight_outcomes",
    )
    op.drop_table("manager_insight_outcomes")
