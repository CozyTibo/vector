"""github_commits.repo_full_name for readability / queries.

Revision ID: 20260402_0010
Revises: 20260401_0009
Create Date: 2026-04-02

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260402_0010"
down_revision: Union[str, None] = "20260401_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "github_commits",
        sa.Column("repo_full_name", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("github_commits", "repo_full_name")
