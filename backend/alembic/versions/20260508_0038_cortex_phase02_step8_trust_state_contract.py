"""Cortex Phase 02 Step 8 — trust-state snapshots + transition log.

Revision ID: 20260508_0038
Revises: 20260508_0037
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260508_0038"
down_revision: Union[str, None] = "20260508_0037"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "raw_memory_trust_state",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("trust_state", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=8), nullable=False),
        sa.Column("state_reason_codes", pg.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("gate_results", pg.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("blocking", pg.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("continuity_gaps", pg.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("verification", pg.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tenant_id"),
    )
    op.create_table(
        "raw_memory_trust_transitions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("from_state", sa.String(length=64), nullable=True),
        sa.Column("to_state", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=8), nullable=False),
        sa.Column("trigger", sa.String(length=128), nullable=False),
        sa.Column("detail", pg.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_raw_memory_trust_transitions_tenant_created",
        "raw_memory_trust_transitions",
        ["tenant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_raw_memory_trust_transitions_tenant_created", table_name="raw_memory_trust_transitions")
    op.drop_table("raw_memory_trust_transitions")
    op.drop_table("raw_memory_trust_state")
