"""M5: tenant execution lease FSM state + transition log."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.fsm import fsm_state_for_phase_cursor_v1
from vector.domains.cortex.execution.lease import (
    complete_convergence_lease_v1,
    mark_tenant_dirty_v1,
    try_acquire_convergence_lease_v1,
)
from vector.domains.cortex.execution.tenant_constants import (
    FSM_CANONICAL_DRAINING,
    FSM_IDLE,
    LEASE_STATUS_DIRTY,
    LEASE_STATUS_IDLE,
    LEASE_STATUS_RUNNING,
)
from vector.domains.cortex.execution.scheduling import verify_tenant_execution_fsm_on_lease_v1
from vector.domains.cortex.substrate_pipeline.constants import PHASE_03_IDENTITY
from vector.infrastructure.db.models.cortex_execution_transition_log import CortexExecutionTransitionLog
from vector.infrastructure.db.models.tenant import Tenant


@pytest.fixture
def execution_tenant_id(db_session: Session) -> uuid.UUID:
    slug = f"exec-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="Execution FSM Test",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()
    return tenant.id


def test_fsm_phase_cursor_mapping() -> None:
    assert fsm_state_for_phase_cursor_v1(PHASE_03_IDENTITY) == "IDENTITY"
    assert fsm_state_for_phase_cursor_v1(None) == FSM_CANONICAL_DRAINING


def test_verify_tenant_execution_fsm_static_gate() -> None:
    assert verify_tenant_execution_fsm_on_lease_v1() == []


@pytest.mark.integration
def test_mark_dirty_records_fsm_and_transition_log(
    db_session: Session, execution_tenant_id: uuid.UUID
) -> None:
    dirty = mark_tenant_dirty_v1(db_session, tenant_id=execution_tenant_id, reason="test")
    assert dirty["fsm_state"] == FSM_CANONICAL_DRAINING
    assert dirty["status"] == LEASE_STATUS_DIRTY

    count = db_session.scalar(
        select(func.count())
        .select_from(CortexExecutionTransitionLog)
        .where(CortexExecutionTransitionLog.tenant_id == execution_tenant_id)
    )
    assert int(count or 0) >= 1

    row = db_session.scalars(
        select(CortexExecutionTransitionLog)
        .where(CortexExecutionTransitionLog.tenant_id == execution_tenant_id)
        .order_by(CortexExecutionTransitionLog.created_at.desc())
        .limit(1)
    ).first()
    assert row is not None
    assert row.to_state == FSM_CANONICAL_DRAINING


@pytest.mark.integration
def test_acquire_and_complete_idle_fsm(
    db_session: Session, execution_tenant_id: uuid.UUID
) -> None:
    mark_tenant_dirty_v1(db_session, tenant_id=execution_tenant_id, reason="test")
    lease, block = try_acquire_convergence_lease_v1(db_session, tenant_id=execution_tenant_id)
    assert block == ""
    assert lease is not None
    assert lease.status == LEASE_STATUS_RUNNING
    assert lease.fsm_state == FSM_CANONICAL_DRAINING

    complete_convergence_lease_v1(db_session, lease=lease)
    assert lease.status == LEASE_STATUS_IDLE
    assert lease.fsm_state == FSM_IDLE
