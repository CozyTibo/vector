"""E2E restart/resume — pipeline idempotency and phase re-entry."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.repository import (
    compute_pipeline_idempotency_key_v1,
    create_pipeline_run_v1,
    get_running_pipeline_run_v1,
    mark_pipeline_running_v1,
)


@pytest.mark.integration
def test_restart_resume_pipeline_coalesce(db_session: Session, e2e_tenant_id: uuid.UUID) -> None:
    idem = compute_pipeline_idempotency_key_v1(
        tenant_id=e2e_tenant_id, trigger_kind="e2e_restart"
    )
    run1 = create_pipeline_run_v1(
        db_session,
        tenant_id=e2e_tenant_id,
        trigger_kind="e2e_restart",
        bundle_id=None,
        idempotency_key=idem,
    )
    mark_pipeline_running_v1(db_session, run1)
    db_session.flush()
    running = get_running_pipeline_run_v1(db_session, tenant_id=e2e_tenant_id)
    assert running is not None
    run2 = create_pipeline_run_v1(
        db_session,
        tenant_id=e2e_tenant_id,
        trigger_kind="e2e_restart",
        bundle_id=None,
        idempotency_key=f"{idem}-other",
    )
    assert run2.id == run1.id
