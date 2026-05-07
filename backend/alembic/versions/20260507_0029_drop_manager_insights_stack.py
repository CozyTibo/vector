"""Drop legacy manager insights tables.

Revision ID: 20260507_0029
Revises: 20260507_0028
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260507_0029"
down_revision: Union[str, None] = "20260507_0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_MANAGER_INSIGHT_TABLES: tuple[str, ...] = (
    "manager_insight_outcomes",
    "manager_insight_policy_counters",
    "manager_insight_decisions",
)


def upgrade() -> None:
    # Keep this idempotent for safe rollout on environments where these tables may already be absent.
    for table in _MANAGER_INSIGHT_TABLES:
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')


def downgrade() -> None:
    msg = (
        "Irreversible migration: manager insights tables were dropped. "
        "Restore from backup/snapshot if rollback is required."
    )
    raise RuntimeError(msg)
