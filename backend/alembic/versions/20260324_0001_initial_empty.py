"""Initial revision (empty schema).

Revision ID: 20260324_0001
Revises:
Create Date: 2026-03-24

"""

from collections.abc import Sequence
from typing import Union

revision: str = "20260324_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
