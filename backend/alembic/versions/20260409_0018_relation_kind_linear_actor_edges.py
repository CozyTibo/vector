"""Add relation_kind rows for Linear actor→artifact edges (assignee, commenter).

Revision ID: 20260409_0018
Revises: 20260408_0017
Create Date: 2026-04-09

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260409_0018"
down_revision: Union[str, None] = "20260408_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO relation_kind (id, name, description, subject_kind, object_kind) VALUES
            (
                4,
                'assigned_to',
                'Actor is assigned to the work item',
                'actor',
                'artifact'
            ),
            (
                5,
                'commented_on',
                'Actor commented on the work item',
                'actor',
                'artifact'
            )
            ON CONFLICT (name) DO NOTHING
            """
        ),
    )
    op.execute(
        sa.text(
            "SELECT setval(pg_get_serial_sequence('relation_kind', 'id'), "
            "(SELECT COALESCE(MAX(id), 1) FROM relation_kind))",
        ),
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM relation_kind WHERE name IN ('assigned_to', 'commented_on')"))
    op.execute(
        sa.text(
            "SELECT setval(pg_get_serial_sequence('relation_kind', 'id'), "
            "(SELECT COALESCE(MAX(id), 1) FROM relation_kind))",
        ),
    )
