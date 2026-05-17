"""Cortex Phase 07 Step 14 — retrieval index epochs + publish barrier.

Revision ID: 20260516_0071
Revises: 20260516_0070
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260516_0071"
down_revision: Union[str, None] = "20260516_0070"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_retrieval_index_epochs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("index_epoch", sa.String(length=128), nullable=False),
        sa.Column("build_state", sa.String(length=32), nullable=False),
        sa.Column("entry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_index_hash", sa.String(length=128), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
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
    )
    op.create_index(
        "ix_cortex_retrieval_index_epochs_tenant",
        "cortex_retrieval_index_epochs",
        ["tenant_id"],
    )
    op.create_index(
        "ix_cortex_retrieval_index_epochs_tenant_state",
        "cortex_retrieval_index_epochs",
        ["tenant_id", "build_state"],
    )
    op.create_unique_constraint(
        "uq_cortex_retrieval_index_epochs_tenant_epoch",
        "cortex_retrieval_index_epochs",
        ["tenant_id", "index_epoch"],
    )

    op.add_column(
        "cortex_retrieval_index_entries",
        sa.Column("index_epoch", sa.String(length=128), nullable=True),
    )
    op.execute(
        """
        UPDATE cortex_retrieval_index_entries
        SET index_epoch = traversal_epoch
        WHERE index_epoch IS NULL AND traversal_epoch IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("cortex_retrieval_index_entries", "index_epoch")
    op.drop_table("cortex_retrieval_index_epochs")
