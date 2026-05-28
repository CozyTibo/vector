"""graph_unresolved_references — deterministic text refs that did not resolve.

Revision ID: 20260528_0105
Revises: 20260528_0104
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260528_0105"
down_revision = "20260528_0104"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "graph_unresolved_references",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_raw_id", sa.BigInteger(), nullable=True),
        sa.Column("reference_kind", sa.String(length=64), nullable=False),
        sa.Column("reference_text", sa.String(length=512), nullable=False),
        sa.Column("extractor_rule", sa.String(length=128), nullable=False),
        sa.Column("evidence_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="unresolved"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_entity_id"], ["canon_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_raw_id"], ["raw_ingestion_records.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_graph_unresolved_refs_tenant",
        "graph_unresolved_references",
        ["tenant_id"],
    )
    op.create_index(
        "ix_graph_unresolved_refs_source_entity",
        "graph_unresolved_references",
        ["source_entity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_graph_unresolved_refs_source_entity", table_name="graph_unresolved_references")
    op.drop_index("ix_graph_unresolved_refs_tenant", table_name="graph_unresolved_references")
    op.drop_table("graph_unresolved_references")
