"""Cortex Phase 03 Step 7 — ambiguity persistence + append-only lifecycle log.

Revision ID: 20260508_0041
Revises: 20260508_0040
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260508_0041"
down_revision: Union[str, None] = "20260508_0040"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_canonical_ambiguity_records",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_id", sa.String(length=256), nullable=False),
        sa.Column("ambiguity_class", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=512), nullable=False),
        sa.Column("record_handle", sa.String(length=256), nullable=True),
        sa.Column(
            "raw_record_ids",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "rule_ids_involved",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("primary_connector", sa.String(length=64), nullable=True),
        sa.Column("primary_resource_type", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supersession_note", sa.Text(), nullable=True),
        sa.Column("superseded_by_ambiguity_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "evidence_payload",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["bundle_id"], ["cortex_mapping_bundles.bundle_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["superseded_by_ambiguity_id"],
            ["cortex_canonical_ambiguity_records.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cortex_ambiguity_records_tenant_status",
        "cortex_canonical_ambiguity_records",
        ["tenant_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_cortex_ambiguity_records_tenant_class",
        "cortex_canonical_ambiguity_records",
        ["tenant_id", "ambiguity_class"],
        unique=False,
    )
    op.create_index(
        "ix_cortex_ambiguity_records_tenant_connector_resource",
        "cortex_canonical_ambiguity_records",
        ["tenant_id", "primary_connector", "primary_resource_type"],
        unique=False,
    )
    op.create_index(
        "uq_cortex_ambiguity_tenant_record_handle",
        "cortex_canonical_ambiguity_records",
        ["tenant_id", "record_handle"],
        unique=True,
        postgresql_where=sa.text("record_handle IS NOT NULL"),
    )

    op.create_table(
        "cortex_canonical_ambiguity_lifecycle_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ambiguity_record_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("event_kind", sa.String(length=64), nullable=False),
        sa.Column("previous_status", sa.String(length=64), nullable=True),
        sa.Column("new_status", sa.String(length=64), nullable=False),
        sa.Column(
            "payload",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["ambiguity_record_id"],
            ["cortex_canonical_ambiguity_records.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cortex_ambiguity_lifecycle_ambiguity_id",
        "cortex_canonical_ambiguity_lifecycle_events",
        ["ambiguity_record_id"],
        unique=False,
    )
    op.create_index(
        "ix_cortex_ambiguity_lifecycle_tenant_created",
        "cortex_canonical_ambiguity_lifecycle_events",
        ["tenant_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cortex_ambiguity_lifecycle_tenant_created",
        table_name="cortex_canonical_ambiguity_lifecycle_events",
    )
    op.drop_index(
        "ix_cortex_ambiguity_lifecycle_ambiguity_id",
        table_name="cortex_canonical_ambiguity_lifecycle_events",
    )
    op.drop_table("cortex_canonical_ambiguity_lifecycle_events")
    op.drop_index("uq_cortex_ambiguity_tenant_record_handle", table_name="cortex_canonical_ambiguity_records")
    op.drop_index(
        "ix_cortex_ambiguity_records_tenant_connector_resource",
        table_name="cortex_canonical_ambiguity_records",
    )
    op.drop_index("ix_cortex_ambiguity_records_tenant_class", table_name="cortex_canonical_ambiguity_records")
    op.drop_index("ix_cortex_ambiguity_records_tenant_status", table_name="cortex_canonical_ambiguity_records")
    op.drop_table("cortex_canonical_ambiguity_records")
