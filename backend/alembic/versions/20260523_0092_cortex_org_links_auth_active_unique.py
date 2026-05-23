"""Wave S1 — dedupe active authoritative links + unique endpoint constraint.

Revision ID: 20260523_0092
Revises: 20260522_0091
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260523_0092"
down_revision: Union[str, None] = "20260522_0091"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Revoke duplicate active authoritative rows (keep newest per endpoint triple).
    op.execute(
        """
        UPDATE cortex_org_links AS l
        SET revoked_at = NOW(),
            updated_at = NOW()
        WHERE l.id IN (
          SELECT id FROM (
            SELECT id,
              ROW_NUMBER() OVER (
                PARTITION BY tenant_id, source_entity_id, target_entity_id, link_type
                ORDER BY created_at DESC, id DESC
              ) AS rn
            FROM cortex_org_links
            WHERE revoked_at IS NULL
              AND link_authority = 'authoritative'
          ) AS ranked
          WHERE ranked.rn > 1
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_cortex_org_links_auth_active_endpoints
        ON cortex_org_links (tenant_id, source_entity_id, target_entity_id, link_type)
        WHERE revoked_at IS NULL AND link_authority = 'authoritative'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_cortex_org_links_auth_active_endpoints")
