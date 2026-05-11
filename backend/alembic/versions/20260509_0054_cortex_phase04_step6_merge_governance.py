"""Cortex Phase 04 Step 6 — merge governance policies + append-only merge ledger.

Revision ID: 20260509_0054
Revises: 20260509_0053
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260509_0054"
down_revision: Union[str, None] = "20260509_0053"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_org_merge_policies",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_ref", sa.String(length=256), nullable=False),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cortex_org_merge_policies_tenant",
        "cortex_org_merge_policies",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "cortex_org_merges",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("merge_kind", sa.String(length=64), nullable=False),
        sa.Column("merge_policy_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "source_entity_ids",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("target_entity_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "evidence_raw_record_ids",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("operator_user_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("supersedes_merge_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "metadata_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(merge_kind <> 'human_actor_merge') OR ("
            "jsonb_typeof(source_entity_ids) = 'array' AND jsonb_array_length(source_entity_ids) >= 2 AND "
            "jsonb_typeof(evidence_raw_record_ids) = 'array' AND jsonb_array_length(evidence_raw_record_ids) >= 2 AND "
            "operator_user_id IS NOT NULL)",
            name="ck_cortex_org_merges_human_actor_evidence_operator",
        ),
        sa.CheckConstraint(
            "(merge_kind <> 'compensating_merge') OR (supersedes_merge_id IS NOT NULL)",
            name="ck_cortex_org_merges_compensating_requires_supersedes",
        ),
        sa.CheckConstraint(
            "(merge_kind NOT IN ('team_merge', 'service_split')) OR ("
            "jsonb_typeof(evidence_raw_record_ids) = 'array' AND jsonb_array_length(evidence_raw_record_ids) >= 1)",
            name="ck_cortex_org_merges_team_service_evidence",
        ),
        sa.ForeignKeyConstraint(["merge_policy_id"], ["cortex_org_merge_policies.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operator_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supersedes_merge_id"], ["cortex_org_merges.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["cortex_org_entities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cortex_org_merges_tenant_created",
        "cortex_org_merges",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_cortex_org_merges_tenant_kind",
        "cortex_org_merges",
        ["tenant_id", "merge_kind"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cortex_org_merges_tenant_kind", table_name="cortex_org_merges")
    op.drop_index("ix_cortex_org_merges_tenant_created", table_name="cortex_org_merges")
    op.drop_table("cortex_org_merges")
    op.drop_index("ix_cortex_org_merge_policies_tenant", table_name="cortex_org_merge_policies")
    op.drop_table("cortex_org_merge_policies")
