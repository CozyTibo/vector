"""Cortex Phase 02 Step 7 — failure representation + recovery validation.

Revision ID: 20260508_0037
Revises: 20260508_0036
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260508_0037"
down_revision: Union[str, None] = "20260508_0036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "raw_memory_failure_cases",
        sa.Column("gap_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("failure_class", sa.String(length=64), nullable=False),
        sa.Column("gap_type", sa.String(length=64), nullable=False),
        sa.Column("scope_connector", sa.String(length=32), nullable=True),
        sa.Column("scope_resource_type", sa.String(length=64), nullable=True),
        sa.Column("scope_source_identity_key", sa.String(length=255), nullable=True),
        sa.Column("window_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("trust_state_impact", sa.String(length=64), nullable=False),
        sa.Column("recoverability_class", sa.String(length=64), nullable=False),
        sa.Column("recovery_status", sa.String(length=64), nullable=False),
        sa.Column("last_validation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("detail", pg.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("gap_id"),
    )
    op.create_index(
        "ix_raw_memory_failure_cases_tenant_failure_class",
        "raw_memory_failure_cases",
        ["tenant_id", "failure_class"],
        unique=False,
    )
    op.create_index(
        "ix_raw_memory_failure_cases_tenant_active",
        "raw_memory_failure_cases",
        ["tenant_id", "active"],
        unique=False,
    )

    op.create_table(
        "raw_memory_recovery_validations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("apply_repairs", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("detail", pg.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_raw_memory_recovery_validations_tenant_created",
        "raw_memory_recovery_validations",
        ["tenant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_raw_memory_recovery_validations_tenant_created",
        table_name="raw_memory_recovery_validations",
    )
    op.drop_table("raw_memory_recovery_validations")
    op.drop_index("ix_raw_memory_failure_cases_tenant_active", table_name="raw_memory_failure_cases")
    op.drop_index("ix_raw_memory_failure_cases_tenant_failure_class", table_name="raw_memory_failure_cases")
    op.drop_table("raw_memory_failure_cases")
