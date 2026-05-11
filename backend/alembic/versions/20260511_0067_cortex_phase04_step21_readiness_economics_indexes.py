"""Cortex Phase 04 Step 21 — readiness economics probe indexes (P04-21).

Revision ID: 20260511_0067
Revises: 20260511_0066
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260511_0067"
down_revision: Union[str, None] = "20260511_0066"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_cortex_org_link_candidates_tenant_created",
        "cortex_org_link_candidates",
        ["tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_cortex_org_link_replay_jobs_tenant_status_created",
        "cortex_org_link_replay_jobs",
        ["tenant_id", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cortex_org_link_replay_jobs_tenant_status_created", table_name="cortex_org_link_replay_jobs")
    op.drop_index("ix_cortex_org_link_candidates_tenant_created", table_name="cortex_org_link_candidates")
