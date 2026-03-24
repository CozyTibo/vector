"""Nullable password_hash for local auth.

Revision ID: 20260326_0003
Revises: 20260325_0002
Create Date: 2026-03-26

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260326_0003"
down_revision: Union[str, None] = "20260325_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "password_hash")
