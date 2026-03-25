"""Step 2: GitHub connector projections + raw ingestion worker index.

Revision ID: 20260401_0009
Revises: 20260331_0008
Create Date: 2026-04-01

- Projection tables: github_* + connector_projection_progress
- Index on raw_ingestion_records (connection_id, connector, replay_sequence, id)

Note: raw_ingestion_records.connector already exists (Step 1 migration).

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260401_0009"
down_revision: Union[str, None] = "20260331_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_raw_ingestion_records_conn_connector_replay",
        "raw_ingestion_records",
        ["connection_id", "connector", "replay_sequence", "id"],
        unique=False,
    )

    op.create_table(
        "connector_projection_progress",
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connector", sa.String(length=32), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("last_replay_sequence", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_id", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("lock_owner", sa.String(length=128), nullable=True),
        sa.Column("lock_expires_at", sa.DateTime(timezone=True), nullable=True),
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
        "ix_connector_projection_progress_tenant_conn",
        "connector_projection_progress",
        ["tenant_id", "connection_id", "connector"],
        unique=False,
    )

    op.create_table(
        "github_repositories",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_github_id", sa.BigInteger(), nullable=False),
        sa.Column("node_id", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("full_name", sa.Text(), nullable=True),
        sa.Column("owner_login", sa.Text(), nullable=True),
        sa.Column("owner_github_id", sa.BigInteger(), nullable=True),
        sa.Column("private", sa.Boolean(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_branch", sa.Text(), nullable=True),
        sa.Column("html_url", sa.Text(), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=True),
        sa.Column("disabled", sa.Boolean(), nullable=True),
        sa.Column("fork", sa.Boolean(), nullable=True),
        sa.Column("pushed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("github_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("github_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_raw_record_id", sa.BigInteger(), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_replay_sequence", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("connection_id", "repository_github_id"),
    )
    op.create_index(
        "ix_github_repositories_tenant_conn",
        "github_repositories",
        ["tenant_id", "connection_id"],
        unique=False,
    )

    op.create_table(
        "github_pull_requests",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_github_id", sa.BigInteger(), nullable=False),
        sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column("pull_request_github_id", sa.BigInteger(), nullable=True),
        sa.Column("node_id", sa.Text(), nullable=True),
        sa.Column("repo_full_name", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("draft", sa.Boolean(), nullable=True),
        sa.Column("author_github_id", sa.BigInteger(), nullable=True),
        sa.Column("author_login", sa.Text(), nullable=True),
        sa.Column("head_sha", sa.Text(), nullable=True),
        sa.Column("head_ref", sa.Text(), nullable=True),
        sa.Column("base_sha", sa.Text(), nullable=True),
        sa.Column("base_ref", sa.Text(), nullable=True),
        sa.Column("html_url", sa.Text(), nullable=True),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("github_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("github_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_raw_record_id", sa.BigInteger(), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_replay_sequence", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("connection_id", "repository_github_id", "pr_number"),
    )
    op.create_index(
        "ix_github_pull_requests_tenant_conn",
        "github_pull_requests",
        ["tenant_id", "connection_id"],
        unique=False,
    )
    op.create_index(
        "ix_github_pull_requests_tenant_conn_state",
        "github_pull_requests",
        ["tenant_id", "connection_id", "state"],
        unique=False,
    )

    op.create_table(
        "github_issues",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_github_id", sa.BigInteger(), nullable=False),
        sa.Column("issue_number", sa.Integer(), nullable=False),
        sa.Column("issue_github_id", sa.BigInteger(), nullable=True),
        sa.Column("node_id", sa.Text(), nullable=True),
        sa.Column("repo_full_name", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("author_github_id", sa.BigInteger(), nullable=True),
        sa.Column("author_login", sa.Text(), nullable=True),
        sa.Column("html_url", sa.Text(), nullable=True),
        sa.Column("locked", sa.Boolean(), nullable=True),
        sa.Column("github_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("github_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_raw_record_id", sa.BigInteger(), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_replay_sequence", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("connection_id", "repository_github_id", "issue_number"),
    )
    op.create_index(
        "ix_github_issues_tenant_conn",
        "github_issues",
        ["tenant_id", "connection_id"],
        unique=False,
    )

    op.create_table(
        "github_commits",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("repository_github_id", sa.BigInteger(), nullable=False),
        sa.Column("commit_sha", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("author_name", sa.Text(), nullable=True),
        sa.Column("author_email", sa.Text(), nullable=True),
        sa.Column("author_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("committer_name", sa.Text(), nullable=True),
        sa.Column("committer_email", sa.Text(), nullable=True),
        sa.Column("committer_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("author_github_id", sa.BigInteger(), nullable=True),
        sa.Column("committer_github_id", sa.BigInteger(), nullable=True),
        sa.Column("html_url", sa.Text(), nullable=True),
        sa.Column("parents_json", pg.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_raw_record_id", sa.BigInteger(), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_replay_sequence", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("connection_id", "repository_github_id", "commit_sha"),
    )
    op.create_index(
        "ix_github_commits_tenant_conn_repo",
        "github_commits",
        ["tenant_id", "connection_id", "repository_github_id"],
        unique=False,
    )

    op.create_table(
        "github_users",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("github_id", sa.BigInteger(), nullable=False),
        sa.Column("login", sa.Text(), nullable=True),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("html_url", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("site_admin", sa.Boolean(), nullable=True),
        sa.Column("last_raw_record_id", sa.BigInteger(), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_replay_sequence", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("connection_id", "github_id"),
    )
    op.create_index(
        "ix_github_users_tenant_conn",
        "github_users",
        ["tenant_id", "connection_id"],
        unique=False,
    )
    op.create_index(
        "ix_github_users_tenant_conn_login",
        "github_users",
        ["tenant_id", "connection_id", "login"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_github_users_tenant_conn_login", table_name="github_users")
    op.drop_index("ix_github_users_tenant_conn", table_name="github_users")
    op.drop_table("github_users")

    op.drop_index("ix_github_commits_tenant_conn_repo", table_name="github_commits")
    op.drop_table("github_commits")

    op.drop_index("ix_github_issues_tenant_conn", table_name="github_issues")
    op.drop_table("github_issues")

    op.drop_index("ix_github_pull_requests_tenant_conn_state", table_name="github_pull_requests")
    op.drop_index("ix_github_pull_requests_tenant_conn", table_name="github_pull_requests")
    op.drop_table("github_pull_requests")

    op.drop_index("ix_github_repositories_tenant_conn", table_name="github_repositories")
    op.drop_table("github_repositories")

    op.drop_index("ix_connector_projection_progress_tenant_conn", table_name="connector_projection_progress")
    op.drop_table("connector_projection_progress")

    op.drop_index("ix_raw_ingestion_records_conn_connector_replay", table_name="raw_ingestion_records")
