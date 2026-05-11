"""Cortex Phase 03 Step 5 — mapping bundle registry, pins, compatibility, changelog.

Revision ID: 20260508_0039
Revises: 20260508_0038
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260508_0039"
down_revision: Union[str, None] = "20260508_0038"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Aligned with `oracle_manifest.PHASE03_STEP03_*` and operator seed.
_STUB_BUNDLE_ID = "bundle.phase03.step03.logical_keys.v1"
_STUB_MANIFEST_HASH = "sha256:0000000000000000000000000000000000000000000000000000000000000000"


def upgrade() -> None:
    op.create_table(
        "cortex_mapping_bundles",
        sa.Column("bundle_id", sa.String(length=256), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False),
        sa.Column("manifest_hash", sa.String(length=128), nullable=False),
        sa.Column("owner_team", sa.String(length=256), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("predecessor_bundle_id", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["predecessor_bundle_id"], ["cortex_mapping_bundles.bundle_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("bundle_id"),
    )
    op.create_index("ix_cortex_mapping_bundles_lifecycle_state", "cortex_mapping_bundles", ["lifecycle_state"])

    op.create_table(
        "cortex_mapping_bundle_changelog",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("bundle_id", sa.String(length=256), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("breaking_classification", sa.String(length=32), nullable=False),
        sa.Column(
            "artifact_delta",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "oracle_vector_refs",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "compatibility_edges_delta",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "invalidation_scope",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "ci_report_refs",
            pg.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["bundle_id"], ["cortex_mapping_bundles.bundle_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bundle_id", "sequence_number", name="uq_cortex_mapping_bundle_changelog_seq"),
    )
    op.create_index("ix_cortex_mapping_bundle_changelog_bundle_id", "cortex_mapping_bundle_changelog", ["bundle_id"])

    op.create_table(
        "cortex_mapping_bundle_compatibility",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("from_bundle_id", sa.String(length=256), nullable=False),
        sa.Column("to_bundle_id", sa.String(length=256), nullable=False),
        sa.Column("edge_kind", sa.String(length=32), nullable=False),
        sa.Column("is_breaking", sa.Boolean(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("declared_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["from_bundle_id"], ["cortex_mapping_bundles.bundle_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_bundle_id"], ["cortex_mapping_bundles.bundle_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cortex_mapping_bundle_compat_from",
        "cortex_mapping_bundle_compatibility",
        ["from_bundle_id"],
    )
    op.create_index(
        "ix_cortex_mapping_bundle_compat_to",
        "cortex_mapping_bundle_compatibility",
        ["to_bundle_id"],
    )

    op.create_table(
        "cortex_mapping_bundle_pins",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("bundle_id", sa.String(length=256), nullable=False),
        sa.Column("scope_kind", sa.String(length=64), nullable=False),
        sa.Column("scope_marker", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("effective_from", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("policy_reference", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bundle_id"], ["cortex_mapping_bundles.bundle_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cortex_mapping_bundle_pins_tenant_id", "cortex_mapping_bundle_pins", ["tenant_id"])
    op.create_index("ix_cortex_mapping_bundle_pins_bundle_id", "cortex_mapping_bundle_pins", ["bundle_id"])
    op.create_index(
        "uq_cortex_mapping_bundle_pins_scope",
        "cortex_mapping_bundle_pins",
        ["tenant_id", "scope_kind", "scope_marker"],
        unique=True,
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO cortex_mapping_bundles (
              bundle_id, lifecycle_state, manifest_hash, owner_team, title, notes
            ) VALUES (
              :bid,
              'approved',
              :mh,
              'cortex-platform',
              'Phase 03 stub logical-keys bundle',
              :notes
            )
            """
        ),
        {
            "bid": _STUB_BUNDLE_ID,
            "mh": _STUB_MANIFEST_HASH,
            "notes": (
                "Seeded registry row for Step 5; artifact bodies are placeholders until mapping runtime (Step 6)."
            ),
        },
    )

    conn.execute(
        sa.text(
            """
            INSERT INTO cortex_mapping_bundle_changelog (
              bundle_id, sequence_number, summary, breaking_classification, artifact_delta
            ) VALUES (
              :bid,
              1,
              :summary,
              'documentation_only',
              CAST(:artifact_delta AS jsonb)
            )
            """
        ),
        {
            "bid": _STUB_BUNDLE_ID,
            "summary": "Initial bundle registration — aligns oracle manifest stub bundle id + manifest hash.",
            "artifact_delta": '{"tables": [], "note": "No mapping artifacts materialized yet"}',
        },
    )


def downgrade() -> None:
    op.drop_index("uq_cortex_mapping_bundle_pins_scope", table_name="cortex_mapping_bundle_pins")
    op.drop_index("ix_cortex_mapping_bundle_pins_bundle_id", table_name="cortex_mapping_bundle_pins")
    op.drop_index("ix_cortex_mapping_bundle_pins_tenant_id", table_name="cortex_mapping_bundle_pins")
    op.drop_table("cortex_mapping_bundle_pins")

    op.drop_index("ix_cortex_mapping_bundle_compat_to", table_name="cortex_mapping_bundle_compatibility")
    op.drop_index("ix_cortex_mapping_bundle_compat_from", table_name="cortex_mapping_bundle_compatibility")
    op.drop_table("cortex_mapping_bundle_compatibility")

    op.drop_index("ix_cortex_mapping_bundle_changelog_bundle_id", table_name="cortex_mapping_bundle_changelog")
    op.drop_table("cortex_mapping_bundle_changelog")

    op.drop_index("ix_cortex_mapping_bundles_lifecycle_state", table_name="cortex_mapping_bundles")
    op.drop_table("cortex_mapping_bundles")
