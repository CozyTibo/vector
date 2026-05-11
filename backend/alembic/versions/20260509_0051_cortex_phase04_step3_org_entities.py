"""Cortex Phase 04 Step 3 — org entity (org handle) registry.

Revision ID: 20260509_0051
Revises: 20260508_0050
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260509_0051"
down_revision: Union[str, None] = "20260508_0050"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_org_entities",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_kind", sa.String(length=64), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False, server_default=sa.text("'active'")),
        sa.Column("superseded_by_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("identity_key_fingerprint", sa.String(length=128), nullable=False),
        sa.Column(
            "metadata_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
        sa.Column("tombstoned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["cortex_org_entities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cortex_org_entities_tenant_kind",
        "cortex_org_entities",
        ["tenant_id", "entity_kind"],
        unique=False,
    )
    op.create_index(
        "ix_cortex_org_entities_tenant_created",
        "cortex_org_entities",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "uq_cortex_org_entity_fingerprint",
        "cortex_org_entities",
        ["tenant_id", "entity_kind", "identity_key_fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_cortex_org_entity_fingerprint", table_name="cortex_org_entities")
    op.drop_index("ix_cortex_org_entities_tenant_created", table_name="cortex_org_entities")
    op.drop_index("ix_cortex_org_entities_tenant_kind", table_name="cortex_org_entities")
    op.drop_table("cortex_org_entities")
