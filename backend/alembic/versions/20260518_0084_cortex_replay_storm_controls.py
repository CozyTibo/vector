"""Cortex replay storm controls + divergence events (P085-34 / G-P085-ECON-02).

Revision ID: 20260518_0084
Revises: 20260518_0083
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260518_0084"
down_revision: Union[str, None] = "20260518_0083"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_replay_divergence_events",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column(
            "detail_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_cortex_replay_div_events_tenant_created",
        "cortex_replay_divergence_events",
        ["tenant_id", "created_at"],
    )

    op.create_table(
        "cortex_replay_storm_controls",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("storm_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "exploration_partition_paused",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("pinned_retrieval_policy_digest", sa.String(length=128), nullable=True),
        sa.Column("pinned_synthesis_policy_pack_digest", sa.String(length=128), nullable=True),
        sa.Column("pinned_tcre_policy_bundle_digest", sa.String(length=128), nullable=True),
        sa.Column("operator_acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("operator_acknowledged_by", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("storm_detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "detail_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["operator_acknowledged_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", name="uq_cortex_replay_storm_controls_tenant"),
    )


def downgrade() -> None:
    op.drop_table("cortex_replay_storm_controls")
    op.drop_table("cortex_replay_divergence_events")
