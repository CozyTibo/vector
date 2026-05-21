"""Tests for Postgres-authoritative convergence lease."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.tenant_constants import (
    FSM_CANONICAL_DRAINING,
    FSM_IDLE,
    LEASE_STATUS_DIRTY,
    LEASE_STATUS_IDLE,
    LEASE_STATUS_RUNNING,
)
from vector.domains.cortex.execution.lease import (
    complete_convergence_lease_v1,
    mark_tenant_dirty_v1,
    try_acquire_convergence_lease_v1,
)
from vector.infrastructure.db.models.tenant import Tenant


@pytest.fixture
def convergence_tenant_id(db_session: Session) -> uuid.UUID:
    slug = f"conv-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="Convergence Test",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()
    return tenant.id


@pytest.mark.integration
def test_mark_dirty_bumps_epoch_and_acquire(db_session: Session, convergence_tenant_id: uuid.UUID) -> None:
    dirty = mark_tenant_dirty_v1(db_session, tenant_id=convergence_tenant_id, reason="test")
    assert dirty["obligation_epoch"] == 1
    assert dirty["status"] == LEASE_STATUS_DIRTY
    assert dirty["fsm_state"] == FSM_CANONICAL_DRAINING

    lease, block = try_acquire_convergence_lease_v1(db_session, tenant_id=convergence_tenant_id)
    assert block == ""
    assert lease is not None
    assert lease.status == LEASE_STATUS_RUNNING
    assert int(lease.target_epoch) == 1

    complete_convergence_lease_v1(db_session, lease=lease)
    assert lease.status == LEASE_STATUS_IDLE
    assert lease.fsm_state == FSM_IDLE

    mark_tenant_dirty_v1(db_session, tenant_id=convergence_tenant_id, reason="second")
    lease2, block2 = try_acquire_convergence_lease_v1(db_session, tenant_id=convergence_tenant_id)
    assert block2 == ""
    assert lease2 is not None
    assert int(lease2.obligation_epoch) == 2


@pytest.mark.integration
def test_running_lease_blocks_second_acquire(
    db_session: Session, convergence_tenant_id: uuid.UUID
) -> None:
    mark_tenant_dirty_v1(db_session, tenant_id=convergence_tenant_id, reason="test")
    lease, _ = try_acquire_convergence_lease_v1(db_session, tenant_id=convergence_tenant_id)
    assert lease is not None

    lease2, block = try_acquire_convergence_lease_v1(db_session, tenant_id=convergence_tenant_id)
    assert lease2 is None
    assert block == "lease_held_by_other_worker"


@pytest.mark.integration
def test_obligation_ahead_after_complete_stays_dirty(
    db_session: Session, convergence_tenant_id: uuid.UUID
) -> None:
    mark_tenant_dirty_v1(db_session, tenant_id=convergence_tenant_id, reason="first")
    lease, _ = try_acquire_convergence_lease_v1(db_session, tenant_id=convergence_tenant_id)
    assert lease is not None
    mark_tenant_dirty_v1(db_session, tenant_id=convergence_tenant_id, reason="during_run")
    complete_convergence_lease_v1(db_session, lease=lease)
    assert lease.status == LEASE_STATUS_DIRTY
    assert int(lease.obligation_epoch) > int(lease.target_epoch)
