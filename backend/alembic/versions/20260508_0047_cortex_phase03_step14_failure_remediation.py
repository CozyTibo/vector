"""Cortex Phase 03 Step 14 — canonical failure cases + remediation validation ledger.

Revision ID: 20260508_0047
Revises: 20260508_0046
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260508_0047"
down_revision: Union[str, None] = "20260508_0046"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_canonical_failure_cases",
        sa.Column("gap_id", sa.String(length=128), nullable=False),
        sa.Column(
            "tenant_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("failure_class", sa.String(length=64), nullable=False),
        sa.Column("degradation_state", sa.String(length=32), nullable=False),
        sa.Column("scope_kind", sa.String(length=64), nullable=False),
        sa.Column("scope_json", pg.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("detail_json", pg.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.PrimaryKeyConstraint("gap_id"),
    )
    op.create_index(
        "ix_cortex_canonical_failure_cases_tenant_active_created",
        "cortex_canonical_failure_cases",
        ["tenant_id", "active", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_cortex_canonical_failure_cases_tenant_class",
        "cortex_canonical_failure_cases",
        ["tenant_id", "failure_class"],
        unique=False,
    )

    op.create_table(
        "cortex_canonical_remediation_validations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "tenant_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "failure_case_gap_id",
            sa.String(length=128),
            sa.ForeignKey("cortex_canonical_failure_cases.gap_id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("remediation_class", sa.String(length=64), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("confirm_execution", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "payload_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("result_status", sa.String(length=32), nullable=False),
        sa.Column(
            "result_detail_json",
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
        "ix_cortex_canonical_remediation_validations_tenant_created",
        "cortex_canonical_remediation_validations",
        ["tenant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cortex_canonical_remediation_validations_tenant_created",
        table_name="cortex_canonical_remediation_validations",
    )
    op.drop_table("cortex_canonical_remediation_validations")
    op.drop_index("ix_cortex_canonical_failure_cases_tenant_class", table_name="cortex_canonical_failure_cases")
    op.drop_index(
        "ix_cortex_canonical_failure_cases_tenant_active_created",
        table_name="cortex_canonical_failure_cases",
    )
    op.drop_table("cortex_canonical_failure_cases")
