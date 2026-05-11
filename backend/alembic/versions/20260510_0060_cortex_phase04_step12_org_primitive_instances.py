"""Cortex Phase 04 Step 12 — org-scoped execution primitive instances (P04-12).

Revision ID: 20260510_0060
Revises: 20260510_0059
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260510_0060"
down_revision: Union[str, None] = "20260510_0059"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_org_primitive_instances",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("org_entity_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("primitive_kind", sa.String(length=64), nullable=False),
        sa.Column("primitive_key", sa.String(length=64), nullable=False),
        sa.Column(
            "envelope_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "lifecycle_state",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "lifecycle_state IN ('active','superseded','revoked')",
            name="ck_cortex_org_primitive_instances_lifecycle",
        ),
        sa.CheckConstraint(
            (
                "jsonb_typeof(envelope_json->'evidence_raw_record_ids') = 'array' "
                "AND jsonb_array_length(COALESCE(envelope_json->'evidence_raw_record_ids', '[]'::jsonb)) > 0"
            ),
            name="ck_cortex_org_primitive_instances_envelope_evidence_nonempty",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_entity_id"], ["cortex_org_entities.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "tenant_id",
            "primitive_key",
            name="uq_cortex_org_primitive_instances_tenant_primitive_key",
        ),
    )
    op.create_index(
        "ix_cortex_org_primitive_instances_tenant",
        "cortex_org_primitive_instances",
        ["tenant_id"],
    )
    op.create_index(
        "ix_cortex_org_primitive_instances_tenant_created",
        "cortex_org_primitive_instances",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_cortex_org_primitive_instances_org_entity",
        "cortex_org_primitive_instances",
        ["org_entity_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_cortex_org_primitive_instances_org_entity", table_name="cortex_org_primitive_instances")
    op.drop_index("ix_cortex_org_primitive_instances_tenant_created", table_name="cortex_org_primitive_instances")
    op.drop_index("ix_cortex_org_primitive_instances_tenant", table_name="cortex_org_primitive_instances")
    op.drop_table("cortex_org_primitive_instances")
