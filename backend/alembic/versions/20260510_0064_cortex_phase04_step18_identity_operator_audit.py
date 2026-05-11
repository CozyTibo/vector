"""Cortex Phase 04 Step 18 — durable operator-console audit rows (P04-18 / G-P04-23).

Revision ID: 20260510_0064
Revises: 20260510_0063
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260510_0064"
down_revision: Union[str, None] = "20260510_0063"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_org_identity_console_audits",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "tenant_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("surface", sa.String(length=64), nullable=False),
        sa.Column("ref_uuid", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("action_kind", sa.String(length=64), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cortex_org_identity_console_audits_tenant_created",
        "cortex_org_identity_console_audits",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_cortex_org_identity_console_audits_tenant_created", table_name="cortex_org_identity_console_audits")
    op.drop_table("cortex_org_identity_console_audits")
