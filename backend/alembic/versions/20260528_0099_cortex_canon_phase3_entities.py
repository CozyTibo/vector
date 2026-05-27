"""Cortex canon v1 phase 3 — entities, sources, dirty queue.

Revision ID: 20260528_0099
Revises: 20260528_0098
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260528_0099"
down_revision: Union[str, None] = "20260528_0098"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "canon_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector", sa.String(length=32), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_key", sa.String(length=512), nullable=False),
        sa.Column("display_label", sa.String(length=512), nullable=False),
        sa.Column("attrs_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("mapper_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("materialized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("author_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("conversation_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parent_message_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("repository_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assignee_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parent_document_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("work_item_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["connection_id"], ["tenant_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "entity_type",
            "entity_key",
            name="uq_canon_entities_tenant_type_key",
        ),
    )
    op.create_index("ix_canon_entities_tenant_id", "canon_entities", ["tenant_id"])
    op.create_index("ix_canon_entities_entity_type", "canon_entities", ["entity_type"])

    op.create_table(
        "canon_entity_sources",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("canon_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_id", sa.BigInteger(), nullable=False),
        sa.Column("connector", sa.String(length=32), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=512), nullable=False),
        sa.Column("source_identity_key", sa.String(length=255), nullable=False),
        sa.Column("source_revision_key", sa.String(length=128), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_latest", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("mapper_version", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(["canon_entity_id"], ["canon_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raw_id"], ["raw_ingestion_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "canon_entity_id",
            "source_revision_key",
            "mapper_version",
            name="uq_canon_entity_sources_entity_revision_mapper",
        ),
    )
    op.create_index("ix_canon_entity_sources_raw_id", "canon_entity_sources", ["raw_id"])

    op.create_table(
        "canon_dirty_queue",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_identity_key", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("enqueued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["connection_id"], ["tenant_connections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_canon_dirty_queue_tenant_unprocessed",
        "canon_dirty_queue",
        ["tenant_id"],
        postgresql_where=sa.text("processed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_canon_dirty_queue_tenant_unprocessed", table_name="canon_dirty_queue")
    op.drop_table("canon_dirty_queue")
    op.drop_index("ix_canon_entity_sources_raw_id", table_name="canon_entity_sources")
    op.drop_table("canon_entity_sources")
    op.drop_index("ix_canon_entities_entity_type", table_name="canon_entities")
    op.drop_index("ix_canon_entities_tenant_id", table_name="canon_entities")
    op.drop_table("canon_entities")
