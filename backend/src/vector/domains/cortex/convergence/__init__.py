"""Deprecated import path — use ``vector.domains.cortex.execution.*`` submodules (M5)."""

from vector.domains.cortex.execution.enqueue import enqueue_tenant_convergence_v1
from vector.domains.cortex.execution.lease import mark_tenant_dirty_v1
from vector.domains.cortex.execution.tenant_constants import (
    LEASE_STATUS_DIRTY,
    LEASE_STATUS_IDLE,
    LEASE_STATUS_RUNNING,
    LEASE_STATUS_STALLED,
    LEASE_STATUS_WAITING,
)

__all__ = [
    "LEASE_STATUS_DIRTY",
    "LEASE_STATUS_IDLE",
    "LEASE_STATUS_RUNNING",
    "LEASE_STATUS_STALLED",
    "LEASE_STATUS_WAITING",
    "enqueue_tenant_convergence_v1",
    "mark_tenant_dirty_v1",
]
