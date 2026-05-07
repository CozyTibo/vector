"""Drop legacy per-tool ingestion/projection/canonical tables.

Revision ID: 20260507_0028
Revises: 20260430_0027
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "20260507_0028"
down_revision: Union[str, None] = "20260430_0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_LEGACY_TABLES: tuple[str, ...] = (
    # Step 3 canonical ontology.
    "step3_canonical_cursor",
    "relationship",
    "current_mapping",
    "mapping_event",
    "external_reference",
    "artifact_revision",
    "artifact_changeset",
    "artifact_trackable_unit",
    "artifact_repository",
    "artifact",
    "actor_external_identity",
    "actor",
    "artifact_kind",
    "relation_kind",
    # Step 2 projections.
    "connector_projection_progress",
    "github_commits",
    "github_pull_requests",
    "github_issues",
    "github_repositories",
    "github_users",
    "linear_issue_comments",
    "linear_issues",
    "linear_projects",
    "linear_teams",
    "linear_users",
    # Step 1 raw ingestion.
    "raw_ingestion_records",
    "ingestion_runs",
    "connector_sync_state",
)


def upgrade() -> None:
    # CASCADE is intentional here because these tables are tightly coupled and now retired.
    for table in _LEGACY_TABLES:
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')


def downgrade() -> None:
    msg = (
        "Irreversible migration: legacy ingestion/projection/canonical tables were dropped. "
        "Restore from backup/snapshot if rollback is required."
    )
    raise RuntimeError(msg)
