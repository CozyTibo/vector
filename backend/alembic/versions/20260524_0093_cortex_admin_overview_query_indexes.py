"""Admin cortex overview — hot-path query indexes.

Revision ID: 20260524_0093
Revises: 20260523_0092
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260524_0093"
down_revision: Union[str, None] = "20260523_0092"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cortex_org_links_tenant_active_endpoints
        ON cortex_org_links (tenant_id, source_entity_id, target_entity_id)
        WHERE revoked_at IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cortex_org_link_candidates_tenant_rule
        ON cortex_org_link_candidates (tenant_id, rule_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cortex_substrate_phase_runs_phase_status_completed
        ON cortex_substrate_phase_runs (phase_id, status, completed_at DESC NULLS LAST)
        WHERE completed_at IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cortex_substrate_pipeline_runs_tenant
        ON cortex_substrate_pipeline_runs (tenant_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_raw_ingestion_records_tenant_id
        ON raw_ingestion_records (tenant_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_cortex_canonical_identity_anchors_tenant
        ON cortex_canonical_identity_anchors (tenant_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_cortex_canonical_identity_anchors_tenant")
    op.execute("DROP INDEX IF EXISTS ix_raw_ingestion_records_tenant_id")
    op.execute("DROP INDEX IF EXISTS ix_cortex_substrate_pipeline_runs_tenant")
    op.execute("DROP INDEX IF EXISTS ix_cortex_substrate_phase_runs_phase_status_completed")
    op.execute("DROP INDEX IF EXISTS ix_cortex_org_link_candidates_tenant_rule")
    op.execute("DROP INDEX IF EXISTS ix_cortex_org_links_tenant_active_endpoints")
