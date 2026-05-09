"""Cortex Phase 03 Step 6 — canonical transform materializations + field lineage.

Revision ID: 20260508_0040
Revises: 20260508_0039
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260508_0040"
down_revision: Union[str, None] = "20260508_0039"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_canonical_transform_materializations",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_id", sa.String(length=256), nullable=False),
        sa.Column("raw_record_id", sa.BigInteger(), nullable=False),
        sa.Column("canonical_object_kind", sa.String(length=128), nullable=False),
        sa.Column("logical_key_json", pg.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("logical_key_hash", sa.String(length=128), nullable=False),
        sa.Column("emitted_snapshot_json", pg.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("emitted_snapshot_hash", sa.String(length=128), nullable=False),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["bundle_id"], ["cortex_mapping_bundles.bundle_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["raw_record_id"], ["raw_ingestion_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "bundle_id",
            "raw_record_id",
            name="uq_cortex_canonical_transform_mat_scope",
        ),
    )
    op.create_index(
        "ix_cortex_canonical_transform_mat_tenant_created",
        "cortex_canonical_transform_materializations",
        ["tenant_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "cortex_canonical_field_lineage",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("materialization_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("field_path", sa.String(length=512), nullable=False),
        sa.Column("rule_id", sa.String(length=256), nullable=False),
        sa.Column("evidence_grade", sa.String(length=8), nullable=False),
        sa.Column(
            "source_paths",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("value_snapshot", pg.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["materialization_id"],
            ["cortex_canonical_transform_materializations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cortex_canonical_field_lineage_materialization_id",
        "cortex_canonical_field_lineage",
        ["materialization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cortex_canonical_field_lineage_materialization_id", table_name="cortex_canonical_field_lineage")
    op.drop_table("cortex_canonical_field_lineage")
    op.drop_index(
        "ix_cortex_canonical_transform_mat_tenant_created",
        table_name="cortex_canonical_transform_materializations",
    )
    op.drop_table("cortex_canonical_transform_materializations")
