"""Cortex Phase 04 Step 4 — org link ledger (authoritative meaning links).

Revision ID: 20260509_0052
Revises: 20260509_0051
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260509_0052"
down_revision: Union[str, None] = "20260509_0051"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_org_links",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
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
        sa.Column("confidence_class", sa.String(length=64), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supersedes_link_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "link_authority",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'authoritative'"),
        ),
        sa.Column(
            "metadata_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(jsonb_typeof(evidence_raw_record_ids) = 'array' AND jsonb_array_length("
            "evidence_raw_record_ids) > 0) OR (rule_id IS NOT NULL AND btrim(rule_id) <> '')",
            name="ck_cortex_org_links_evidence_or_rule",
        ),
        sa.ForeignKeyConstraint(["source_entity_id"], ["cortex_org_entities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_link_id"], ["cortex_org_links.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_entity_id"], ["cortex_org_entities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cortex_org_links_tenant_created",
        "cortex_org_links",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_cortex_org_links_tenant_type_endpoints",
        "cortex_org_links",
        ["tenant_id", "link_type", "source_entity_id", "target_entity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cortex_org_links_tenant_type_endpoints", table_name="cortex_org_links")
    op.drop_index("ix_cortex_org_links_tenant_created", table_name="cortex_org_links")
    op.drop_table("cortex_org_links")
