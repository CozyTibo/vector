"""Cortex Phase 04 Step 8 — org link half-open validity CHECK on cortex_org_links.

Revision ID: 20260510_0056
Revises: 20260510_0055
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260510_0056"
down_revision: Union[str, None] = "20260510_0055"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_cortex_org_links_valid_half_open",
        "cortex_org_links",
        "(valid_from IS NULL OR valid_to IS NULL OR valid_from < valid_to)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_cortex_org_links_valid_half_open", "cortex_org_links", type_="check")
