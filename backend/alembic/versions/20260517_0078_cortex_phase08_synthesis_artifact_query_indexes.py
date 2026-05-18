"""Cortex Phase 08 Step 20 — synthesis artifact query indexes (lookup + epoch pins).

Revision ID: 20260517_0078
Revises: 20260517_0077
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260517_0078"
down_revision: Union[str, None] = "20260517_0077"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "cortex_synthesis_artifacts",
        sa.Column("retrieval_lookup_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "cortex_synthesis_artifacts",
        sa.Column("retrieval_query_replay_identity", sa.String(length=128), nullable=True),
    )
    op.execute(
        """
        UPDATE cortex_synthesis_artifacts
        SET retrieval_query_replay_identity = NULLIF(body_json->>'retrieval_query_replay_identity', ''),
            retrieval_lookup_id = NULLIF(
                COALESCE(
                    body_json->>'retrieval_lookup_id',
                    body_json->'evidence_scope_summary'->>'retrieval_lookup_id'
                ),
                ''
            )
        """
    )
    op.create_index(
        "ix_cortex_synthesis_artifacts_tenant_lookup",
        "cortex_synthesis_artifacts",
        ["tenant_id", "retrieval_lookup_id"],
    )
    op.create_index(
        "ix_cortex_synthesis_artifacts_tenant_rqid",
        "cortex_synthesis_artifacts",
        ["tenant_id", "retrieval_query_replay_identity"],
    )
    op.create_index(
        "ix_cortex_synthesis_artifacts_tenant_pub_epoch",
        "cortex_synthesis_artifacts",
        ["tenant_id", "synthesis_publication_epoch"],
    )


def downgrade() -> None:
    op.drop_index("ix_cortex_synthesis_artifacts_tenant_pub_epoch", table_name="cortex_synthesis_artifacts")
    op.drop_index("ix_cortex_synthesis_artifacts_tenant_rqid", table_name="cortex_synthesis_artifacts")
    op.drop_index("ix_cortex_synthesis_artifacts_tenant_lookup", table_name="cortex_synthesis_artifacts")
    op.drop_column("cortex_synthesis_artifacts", "retrieval_query_replay_identity")
    op.drop_column("cortex_synthesis_artifacts", "retrieval_lookup_id")
