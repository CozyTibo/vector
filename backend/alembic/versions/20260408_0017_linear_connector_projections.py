"""Step 2: Linear connector projections.

Revision ID: 20260408_0017
Revises: 20260407_0016
Create Date: 2026-04-08

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260408_0017"
down_revision: Union[str, None] = "20260407_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "linear_users",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("linear_user_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.Column("guest", sa.Boolean(), nullable=True),
        sa.Column("admin", sa.Boolean(), nullable=True),
        sa.Column("last_raw_record_id", sa.Integer(), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_replay_sequence", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("connection_id", "linear_user_id"),
    )
    op.create_index(
        "ix_linear_users_tenant_conn",
        "linear_users",
        ["tenant_id", "connection_id"],
        unique=False,
    )

    op.create_table(
        "linear_teams",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("linear_team_id", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("private", sa.Boolean(), nullable=True),
        sa.Column("last_raw_record_id", sa.Integer(), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_replay_sequence", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("connection_id", "linear_team_id"),
    )
    op.create_index(
        "ix_linear_teams_tenant_conn",
        "linear_teams",
        ["tenant_id", "connection_id"],
        unique=False,
    )

    op.create_table(
        "linear_projects",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("linear_project_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("slug", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("last_raw_record_id", sa.Integer(), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_replay_sequence", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("connection_id", "linear_project_id"),
    )
    op.create_index(
        "ix_linear_projects_tenant_conn",
        "linear_projects",
        ["tenant_id", "connection_id"],
        unique=False,
    )

    op.create_table(
        "linear_issues",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("linear_issue_id", sa.Text(), nullable=False),
        sa.Column("identifier", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("estimate", sa.Float(), nullable=True),
        sa.Column("state_id", sa.Text(), nullable=True),
        sa.Column("state_name", sa.Text(), nullable=True),
        sa.Column("state_type", sa.Text(), nullable=True),
        sa.Column("team_id", sa.Text(), nullable=True),
        sa.Column("assignee_id", sa.Text(), nullable=True),
        sa.Column("creator_id", sa.Text(), nullable=True),
        sa.Column("project_id", sa.Text(), nullable=True),
        sa.Column("parent_issue_id", sa.Text(), nullable=True),
        sa.Column("cycle_id", sa.Text(), nullable=True),
        sa.Column("labels_json", pg.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_raw_record_id", sa.Integer(), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_replay_sequence", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("connection_id", "linear_issue_id"),
    )
    op.create_index(
        "ix_linear_issues_tenant_conn",
        "linear_issues",
        ["tenant_id", "connection_id"],
        unique=False,
    )

    op.create_table(
        "linear_issue_comments",
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("connection_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("linear_comment_id", sa.Text(), nullable=False),
        sa.Column("linear_issue_id", sa.Text(), nullable=True),
        sa.Column("issue_identifier", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_raw_record_id", sa.Integer(), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_replay_sequence", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("connection_id", "linear_comment_id"),
    )
    op.create_index(
        "ix_linear_issue_comments_tenant_conn",
        "linear_issue_comments",
        ["tenant_id", "connection_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_linear_issue_comments_tenant_conn", table_name="linear_issue_comments")
    op.drop_table("linear_issue_comments")
    op.drop_index("ix_linear_issues_tenant_conn", table_name="linear_issues")
    op.drop_table("linear_issues")
    op.drop_index("ix_linear_projects_tenant_conn", table_name="linear_projects")
    op.drop_table("linear_projects")
    op.drop_index("ix_linear_teams_tenant_conn", table_name="linear_teams")
    op.drop_table("linear_teams")
    op.drop_index("ix_linear_users_tenant_conn", table_name="linear_users")
    op.drop_table("linear_users")
