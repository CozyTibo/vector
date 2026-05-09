"""Cortex Phase 03 Step 11 — canonical provenance records (raw↔canonical forward index + derivation envelope).

Revision ID: 20260508_0045
Revises: 20260508_0044
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260508_0045"
down_revision: Union[str, None] = "20260508_0044"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_canonical_provenance_records",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "materialization_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("cortex_canonical_transform_materializations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "bundle_id",
            sa.String(length=256),
            sa.ForeignKey("cortex_mapping_bundles.bundle_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "raw_record_id",
            sa.BigInteger(),
            sa.ForeignKey("raw_ingestion_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("canonical_object_kind", sa.String(length=128), nullable=False),
        sa.Column("logical_key_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "evidence_shape",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'1:1'"),
        ),
        sa.Column("primary_raw_record_ids", pg.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rule_ids_involved", pg.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("derivation_json", pg.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "parent_materialization_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("cortex_canonical_transform_materializations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("materialization_id", name="uq_cortex_canonical_provenance_mat"),
    )
    op.create_index(
        "ix_cortex_canonical_provenance_tenant_raw",
        "cortex_canonical_provenance_records",
        ["tenant_id", "raw_record_id"],
        unique=False,
    )
    op.create_index(
        "ix_cortex_canonical_provenance_tenant_bundle_lk",
        "cortex_canonical_provenance_records",
        ["tenant_id", "bundle_id", "logical_key_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cortex_canonical_provenance_tenant_bundle_lk", table_name="cortex_canonical_provenance_records")
    op.drop_index("ix_cortex_canonical_provenance_tenant_raw", table_name="cortex_canonical_provenance_records")
    op.drop_table("cortex_canonical_provenance_records")
