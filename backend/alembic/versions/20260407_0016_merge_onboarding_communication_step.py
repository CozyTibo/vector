"""Merge CONNECT_SLACK + CONNECT_COMM into CONNECT_COMMUNICATION.

Revision ID: 20260407_0016
Revises: 20260406_0015
Create Date: 2026-04-07

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260407_0016"
down_revision: Union[str, None] = "20260406_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE onboarding_state
        SET current_step = 'CONNECT_COMMUNICATION'
        WHERE current_step IN ('CONNECT_SLACK', 'CONNECT_COMM')
        """
    )


def downgrade() -> None:
    # Cannot reliably split again; map combined step back to Slack-oriented id.
    op.execute(
        """
        UPDATE onboarding_state
        SET current_step = 'CONNECT_SLACK'
        WHERE current_step = 'CONNECT_COMMUNICATION'
        """
    )
