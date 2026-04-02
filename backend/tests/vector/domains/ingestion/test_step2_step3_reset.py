"""Step 2 / Step 3 tenant wipes (no connector I/O)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.ingestion.step2_step3_reset import (
    wipe_step2_projections_for_tenant,
    wipe_step3_canonical_for_tenant,
)


@pytest.mark.integration
def test_wipe_step2_projections_for_unknown_tenant_is_noop_counts(db_session: Session) -> None:
    tid = uuid.uuid4()
    out = wipe_step2_projections_for_tenant(db_session, tenant_id=tid)
    assert out == {
        "deleted_github_projection_rows": 0,
        "deleted_linear_projection_rows": 0,
        "deleted_connector_projection_progress_rows": 0,
    }


@pytest.mark.integration
def test_wipe_step3_canonical_for_unknown_tenant_is_noop_counts(db_session: Session) -> None:
    tid = uuid.uuid4()
    out = wipe_step3_canonical_for_tenant(db_session, tenant_id=tid)
    assert out == {
        "deleted_relationships": 0,
        "deleted_mapping_events": 0,
        "deleted_current_mappings": 0,
        "deleted_external_references": 0,
        "deleted_actor_external_identities": 0,
        "deleted_artifacts": 0,
        "deleted_actors": 0,
        "deleted_step3_canonical_cursors": 0,
    }
