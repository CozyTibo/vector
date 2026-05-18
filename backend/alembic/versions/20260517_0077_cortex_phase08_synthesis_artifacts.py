"""Cortex Phase 08 Step 14 — synthesis intelligence artifacts.

Revision ID: 20260517_0077
Revises: 20260517_0076
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "20260517_0077"
down_revision: Union[str, None] = "20260517_0076"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cortex_synthesis_artifacts",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_kind", sa.String(length=64), nullable=False),
        sa.Column("artifact_digest", sa.String(length=128), nullable=False),
        sa.Column("synthesis_legality_class", sa.String(length=64), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("synthesis_publication_epoch", sa.String(length=128), nullable=True),
        sa.Column("body_json", pg.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["cortex_synthesis_jobs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "artifact_digest", name="uq_cortex_synthesis_artifacts_tenant_digest"),
    )
    op.create_index(
        "ix_cortex_synthesis_artifacts_tenant_created",
        "cortex_synthesis_artifacts",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_cortex_synthesis_artifacts_job_id",
        "cortex_synthesis_artifacts",
        ["job_id"],
    )


def downgrade() -> None:
    op.drop_table("cortex_synthesis_artifacts")
