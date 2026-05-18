"""Cortex Phase 08 Step 07 — synthesis_legality_class on jobs.

Revision ID: 20260517_0075
Revises: 20260517_0074
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260517_0075"
down_revision: Union[str, None] = "20260517_0074"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cortex_synthesis_jobs",
        sa.Column("synthesis_legality_class", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_cortex_synthesis_jobs_tenant_legality",
        "cortex_synthesis_jobs",
        ["tenant_id", "synthesis_legality_class"],
    )


def downgrade() -> None:
    op.drop_index("ix_cortex_synthesis_jobs_tenant_legality", table_name="cortex_synthesis_jobs")
    op.drop_column("cortex_synthesis_jobs", "synthesis_legality_class")
