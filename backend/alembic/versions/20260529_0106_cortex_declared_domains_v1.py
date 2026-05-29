"""Cortex declared domains v1 — domains, memberships, stats, dirty queue, pass runs.

Revision ID: 20260529_0106
Revises: 20260528_0105
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260529_0106"
down_revision = "20260528_0105"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "declared_domains",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.String(length=512), nullable=False),
        sa.Column("declared_container_kind", sa.String(length=64), nullable=False),
        sa.Column("seed_canon_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seed_connector", sa.String(length=32), nullable=False),
        sa.Column("seed_resource_type", sa.String(length=64), nullable=False),
        sa.Column("extractor_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seed_canon_entity_id"], ["canon_entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("seed_canon_entity_id"),
    )
    op.create_index("ix_declared_domains_tenant_id", "declared_domains", ["tenant_id"])
    op.create_index(
        "ix_declared_domains_tenant_kind",
        "declared_domains",
        ["tenant_id", "declared_container_kind"],
    )

    op.create_table(
        "declared_domain_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("declared_domain_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canon_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("extractor_version", sa.Integer(), nullable=False),
        sa.Column("extractor_rule", sa.String(length=128), nullable=False),
        sa.Column("expansion_level", sa.String(length=16), nullable=False),
        sa.Column("evidence_kind", sa.String(length=64), nullable=False),
        sa.Column("evidence_ref", sa.String(length=256), nullable=False),
        sa.Column("seed_distance", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["declared_domain_id"], ["declared_domains.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["canon_entity_id"], ["canon_entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_declared_domain_memberships_tenant_id",
        "declared_domain_memberships",
        ["tenant_id"],
    )
    op.create_index(
        "ix_declared_domain_memberships_domain_id",
        "declared_domain_memberships",
        ["declared_domain_id"],
    )
    op.create_index(
        "ix_declared_domain_memberships_canon_entity_id",
        "declared_domain_memberships",
        ["canon_entity_id"],
    )
    op.execute(
        """
        CREATE UNIQUE INDEX ux_declared_domain_memberships_active
        ON declared_domain_memberships (
            tenant_id,
            declared_domain_id,
            canon_entity_id,
            extractor_rule
        )
        WHERE status = 'active'
        """
    )

    op.create_table(
        "declared_domain_stats",
        sa.Column("declared_domain_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "artifact_counts_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("participant_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("events_7d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("events_prior_7d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("activity_delta_7d", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("momentum_pct", sa.Numeric(12, 2), nullable=True),
        sa.Column("mass_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "expansion_level",
            sa.String(length=32),
            nullable=False,
            server_default="direct",
        ),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["declared_domain_id"], ["declared_domains.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("declared_domain_id"),
    )
    op.create_index("ix_declared_domain_stats_tenant_id", "declared_domain_stats", ["tenant_id"])

    op.create_table(
        "declared_domain_dirty_queue",
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
            name="uq_declared_domain_dirty_tenant_entity_processed",
        ),
    )
    op.create_index(
        "ix_declared_domain_dirty_queue_tenant_id",
        "declared_domain_dirty_queue",
        ["tenant_id"],
    )
    op.create_index(
        "ix_declared_domain_dirty_queue_canon_entity_id",
        "declared_domain_dirty_queue",
        ["canon_entity_id"],
    )

    op.create_table(
        "declared_domain_pass_runs",
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
    op.create_index(
        "ix_declared_domain_pass_runs_tenant_id",
        "declared_domain_pass_runs",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_declared_domain_pass_runs_tenant_id", table_name="declared_domain_pass_runs")
    op.drop_table("declared_domain_pass_runs")
    op.drop_index(
        "ix_declared_domain_dirty_queue_canon_entity_id",
        table_name="declared_domain_dirty_queue",
    )
    op.drop_index("ix_declared_domain_dirty_queue_tenant_id", table_name="declared_domain_dirty_queue")
    op.drop_table("declared_domain_dirty_queue")
    op.drop_index("ix_declared_domain_stats_tenant_id", table_name="declared_domain_stats")
    op.drop_table("declared_domain_stats")
    op.execute("DROP INDEX IF EXISTS ux_declared_domain_memberships_active")
    op.drop_index(
        "ix_declared_domain_memberships_canon_entity_id",
        table_name="declared_domain_memberships",
    )
    op.drop_index(
        "ix_declared_domain_memberships_domain_id",
        table_name="declared_domain_memberships",
    )
    op.drop_index(
        "ix_declared_domain_memberships_tenant_id",
        table_name="declared_domain_memberships",
    )
    op.drop_table("declared_domain_memberships")
    op.drop_index("ix_declared_domains_tenant_kind", table_name="declared_domains")
    op.drop_index("ix_declared_domains_tenant_id", table_name="declared_domains")
    op.drop_table("declared_domains")
