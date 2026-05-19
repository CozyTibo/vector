"""Explicit canonical materialization deferrals (topology wait, forward progress).

Revision ID: 20260519_0087
Revises: 20260519_0086
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260519_0087"
down_revision: Union[str, None] = "20260519_0086"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_canonical_materialization_deferrals",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_id", sa.String(length=256), nullable=False),
        sa.Column("raw_record_id", sa.BigInteger(), nullable=False),
        sa.Column("connector", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=128), nullable=False),
        sa.Column("deferral_reason", sa.String(length=64), nullable=False),
        sa.Column("queue", sa.String(length=64), nullable=False),
        sa.Column("parent_raw_record_id", sa.BigInteger(), nullable=True),
        sa.Column("missing_parent_ref", sa.Text(), nullable=True),
        sa.Column("pass_key", sa.String(length=128), nullable=True),
        sa.Column(
            "retry_ready_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "deferred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "detail_json",
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tenant_id", "bundle_id", "raw_record_id"),
    )
    op.create_index(
        "ix_cortex_canon_mat_def_tenant_bundle_retry",
        "cortex_canonical_materialization_deferrals",
        ["tenant_id", "bundle_id", "retry_ready_at"],
    )
    op.create_index(
        "ix_cortex_canon_mat_def_tenant_bundle_pass",
        "cortex_canonical_materialization_deferrals",
        ["tenant_id", "bundle_id", "pass_key"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cortex_canon_mat_def_tenant_bundle_pass",
        table_name="cortex_canonical_materialization_deferrals",
    )
    op.drop_index(
        "ix_cortex_canon_mat_def_tenant_bundle_retry",
        table_name="cortex_canonical_materialization_deferrals",
    )
    op.drop_table("cortex_canonical_materialization_deferrals")
