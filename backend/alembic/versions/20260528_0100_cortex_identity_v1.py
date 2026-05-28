"""Cortex identity v1 tables.

Revision ID: 20260528_0100
Revises: 20260528_0099
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260528_0100"
down_revision: Union[str, None] = "20260528_0099"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "identity_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="unknown"),
        sa.Column("display_name", sa.String(length=512), nullable=False),
        sa.Column("primary_email", sa.String(length=320), nullable=True),
        sa.Column("resolver_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("merged_into_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["merged_into_id"], ["identity_entities.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_identity_entities_tenant_id", "identity_entities", ["tenant_id"])

    op.create_table(
        "identity_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identity_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canon_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector", sa.String(length=32), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("link_tier", sa.String(length=16), nullable=False, server_default="seed"),
        sa.Column("link_rule", sa.String(length=64), nullable=False, server_default="seed_actor"),
        sa.Column("confidence", sa.String(length=16), nullable=False, server_default="low"),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("unlinked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["identity_entity_id"], ["identity_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["canon_entity_id"], ["canon_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["connection_id"], ["tenant_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "canon_entity_id", name="uq_identity_accounts_tenant_canon_entity"),
    )
    op.create_index("ix_identity_accounts_tenant_id", "identity_accounts", ["tenant_id"])
    op.create_index("ix_identity_accounts_identity_entity_id", "identity_accounts", ["identity_entity_id"])
    op.create_index("ix_identity_accounts_canon_entity_id", "identity_accounts", ["canon_entity_id"])

    op.create_table(
        "identity_pass_runs",
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
    op.create_index("ix_identity_pass_runs_tenant_id", "identity_pass_runs", ["tenant_id"])

    op.create_table(
        "identity_dirty_queue",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canon_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("enqueued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
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
            name="uq_identity_dirty_tenant_entity_processed",
        ),
    )
    op.create_index(
        "ix_identity_dirty_queue_tenant_unprocessed",
        "identity_dirty_queue",
        ["tenant_id"],
        postgresql_where=sa.text("processed_at IS NULL"),
    )
    op.create_index("ix_identity_dirty_queue_entity_id", "identity_dirty_queue", ["canon_entity_id"])

    op.create_table(
        "identity_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("left_canon_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("right_canon_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.String(length=16), nullable=False, server_default="suggestion"),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="open"),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["left_canon_entity_id"], ["canon_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["right_canon_entity_id"], ["canon_entities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_identity_suggestions_tenant_id", "identity_suggestions", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_identity_suggestions_tenant_id", table_name="identity_suggestions")
    op.drop_table("identity_suggestions")
    op.drop_index("ix_identity_dirty_queue_entity_id", table_name="identity_dirty_queue")
    op.drop_index("ix_identity_dirty_queue_tenant_unprocessed", table_name="identity_dirty_queue")
    op.drop_table("identity_dirty_queue")
    op.drop_index("ix_identity_pass_runs_tenant_id", table_name="identity_pass_runs")
    op.drop_table("identity_pass_runs")
    op.drop_index("ix_identity_accounts_canon_entity_id", table_name="identity_accounts")
    op.drop_index("ix_identity_accounts_identity_entity_id", table_name="identity_accounts")
    op.drop_index("ix_identity_accounts_tenant_id", table_name="identity_accounts")
    op.drop_table("identity_accounts")
    op.drop_index("ix_identity_entities_tenant_id", table_name="identity_entities")
    op.drop_table("identity_entities")

