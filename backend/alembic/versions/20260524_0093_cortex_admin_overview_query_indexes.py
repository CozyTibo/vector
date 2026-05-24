"""Admin cortex overview — index revision (no-op).

Revision ID: 20260524_0093
Revises: 20260523_0092

Original version attempted blocking CREATE INDEX on large prod tables (notably
``raw_ingestion_records`` / ``cortex_org_links``), causing ECS migration tasks to
exceed the GitHub Actions waiter (~11m) and fail deploy.

Overview latency is addressed in application code (lite continuity context,
deferred semantic readiness). Existing tenant-scoped indexes already cover the
hot paths; any additional partial indexes should be applied manually with
``CREATE INDEX CONCURRENTLY`` during a maintenance window, not in a blocking
Alembic transaction.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

revision: str = "20260524_0093"
down_revision: Union[str, None] = "20260523_0092"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
