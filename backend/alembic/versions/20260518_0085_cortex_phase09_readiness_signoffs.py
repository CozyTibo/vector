"""Cortex Phase 09 readiness sign-offs (P085-35 / G-P085-READY-01).

Revision ID: 20260518_0085
Revises: 20260518_0084
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260518_0085"
down_revision: Union[str, None] = "20260518_0084"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_phase09_readiness_signoffs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("signoff_kind", sa.String(length=64), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signed_by", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "detail_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.ForeignKeyConstraint(["signed_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_cortex_phase09_readiness_signoffs_kind_signed_at",
        "cortex_phase09_readiness_signoffs",
        ["signoff_kind", "signed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cortex_phase09_readiness_signoffs_kind_signed_at",
        table_name="cortex_phase09_readiness_signoffs",
    )
    op.drop_table("cortex_phase09_readiness_signoffs")
