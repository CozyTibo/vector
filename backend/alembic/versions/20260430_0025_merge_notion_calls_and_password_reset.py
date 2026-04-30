"""Merge notion/calls (20260427_0024) and password_reset_tokens (20260429_0024) branches."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

revision: str = "20260430_0025"
down_revision: Union[str, tuple[str, ...], None] = ("20260427_0024", "20260429_0024")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
