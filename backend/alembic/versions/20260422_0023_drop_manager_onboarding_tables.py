"""Drop manager Slack onboarding tables (feature removed).

Revision ID: 20260422_0023
Revises: 20260416_0022
Create Date: 2026-04-22

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import text

revision: str = "20260422_0023"
down_revision: Union[str, None] = "20260416_0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Some DBs still have tables that FK to manager_onboarding_sessions but are not in this
    # repo's Alembic history (e.g. older local/test schemas).
    for _legacy in ("manager_onboarding_events", "execution_onboarding_states"):
        op.execute(text(f'DROP TABLE IF EXISTS "{_legacy}" CASCADE'))

    # Order matches reverse of 20260410_0019_manager_slack_onboarding: children before sessions.
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


def downgrade() -> None:
    msg = (
        "Cannot downgrade: manager onboarding schema was removed. "
        "Restore a DB backup or re-apply revision 20260410_0019 (and 20260411_0020 for `muted`) manually."
    )
    raise NotImplementedError(msg)
