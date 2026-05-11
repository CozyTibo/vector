"""Cortex Phase 04 Step 11 — versioned linkage rule manifests (`cortex_link_rule_versions`).

Revision ID: 20260510_0059
Revises: 20260510_0058
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260510_0059"
down_revision: Union[str, None] = "20260510_0058"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_link_rule_versions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("semantic_version", sa.String(length=128), nullable=False),
        sa.Column(
            "rules_manifest_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("manifest_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "lifecycle_state",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "lifecycle_state IN ('active','deprecated')",
            name="ck_cortex_link_rule_versions_lifecycle",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_cortex_link_rule_versions_tenant",
        "cortex_link_rule_versions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_cortex_link_rule_versions_tenant_created",
        "cortex_link_rule_versions",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "uq_cortex_link_rule_versions_tenant_semantic_active",
        "cortex_link_rule_versions",
        ["tenant_id", "semantic_version"],
        unique=True,
        postgresql_where=sa.text("lifecycle_state = 'active'"),
    )

    op.add_column(
        "cortex_org_link_candidate_batches",
        sa.Column("link_rule_version_id", pg.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_cortex_org_link_candidate_batches_link_rule_version",
        "cortex_org_link_candidate_batches",
        "cortex_link_rule_versions",
        ["link_rule_version_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_cortex_org_link_candidate_batches_link_rule_version",
        "cortex_org_link_candidate_batches",
        ["link_rule_version_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cortex_org_link_candidate_batches_link_rule_version",
        table_name="cortex_org_link_candidate_batches",
    )
    op.drop_constraint(
        "fk_cortex_org_link_candidate_batches_link_rule_version",
        "cortex_org_link_candidate_batches",
        type_="foreignkey",
    )
    op.drop_column("cortex_org_link_candidate_batches", "link_rule_version_id")

    op.drop_index("uq_cortex_link_rule_versions_tenant_semantic_active", table_name="cortex_link_rule_versions")
    op.drop_index("ix_cortex_link_rule_versions_tenant_created", table_name="cortex_link_rule_versions")
    op.drop_index("ix_cortex_link_rule_versions_tenant", table_name="cortex_link_rule_versions")
    op.drop_table("cortex_link_rule_versions")
