"""Manager Slack onboarding tables (sessions, messages, invitations, channels).

Revision ID: 20260410_0019
Revises: 20260409_0018
Create Date: 2026-04-10

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260410_0019"
down_revision: Union[str, None] = "20260409_0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "manager_onboarding_sessions",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("slack_team_id", sa.String(length=32), nullable=False),
        sa.Column("slack_user_id", sa.String(length=32), nullable=False),
        sa.Column("app_user_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("parent_session_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_step", sa.String(length=64), nullable=False),
        sa.Column("answers_json", pg.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("context_json", pg.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("timezone_source", sa.String(length=32), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["app_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_session_id"], ["manager_onboarding_sessions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_manager_ob_sessions_tenant_status",
        "manager_onboarding_sessions",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_manager_ob_sessions_team_user",
        "manager_onboarding_sessions",
        ["slack_team_id", "slack_user_id"],
    )
    op.create_index(
        "uq_manager_ob_sessions_tenant_slack_user",
        "manager_onboarding_sessions",
        ["tenant_id", "slack_user_id"],
        unique=True,
    )

    op.create_table(
        "manager_onboarding_messages",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("slack_channel_id", sa.String(length=32), nullable=True),
        sa.Column("slack_ts", sa.String(length=32), nullable=True),
        sa.Column("thread_ts", sa.String(length=32), nullable=True),
        sa.Column("slack_event_id", sa.String(length=64), nullable=True),
        sa.Column("ingestion_kind", sa.String(length=24), nullable=False, server_default="message"),
        sa.Column("outbound_idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("parse_artifact_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["session_id"], ["manager_onboarding_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_manager_ob_messages_session_created",
        "manager_onboarding_messages",
        ["session_id", "created_at"],
    )
    op.create_index(
        "uq_manager_ob_messages_slack_event_id",
        "manager_onboarding_messages",
        ["slack_event_id"],
        unique=True,
        postgresql_where=sa.text("slack_event_id IS NOT NULL"),
    )
    op.create_index(
        "uq_manager_ob_messages_outbound_idem",
        "manager_onboarding_messages",
        ["outbound_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("outbound_idempotency_key IS NOT NULL"),
    )

    op.create_table(
        "manager_onboarding_parse_artifacts",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger", sa.String(length=32), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("structured_output_json", pg.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("token_usage", sa.Integer(), nullable=True),
        sa.Column("fallback_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["session_id"], ["manager_onboarding_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_manager_ob_parse_session",
        "manager_onboarding_parse_artifacts",
        ["session_id", "created_at"],
    )

    op.create_table(
        "manager_onboarding_invitations",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("inviter_session_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("invitee_slack_user_id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("invitation_dm_ts", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["inviter_session_id"], ["manager_onboarding_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_manager_ob_invites_tenant",
        "manager_onboarding_invitations",
        ["tenant_id"],
    )

    op.create_table(
        "manager_onboarding_channel_observations",
        sa.Column("id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("slack_channel_id", sa.String(length=32), nullable=False),
        sa.Column("channel_name", sa.String(length=255), nullable=True),
        sa.Column("access_status", sa.String(length=32), nullable=False),
        sa.Column("bot_is_member", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("history_readable", sa.Boolean(), nullable=True),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validation_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["manager_onboarding_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_manager_ob_ch_obs_session",
        "manager_onboarding_channel_observations",
        ["session_id"],
    )

    op.create_table(
        "manager_onboarding_slack_event_dedup",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )


def downgrade() -> None:
    op.drop_table("manager_onboarding_slack_event_dedup")
    op.drop_index("ix_manager_ob_ch_obs_session", table_name="manager_onboarding_channel_observations")
    op.drop_table("manager_onboarding_channel_observations")
    op.drop_index("ix_manager_ob_invites_tenant", table_name="manager_onboarding_invitations")
    op.drop_table("manager_onboarding_invitations")
    op.drop_index("ix_manager_ob_parse_session", table_name="manager_onboarding_parse_artifacts")
    op.drop_table("manager_onboarding_parse_artifacts")
    op.drop_index("uq_manager_ob_messages_outbound_idem", table_name="manager_onboarding_messages")
    op.drop_index("uq_manager_ob_messages_slack_event_id", table_name="manager_onboarding_messages")
    op.drop_index("ix_manager_ob_messages_session_created", table_name="manager_onboarding_messages")
    op.drop_table("manager_onboarding_messages")
    op.drop_index("uq_manager_ob_sessions_tenant_slack_user", table_name="manager_onboarding_sessions")
    op.drop_index("ix_manager_ob_sessions_team_user", table_name="manager_onboarding_sessions")
    op.drop_index("ix_manager_ob_sessions_tenant_status", table_name="manager_onboarding_sessions")
    op.drop_table("manager_onboarding_sessions")
