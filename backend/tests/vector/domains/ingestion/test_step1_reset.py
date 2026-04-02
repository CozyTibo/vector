"""Step 1 tenant wipe (no connector I/O)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.ingestion.step1_reset import wipe_step1_raw_for_tenant


@pytest.mark.integration
def test_wipe_step1_raw_for_unknown_tenant_is_noop_counts(db_session: Session) -> None:
    tid = uuid.uuid4()
    out = wipe_step1_raw_for_tenant(db_session, tenant_id=tid)
    assert out == {
        "deleted_raw_records": 0,
        "deleted_ingestion_runs": 0,
        "deleted_sync_state_rows": 0,
    }
