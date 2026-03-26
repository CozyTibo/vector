"""Add artifact–artifact relation_kind: contains (PR changeset → commit revision)."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260403_0012"
down_revision: str | None = "20260324_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO relation_kind (id, name, description, subject_kind, object_kind)
            VALUES (
                3,
                'contains',
                'Subject artifact includes or is composed of the object artifact',
                'artifact',
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
    op.execute(sa.text("DELETE FROM relation_kind WHERE name = 'contains'"))
    op.execute(
        sa.text(
            "SELECT setval(pg_get_serial_sequence('relation_kind', 'id'), "
            "(SELECT COALESCE(MAX(id), 1) FROM relation_kind))",
        ),
    )
