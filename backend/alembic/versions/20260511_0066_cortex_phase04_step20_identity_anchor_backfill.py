"""Cortex Phase 04 Step 20 — identity anchor → org handle backfill audit (P04-20).

Revision ID: 20260511_0066
Revises: 20260510_0065
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260511_0066"
down_revision: Union[str, None] = "20260510_0065"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_org_identity_backfill_runs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("anchors_scanned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("entities_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("backfill_set_sha256", sa.String(length=64), nullable=False),
        sa.Column("summary_json", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_cortex_org_identity_backfill_runs_tenant_id",
        "cortex_org_identity_backfill_runs",
        ["tenant_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_cortex_org_identity_backfill_runs_tenant",
        "cortex_org_identity_backfill_runs",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_table("cortex_org_identity_backfill_runs")
