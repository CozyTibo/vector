"""Cortex Phase 07 — durable OCTS walks, artifact lineage, retrieval index.

Revision ID: 20260516_0070
Revises: 20260516_0069
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260516_0070"
down_revision: Union[str, None] = "20260516_0069"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_octs_durable_walk_records",
        sa.Column("walk_id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "request_body",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("walk_payload", pg.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("job_id", sa.String(length=256), nullable=True),
        sa.Column("idempotency_key", sa.String(length=256), nullable=True),
        sa.Column("walk_hash", sa.String(length=128), nullable=True),
        sa.Column("traversal_receipt_digest", sa.String(length=128), nullable=True),
        sa.Column("traversal_epoch", sa.String(length=128), nullable=True),
        sa.Column("replay_identity", sa.String(length=128), nullable=True),
        sa.Column(
            "permutation_profile",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("continuity_proof_ref", sa.String(length=256), nullable=True),
        sa.Column(
            "frontier_boundaries",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("replay_legality_posture", sa.String(length=64), nullable=True),
        sa.Column(
            "degradation_classes",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("parent_walk_id", pg.UUID(as_uuid=True), nullable=True),
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
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_walk_id"],
            ["cortex_octs_durable_walk_records.walk_id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_cortex_octs_durable_walk_tenant",
        "cortex_octs_durable_walk_records",
        ["tenant_id"],
    )
    op.create_index(
        "ix_cortex_octs_durable_walk_tenant_status",
        "cortex_octs_durable_walk_records",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_cortex_octs_durable_walk_replay_identity",
        "cortex_octs_durable_walk_records",
        ["tenant_id", "replay_identity"],
    )
    op.create_index(
        "ix_cortex_octs_durable_walk_idem",
        "cortex_octs_durable_walk_records",
        ["tenant_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.create_table(
        "cortex_octs_traversal_receipts",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("walk_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_digest", sa.String(length=128), nullable=False),
        sa.Column("receipt_kind", sa.String(length=64), nullable=False),
        sa.Column(
            "body_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["walk_id"],
            ["cortex_octs_durable_walk_records.walk_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_cortex_octs_traversal_receipt_walk",
        "cortex_octs_traversal_receipts",
        ["walk_id"],
    )
    op.create_unique_constraint(
        "uq_cortex_octs_traversal_receipt_walk_kind",
        "cortex_octs_traversal_receipts",
        ["walk_id", "receipt_kind"],
    )

    op.create_table(
        "cortex_octs_traversal_replay_archive",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("walk_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("archive_digest", sa.String(length=128), nullable=False),
        sa.Column(
            "snapshot_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "archived_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["walk_id"],
            ["cortex_octs_durable_walk_records.walk_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_cortex_octs_traversal_archive_walk",
        "cortex_octs_traversal_replay_archive",
        ["walk_id"],
    )

    op.create_table(
        "cortex_artifact_lineage_edges",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("lineage_edge_id", sa.String(length=128), nullable=False),
        sa.Column("from_artifact_kind", sa.String(length=64), nullable=False),
        sa.Column("from_artifact_ref", sa.String(length=256), nullable=False),
        sa.Column("to_artifact_kind", sa.String(length=64), nullable=False),
        sa.Column("to_artifact_ref", sa.String(length=256), nullable=False),
        sa.Column("edge_kind", sa.String(length=64), nullable=False),
        sa.Column("replay_identity", sa.String(length=128), nullable=True),
        sa.Column(
            "degradation_propagation",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "omission_summary",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_cortex_artifact_lineage_tenant",
        "cortex_artifact_lineage_edges",
        ["tenant_id"],
    )
    op.create_unique_constraint(
        "uq_cortex_artifact_lineage_edge_id",
        "cortex_artifact_lineage_edges",
        ["tenant_id", "lineage_edge_id"],
    )

    op.create_table(
        "cortex_retrieval_index_entries",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("retrieval_lookup_id", sa.String(length=128), nullable=False),
        sa.Column("index_kind", sa.String(length=64), nullable=False),
        sa.Column("index_key", sa.String(length=256), nullable=False),
        sa.Column("replay_identity", sa.String(length=128), nullable=False),
        sa.Column("traversal_epoch", sa.String(length=128), nullable=True),
        sa.Column("chronology_legality_class", sa.String(length=64), nullable=False),
        sa.Column("causal_legality_class", sa.String(length=64), nullable=False),
        sa.Column("retrieval_legality_class", sa.String(length=64), nullable=False),
        sa.Column("degradation_posture", sa.String(length=64), nullable=False),
        sa.Column("continuity_posture", sa.String(length=64), nullable=False),
        sa.Column(
            "artifact_ref_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "omission_summary",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("retrieval_policy_digest", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_cortex_retrieval_index_tenant_kind",
        "cortex_retrieval_index_entries",
        ["tenant_id", "index_kind"],
    )
    op.create_unique_constraint(
        "uq_cortex_retrieval_index_lookup",
        "cortex_retrieval_index_entries",
        ["tenant_id", "retrieval_lookup_id"],
    )


def downgrade() -> None:
    op.drop_table("cortex_retrieval_index_entries")
    op.drop_table("cortex_artifact_lineage_edges")
    op.drop_table("cortex_octs_traversal_replay_archive")
    op.drop_table("cortex_octs_traversal_receipts")
    op.drop_table("cortex_octs_durable_walk_records")
