"""Cortex Phase 04 Step 9 — bundle equivalence declarations (cross-bundle org continuity).

Revision ID: 20260510_0057
Revises: 20260510_0056
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260510_0057"
down_revision: Union[str, None] = "20260510_0056"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_P04_STUB_BUNDLE_B = "bundle.phase04.step09.equivalence.b.v1"
_P04_STUB_MANIFEST = "sha256:0000000000000000000000000000000000000000000000000000000000000001"


def upgrade() -> None:
    op.create_table(
        "cortex_bundle_equivalence_declarations",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("left_bundle_id", sa.String(length=256), nullable=False),
        sa.Column("right_bundle_id", sa.String(length=256), nullable=False),
        sa.Column("replay_ordinal", sa.Integer(), nullable=False),
        sa.Column(
            "evidence_raw_record_ids",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "metadata_json",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("engine_build_ref", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "left_bundle_id < right_bundle_id",
            name="ck_cortex_bundle_eq_pair_ordered",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["left_bundle_id"], ["cortex_mapping_bundles.bundle_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["right_bundle_id"], ["cortex_mapping_bundles.bundle_id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_cortex_bundle_eq_decl_tenant",
        "cortex_bundle_equivalence_declarations",
        ["tenant_id"],
    )
    op.create_index(
        "ix_cortex_bundle_eq_decl_tenant_replay_ord",
        "cortex_bundle_equivalence_declarations",
        ["tenant_id", "replay_ordinal"],
    )
    op.create_index(
        "uq_cortex_bundle_eq_decl_active_pair",
        "cortex_bundle_equivalence_declarations",
        ["tenant_id", "left_bundle_id", "right_bundle_id"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO cortex_mapping_bundles (
              bundle_id, lifecycle_state, manifest_hash, owner_team, title, notes
            )
            SELECT CAST(:bid AS VARCHAR(256)), 'approved', CAST(:mh AS VARCHAR(128)), 'cortex-platform',
                   'Phase 04 Step 9 stub bundle B',
                   'Second registry row for cross-bundle equivalence tests.'
            WHERE NOT EXISTS (SELECT 1 FROM cortex_mapping_bundles WHERE bundle_id = CAST(:bid AS VARCHAR(256)))
            """
        ),
        {"bid": _P04_STUB_BUNDLE_B, "mh": _P04_STUB_MANIFEST},
    )


def downgrade() -> None:
    op.drop_index("uq_cortex_bundle_eq_decl_active_pair", table_name="cortex_bundle_equivalence_declarations")
    op.drop_index("ix_cortex_bundle_eq_decl_tenant_replay_ord", table_name="cortex_bundle_equivalence_declarations")
    op.drop_index("ix_cortex_bundle_eq_decl_tenant", table_name="cortex_bundle_equivalence_declarations")
    op.drop_table("cortex_bundle_equivalence_declarations")
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM cortex_mapping_bundles WHERE bundle_id = :bid"),
        {"bid": _P04_STUB_BUNDLE_B},
    )
