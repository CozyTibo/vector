"""Cortex Phase 03 Step 9 — canonical identity anchors + Phase 04 boundary hooks.

Revision ID: 20260508_0043
Revises: 20260508_0042
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260508_0043"
down_revision: Union[str, None] = "20260508_0042"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_canonical_identity_anchors",
        sa.Column("canonical_entity_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_id", sa.String(length=256), nullable=False),
        sa.Column("canonical_object_kind", sa.String(length=128), nullable=False),
        sa.Column("provider_identity_hash", sa.String(length=128), nullable=False),
        sa.Column("provider_identity_json", pg.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("logical_key_hash", sa.String(length=128), nullable=False),
        sa.Column("materialization_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("raw_record_id", sa.BigInteger(), nullable=False),
        sa.Column("connector", sa.String(length=64), nullable=False),
        sa.Column(
            "phase04_boundary_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["bundle_id"], ["cortex_mapping_bundles.bundle_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["materialization_id"], ["cortex_canonical_transform_materializations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["raw_record_id"], ["raw_ingestion_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("canonical_entity_id"),
    )
    op.create_index(
        "ix_cortex_identity_anchors_tenant_updated",
        "cortex_canonical_identity_anchors",
        ["tenant_id", "updated_at"],
        unique=False,
    )
    op.create_index(
        "uq_cortex_identity_provider_scope",
        "cortex_canonical_identity_anchors",
        ["tenant_id", "bundle_id", "canonical_object_kind", "provider_identity_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_cortex_identity_provider_scope", table_name="cortex_canonical_identity_anchors")
    op.drop_index("ix_cortex_identity_anchors_tenant_updated", table_name="cortex_canonical_identity_anchors")
    op.drop_table("cortex_canonical_identity_anchors")
