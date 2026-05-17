"""Cortex Phase 07 Step 22 — retrieval query audit trail.

Revision ID: 20260516_0072
Revises: 20260516_0071
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260516_0072"
down_revision: Union[str, None] = "20260516_0071"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_retrieval_query_audit",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_digest", sa.String(length=128), nullable=False),
        sa.Column("operator_user_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("query_envelope_hash", sa.String(length=128), nullable=False),
        sa.Column("result_legality_class", sa.String(length=64), nullable=False),
        sa.Column("retrieval_query_replay_identity", sa.String(length=128), nullable=False),
        sa.Column("workload_class", sa.String(length=64), nullable=False),
        sa.Column("intent", sa.String(length=64), nullable=False),
        sa.Column("execution_partition", sa.String(length=32), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("omission_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
        sa.Column("policy_digest", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["operator_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_cortex_retrieval_query_audit_tenant_created",
        "cortex_retrieval_query_audit",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_cortex_retrieval_query_audit_tenant_receipt",
        "cortex_retrieval_query_audit",
        ["tenant_id", "receipt_digest"],
    )


def downgrade() -> None:
    op.drop_table("cortex_retrieval_query_audit")
