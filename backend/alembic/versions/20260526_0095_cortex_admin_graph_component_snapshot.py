"""Admin graph component snapshot table for async operator inspect (R4).

Revision ID: 20260526_0095
Revises: 20260525_0094
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260526_0095"
down_revision: Union[str, None] = "20260525_0094"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_admin_graph_component_snapshot",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "captured_at_utc",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("component_count", sa.Integer(), nullable=True),
        sa.Column(
            "component_sizes_top_20",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("job_status", sa.String(length=32), nullable=False, server_default="idle"),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("cortex_admin_graph_component_snapshot")
