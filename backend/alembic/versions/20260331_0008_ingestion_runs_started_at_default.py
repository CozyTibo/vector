"""ingestion_runs.started_at server default (align DB with ORM).

Revision ID: 20260331_0008
Revises: 20260330_0007
Create Date: 2026-03-31

The initial Step 1 migration set started_at NOT NULL without DEFAULT; inserts
that omit the column failed. Application code sets started_at explicitly; this
migration adds DEFAULT now() for consistency and ad-hoc SQL.

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260331_0008"
down_revision: Union[str, None] = "20260330_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "ingestion_runs",
        "started_at",
        server_default=sa.text("now()"),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "ingestion_runs",
        "started_at",
        server_default=None,
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )
