"""Cortex Phase 03 Step 8 — confidence class + metadata on field lineage rows.

Revision ID: 20260508_0042
Revises: 20260508_0041
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260508_0042"
down_revision: Union[str, None] = "20260508_0041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cortex_canonical_field_lineage",
        sa.Column(
            "confidence_class",
            sa.String(length=64),
            nullable=False,
            server_default="DETERMINISTIC_RULE",
        ),
    )
    op.add_column(
        "cortex_canonical_field_lineage",
        sa.Column(
            "confidence_metadata",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index(
        "ix_cortex_field_lineage_confidence_class",
        "cortex_canonical_field_lineage",
        ["confidence_class"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cortex_field_lineage_confidence_class", table_name="cortex_canonical_field_lineage")
    op.drop_column("cortex_canonical_field_lineage", "confidence_metadata")
    op.drop_column("cortex_canonical_field_lineage", "confidence_class")
