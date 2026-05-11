"""Cortex Phase 04 Step 14 — org-scoped ambiguity / multiplicity records (P04-14).

Revision ID: 20260510_0061
Revises: 20260510_0060
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260510_0061"
down_revision: Union[str, None] = "20260510_0060"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_org_ambiguity_records",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("org_ambiguity_class", sa.String(length=64), nullable=False),
        sa.Column("subject_key", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column(
            "involved_org_entity_ids",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "evidence_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("superseded_by_org_ambiguity_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("operator_note", sa.Text(), nullable=True),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
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
        sa.CheckConstraint(
            "status IN ('open','acknowledged','superseded','void')",
            name="ck_cortex_org_ambiguity_records_status",
        ),
        sa.CheckConstraint(
            (
                "jsonb_typeof(involved_org_entity_ids) = 'array' "
                "AND jsonb_array_length(COALESCE(involved_org_entity_ids, '[]'::jsonb)) >= 2"
            ),
            name="ck_cortex_org_ambiguity_records_involved_min_two",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["superseded_by_org_ambiguity_id"],
            ["cortex_org_ambiguity_records.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_cortex_org_ambiguity_records_tenant_status",
        "cortex_org_ambiguity_records",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_cortex_org_ambiguity_records_tenant_class",
        "cortex_org_ambiguity_records",
        ["tenant_id", "org_ambiguity_class"],
        unique=False,
    )
    op.create_index(
        "uq_cortex_org_ambiguity_records_tenant_subject_open",
        "cortex_org_ambiguity_records",
        ["tenant_id", "subject_key"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_cortex_org_ambiguity_records_tenant_subject_open",
        table_name="cortex_org_ambiguity_records",
    )
    op.drop_index("ix_cortex_org_ambiguity_records_tenant_class", table_name="cortex_org_ambiguity_records")
    op.drop_index("ix_cortex_org_ambiguity_records_tenant_status", table_name="cortex_org_ambiguity_records")
    op.drop_table("cortex_org_ambiguity_records")
