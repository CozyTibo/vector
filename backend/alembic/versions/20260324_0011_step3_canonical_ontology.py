"""Step 3: canonical ontology (actors, artifacts, relationships, mapping).

Revision ID: 20260324_0011
Revises: 20260402_0010
Create Date: 2026-03-24

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260324_0011"
down_revision: Union[str, None] = "20260402_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "artifact_kind",
        sa.Column("id", sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_container", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_artifact_kind_name"),
    )

    op.create_table(
        "relation_kind",
        sa.Column("id", sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("subject_kind", sa.Text(), nullable=False),
        sa.Column("object_kind", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_relation_kind_name"),
        sa.CheckConstraint(
            "subject_kind IN ('actor', 'artifact')",
            name="ck_relation_kind_subject_kind",
        ),
        sa.CheckConstraint(
            "object_kind IN ('actor', 'artifact')",
            name="ck_relation_kind_object_kind",
        ),
    )

    op.create_table(
        "actor",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False, server_default=sa.text("'person'")),
        sa.Column("display_name", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_actor_tenant_id", "actor", ["tenant_id"], unique=False)

    op.create_table(
        "actor_external_identity",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connector", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("traits_json", pg.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["actor.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "connector",
            "external_id",
            name="uq_actor_external_identity_tenant_connector_ext",
        ),
    )
    op.create_index(
        "ix_actor_external_identity_actor",
        "actor_external_identity",
        ["actor_id"],
        unique=False,
    )

    op.create_table(
        "artifact",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_kind_id", sa.SmallInteger(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["artifact_kind_id"], ["artifact_kind.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_artifact_tenant_kind", "artifact", ["tenant_id", "artifact_kind_id"])

    op.create_table(
        "artifact_repository",
        sa.Column("artifact_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_github_id", sa.BigInteger(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifact.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("artifact_id"),
    )

    op.create_table(
        "artifact_trackable_unit",
        sa.Column("artifact_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False, server_default=sa.text("'github'")),
        sa.Column("key", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("repository_github_id", sa.BigInteger(), nullable=True),
        sa.Column("issue_number", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifact.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("artifact_id"),
    )

    op.create_table(
        "artifact_changeset",
        sa.Column("artifact_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_github_id", sa.BigInteger(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("head_sha", sa.Text(), nullable=True),
        sa.Column("repo_full_name", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifact.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("artifact_id"),
    )

    op.create_table(
        "artifact_revision",
        sa.Column("artifact_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_github_id", sa.BigInteger(), nullable=False),
        sa.Column("sha", sa.Text(), nullable=False),
        sa.Column("repo_full_name", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifact.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("artifact_id"),
    )

    op.create_table(
        "external_reference",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connector", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=True),
        sa.Column("external_key", sa.Text(), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("last_raw_record_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "connector",
            "external_key",
            name="uq_external_reference_tenant_connector_key",
        ),
    )
    op.create_index(
        "ix_external_reference_tenant_conn",
        "external_reference",
        ["tenant_id", "connection_id"],
        unique=False,
    )

    op.create_table(
        "mapping_event",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("external_reference_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("rule_version", sa.Text(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_hash", sa.Text(), nullable=True),
        sa.Column("supersedes_event_id", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["artifact.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["actor.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["external_reference_id"],
            ["external_reference.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "(artifact_id IS NOT NULL)::int + (actor_id IS NOT NULL)::int = 1",
            name="ck_mapping_event_single_target",
        ),
    )
    op.create_index(
        "ix_mapping_event_external_ref_time",
        "mapping_event",
        ["external_reference_id", "effective_at", "id"],
        unique=False,
    )
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_mapping_event_dedup ON mapping_event "
            "(external_reference_id, rule_version, payload_hash) "
            "WHERE payload_hash IS NOT NULL",
        ),
    )

    op.create_table(
        "current_mapping",
        sa.Column("external_reference_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["artifact_id"],
            ["artifact.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["actor.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["external_reference_id"],
            ["external_reference.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("external_reference_id"),
        sa.CheckConstraint(
            "(artifact_id IS NOT NULL)::int + (actor_id IS NOT NULL)::int = 1",
            name="ck_current_mapping_single_target",
        ),
    )

    op.create_table(
        "relationship",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_type", sa.Text(), nullable=False),
        sa.Column("subject_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("object_type", sa.Text(), nullable=False),
        sa.Column("object_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_kind_id", sa.SmallInteger(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("evidence_ref", sa.Text(), nullable=True),
        sa.Column("rule_version", sa.Text(), nullable=True),
        sa.Column("rule_source", sa.Text(), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["relation_kind_id"], ["relation_kind.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "subject_type IN ('actor', 'artifact')",
            name="ck_relationship_subject_type",
        ),
        sa.CheckConstraint(
            "object_type IN ('actor', 'artifact')",
            name="ck_relationship_object_type",
        ),
    )
    op.create_index(
        "ix_relationship_subject",
        "relationship",
        ["tenant_id", "subject_type", "subject_id"],
        unique=False,
    )
    op.create_index(
        "ix_relationship_object",
        "relationship",
        ["tenant_id", "object_type", "object_id"],
        unique=False,
    )
    op.create_index(
        "ix_relationship_current",
        "relationship",
        ["tenant_id", "relation_kind_id"],
        unique=False,
        postgresql_where=sa.text("valid_to IS NULL"),
    )

    op.create_table(
        "step3_canonical_cursor",
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connector", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("last_replay_sequence", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_raw_record_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "last_processed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("connection_id", "connector"),
    )
    op.create_index(
        "ix_step3_canonical_cursor_tenant",
        "step3_canonical_cursor",
        ["tenant_id", "connection_id", "connector"],
        unique=False,
    )

    # Seed registries (stable ids for code references)
    op.execute(
        sa.text("""
        INSERT INTO artifact_kind (id, name, description, is_container) VALUES
        (1, 'repository', 'VCS repository / project root', true),
        (2, 'trackable_unit', 'Issue, ticket, or work item', false),
        (3, 'changeset', 'Pull request / merge request', false),
        (4, 'revision', 'Commit or immutable revision', false)
        ON CONFLICT (name) DO NOTHING
        """)
    )
    op.execute(
        sa.text("""
        INSERT INTO relation_kind (id, name, description, subject_kind, object_kind) VALUES
        (1, 'authored_by', 'Actor created or opened the artifact', 'actor', 'artifact'),
        (2, 'associated_with', 'Loose association between artifacts', 'artifact', 'artifact')
        ON CONFLICT (name) DO NOTHING
        """)
    )
    op.execute(
        sa.text(
            "SELECT setval(pg_get_serial_sequence('artifact_kind', 'id'), "
            "(SELECT COALESCE(MAX(id), 1) FROM artifact_kind))",
        ),
    )
    op.execute(
        sa.text(
            "SELECT setval(pg_get_serial_sequence('relation_kind', 'id'), "
            "(SELECT COALESCE(MAX(id), 1) FROM relation_kind))",
        ),
    )


def downgrade() -> None:
    op.drop_index("ix_step3_canonical_cursor_tenant", table_name="step3_canonical_cursor")
    op.drop_table("step3_canonical_cursor")

    op.drop_index("ix_relationship_current", table_name="relationship")
    op.drop_index("ix_relationship_object", table_name="relationship")
    op.drop_index("ix_relationship_subject", table_name="relationship")
    op.drop_table("relationship")

    op.drop_table("current_mapping")

    op.execute(sa.text("DROP INDEX IF EXISTS uq_mapping_event_dedup"))
    op.drop_index("ix_mapping_event_external_ref_time", table_name="mapping_event")
    op.drop_table("mapping_event")

    op.drop_index("ix_external_reference_tenant_conn", table_name="external_reference")
    op.drop_table("external_reference")

    op.drop_table("artifact_revision")
    op.drop_table("artifact_changeset")
    op.drop_table("artifact_trackable_unit")
    op.drop_table("artifact_repository")

    op.drop_index("ix_artifact_tenant_kind", table_name="artifact")
    op.drop_table("artifact")

    op.drop_index("ix_actor_external_identity_actor", table_name="actor_external_identity")
    op.drop_table("actor_external_identity")

    op.drop_index("ix_actor_tenant_id", table_name="actor")
    op.drop_table("actor")

    op.drop_table("relation_kind")
    op.drop_table("artifact_kind")
