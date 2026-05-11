"""Cortex Phase 04 Step 5 — candidate batches, candidates, promotion policies, link promotion FKs.

Revision ID: 20260509_0053
Revises: 20260509_0052
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260509_0053"
down_revision: Union[str, None] = "20260509_0052"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_org_link_promotion_policies",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_ref", sa.String(length=256), nullable=False),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cortex_org_link_promotion_policies_tenant",
        "cortex_org_link_promotion_policies",
        ["tenant_id"],
        unique=False,
    )

    op.create_table(
        "cortex_org_link_candidate_batches",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_version", sa.String(length=128), nullable=False),
        sa.Column("candidate_set_sha256", sa.String(length=64), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cortex_org_link_candidate_batches_tenant_created",
        "cortex_org_link_candidate_batches",
        ["tenant_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "cortex_org_link_candidates",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("link_type", sa.String(length=128), nullable=False),
        sa.Column("source_entity_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("target_entity_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "evidence_raw_record_ids",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("rule_id", sa.String(length=256), nullable=True),
        sa.Column("row_digest", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["cortex_org_link_candidate_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_entity_id"], ["cortex_org_entities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["cortex_org_entities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cortex_org_link_candidates_tenant_batch",
        "cortex_org_link_candidates",
        ["tenant_id", "batch_id"],
        unique=False,
    )

    op.add_column(
        "cortex_org_links",
        sa.Column("promoted_from_candidate_id", pg.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "cortex_org_links",
        sa.Column("promotion_policy_id", pg.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cortex_org_links_promoted_candidate",
        "cortex_org_links",
        "cortex_org_link_candidates",
        ["promoted_from_candidate_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_cortex_org_links_promotion_policy",
        "cortex_org_links",
        "cortex_org_link_promotion_policies",
        ["promotion_policy_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_cortex_org_links_promotion_pairing",
        "cortex_org_links",
        "(promoted_from_candidate_id IS NULL AND promotion_policy_id IS NULL) OR "
        "(promoted_from_candidate_id IS NOT NULL AND promotion_policy_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_cortex_org_links_promotion_pairing", "cortex_org_links", type_="check")
    op.drop_constraint("fk_cortex_org_links_promotion_policy", "cortex_org_links", type_="foreignkey")
    op.drop_constraint("fk_cortex_org_links_promoted_candidate", "cortex_org_links", type_="foreignkey")
    op.drop_column("cortex_org_links", "promotion_policy_id")
    op.drop_column("cortex_org_links", "promoted_from_candidate_id")
    op.drop_index("ix_cortex_org_link_candidates_tenant_batch", table_name="cortex_org_link_candidates")
    op.drop_table("cortex_org_link_candidates")
    op.drop_index("ix_cortex_org_link_candidate_batches_tenant_created", table_name="cortex_org_link_candidate_batches")
    op.drop_table("cortex_org_link_candidate_batches")
    op.drop_index("ix_cortex_org_link_promotion_policies_tenant", table_name="cortex_org_link_promotion_policies")
    op.drop_table("cortex_org_link_promotion_policies")
