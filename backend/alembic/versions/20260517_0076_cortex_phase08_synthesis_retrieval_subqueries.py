"""Cortex Phase 08 Step 10 — synthesis job retrieval sub-query receipts.

Revision ID: 20260517_0076
Revises: 20260517_0075
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260517_0076"
down_revision: Union[str, None] = "20260517_0075"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cortex_synthesis_jobs",
        sa.Column(
            "retrieval_subqueries_json",
            pg.JSONB(),
            nullable=True,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("cortex_synthesis_jobs", "retrieval_subqueries_json")
