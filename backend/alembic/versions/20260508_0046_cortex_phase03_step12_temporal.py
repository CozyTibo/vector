"""Cortex Phase 03 Step 12 — temporal anchors + deterministic ordering + supersession ledger.

Revision ID: 20260508_0046
Revises: 20260508_0045
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260508_0046"
down_revision: Union[str, None] = "20260508_0045"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cortex_canonical_transform_materializations",
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "cortex_canonical_transform_materializations",
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "cortex_canonical_transform_materializations",
        sa.Column("canonical_processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "cortex_canonical_transform_materializations",
        sa.Column("source_revision_key", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "cortex_canonical_transform_materializations",
        sa.Column("temporal_ordering_key", sa.String(length=512), nullable=True),
    )
    op.create_index(
        "ix_cortex_canonical_transform_mat_temporal_order",
        "cortex_canonical_transform_materializations",
        ["tenant_id", "bundle_id", "temporal_ordering_key"],
        unique=False,
    )

    op.create_table(
        "cortex_canonical_temporal_supersessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
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
        sa.Column("predecessor_materialization_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("predecessor_logical_key_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "successor_materialization_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("cortex_canonical_transform_materializations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "causing_raw_record_id",
            sa.BigInteger(),
            sa.ForeignKey("raw_ingestion_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cortex_canonical_temporal_sup_tenant_created",
        "cortex_canonical_temporal_supersessions",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_cortex_canonical_temporal_sup_bundle",
        "cortex_canonical_temporal_supersessions",
        ["tenant_id", "bundle_id"],
        unique=False,
    )

    op.execute(
        """
        UPDATE cortex_canonical_transform_materializations m
        SET
            observed_at = r.fetched_at,
            occurred_at = r.fetched_at,
            canonical_processed_at = m.created_at,
            source_revision_key = r.source_revision_key
        FROM raw_ingestion_records r
        WHERE r.id = m.raw_record_id
          AND m.observed_at IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_cortex_canonical_temporal_sup_bundle", table_name="cortex_canonical_temporal_supersessions")
    op.drop_index("ix_cortex_canonical_temporal_sup_tenant_created", table_name="cortex_canonical_temporal_supersessions")
    op.drop_table("cortex_canonical_temporal_supersessions")
    op.drop_index("ix_cortex_canonical_transform_mat_temporal_order", table_name="cortex_canonical_transform_materializations")
    op.drop_column("cortex_canonical_transform_materializations", "temporal_ordering_key")
    op.drop_column("cortex_canonical_transform_materializations", "source_revision_key")
    op.drop_column("cortex_canonical_transform_materializations", "canonical_processed_at")
    op.drop_column("cortex_canonical_transform_materializations", "observed_at")
    op.drop_column("cortex_canonical_transform_materializations", "occurred_at")
