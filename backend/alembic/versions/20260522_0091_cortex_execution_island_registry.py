"""P2-C execution island registry — per-tenant component scope persistence.

Revision ID: 20260522_0091
Revises: 20260521_0090
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260522_0091"
down_revision: Union[str, None] = "20260521_0090"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_execution_island_registry",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("island_scope_id", sa.String(length=16), nullable=False),
        sa.Column("entity_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("authoritative_edge_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "entity_ids",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("last_walk_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_retrieval_epoch", sa.String(length=128), nullable=True),
        sa.Column(
            "registry_snapshot_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
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
        sa.UniqueConstraint(
            "tenant_id",
            "island_scope_id",
            name="uq_cortex_execution_island_registry_tenant_scope",
        ),
    )
    op.create_index(
        "ix_cortex_execution_island_registry_tenant_id",
        "cortex_execution_island_registry",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cortex_execution_island_registry_tenant_id",
        table_name="cortex_execution_island_registry",
    )
    op.drop_table("cortex_execution_island_registry")
