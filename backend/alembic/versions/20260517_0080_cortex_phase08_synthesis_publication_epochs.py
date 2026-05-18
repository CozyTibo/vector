"""Cortex Phase 08 Step 31 — synthesis publication epochs.

Revision ID: 20260517_0080
Revises: 20260517_0079
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260517_0080"
down_revision: Union[str, None] = "20260517_0079"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_synthesis_publication_epochs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("synthesis_publication_epoch", sa.String(length=128), nullable=False),
        sa.Column("published_index_epoch", sa.String(length=128), nullable=True),
        sa.Column("artifact_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("substrate_pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cortex_synthesis_publication_epochs_tenant_epoch",
        "cortex_synthesis_publication_epochs",
        ["tenant_id", "synthesis_publication_epoch"],
        unique=True,
    )
    op.create_index(
        op.f("ix_cortex_synthesis_publication_epochs_tenant_id"),
        "cortex_synthesis_publication_epochs",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cortex_synthesis_publication_epochs_substrate_pipeline_run_id"),
        "cortex_synthesis_publication_epochs",
        ["substrate_pipeline_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_cortex_synthesis_publication_epochs_substrate_pipeline_run_id"),
        table_name="cortex_synthesis_publication_epochs",
    )
    op.drop_index(
        op.f("ix_cortex_synthesis_publication_epochs_tenant_id"),
        table_name="cortex_synthesis_publication_epochs",
    )
    op.drop_index(
        "ix_cortex_synthesis_publication_epochs_tenant_epoch",
        table_name="cortex_synthesis_publication_epochs",
    )
    op.drop_table("cortex_synthesis_publication_epochs")
