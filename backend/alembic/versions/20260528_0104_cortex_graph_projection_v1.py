"""Cortex graph projection v1 — relationships, dirty queue, pass runs, scheduler ticks.

Revision ID: 20260528_0104
Revises: 20260528_0103
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260528_0104"
down_revision = "20260528_0103"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "graph_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_kind", sa.String(length=64), nullable=False),
        sa.Column("from_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_identity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("to_identity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("identity_resolver_version_at_enrich", sa.Integer(), nullable=True),
        sa.Column("direction", sa.String(length=16), nullable=False, server_default="directed"),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("extractor_version", sa.Integer(), nullable=False),
        sa.Column("extractor_rule", sa.String(length=128), nullable=False),
        sa.Column("evidence_kind", sa.String(length=64), nullable=False),
        sa.Column("evidence_ref", sa.String(length=256), nullable=False),
        sa.Column("evidence_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_raw_id", sa.BigInteger(), nullable=True),
        sa.Column("source_canon_source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("superseded_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_entity_id"], ["canon_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_entity_id"], ["canon_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["from_identity_id"], ["identity_entities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["to_identity_id"], ["identity_entities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_raw_id"], ["raw_ingestion_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["source_canon_source_id"],
            ["canon_entity_sources.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["graph_relationships.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_graph_relationships_tenant_id", "graph_relationships", ["tenant_id"])
    op.create_index("ix_graph_relationships_status", "graph_relationships", ["status"])
    op.create_index(
        "ix_graph_relationships_from_entity",
        "graph_relationships",
        ["tenant_id", "from_entity_id"],
    )
    op.create_index(
        "ix_graph_relationships_to_entity",
        "graph_relationships",
        ["tenant_id", "to_entity_id"],
    )
    op.execute(
        """
        CREATE UNIQUE INDEX ux_graph_relationships_active_edge
        ON graph_relationships (
            tenant_id,
            relationship_kind,
            from_entity_id,
            to_entity_id,
            extractor_rule
        )
        WHERE status = 'active'
        """
    )

    op.create_table(
        "graph_dirty_queue",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canon_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column(
            "enqueued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["canon_entity_id"], ["canon_entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "canon_entity_id",
            "processed_at",
            name="uq_graph_dirty_tenant_entity_processed",
        ),
    )
    op.create_index("ix_graph_dirty_queue_tenant_id", "graph_dirty_queue", ["tenant_id"])
    op.create_index(
        "ix_graph_dirty_queue_canon_entity_id",
        "graph_dirty_queue",
        ["canon_entity_id"],
    )

    op.create_table(
        "graph_pass_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_trigger", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_graph_pass_runs_tenant_id", "graph_pass_runs", ["tenant_id"])

    op.create_table(
        "graph_scheduler_ticks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("enqueued_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candidate_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("beat_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("skip_reason", sa.String(length=128), nullable=True),
        sa.Column("enqueued_tenant_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_graph_scheduler_ticks_started_at",
        "graph_scheduler_ticks",
        ["started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_graph_scheduler_ticks_started_at", table_name="graph_scheduler_ticks")
    op.drop_table("graph_scheduler_ticks")
    op.drop_index("ix_graph_pass_runs_tenant_id", table_name="graph_pass_runs")
    op.drop_table("graph_pass_runs")
    op.drop_index("ix_graph_dirty_queue_canon_entity_id", table_name="graph_dirty_queue")
    op.drop_index("ix_graph_dirty_queue_tenant_id", table_name="graph_dirty_queue")
    op.drop_table("graph_dirty_queue")
    op.execute("DROP INDEX IF EXISTS ux_graph_relationships_active_edge")
    op.drop_index("ix_graph_relationships_to_entity", table_name="graph_relationships")
    op.drop_index("ix_graph_relationships_from_entity", table_name="graph_relationships")
    op.drop_index("ix_graph_relationships_status", table_name="graph_relationships")
    op.drop_index("ix_graph_relationships_tenant_id", table_name="graph_relationships")
    op.drop_table("graph_relationships")
