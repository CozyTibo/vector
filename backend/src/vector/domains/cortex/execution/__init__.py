"""Cortex tenant execution engine (M5): lease + FSM + worker (evolved from convergence)."""

from vector.domains.cortex.execution.execution_path_telemetry import (
    EXECUTION_PATH_ADMIN_BYPASS,
    EXECUTION_PATH_CONVERGENCE,
    EXECUTION_PATH_LEGACY,
    EXECUTION_PATH_PROGRESSION,
    emit_admin_bypass_telemetry_v1,
    emit_execution_path_telemetry_v1,
    execution_path_from_post_ingestion_path,
)
from vector.domains.cortex.execution.tenant_constants import (
    FSM_AWAITING_TCRE,
    FSM_BLOCKED,
    FSM_CANONICAL_DRAINING,
    FSM_IDLE,
    FSM_STALLED,
    LEASE_STATUS_DIRTY,
    LEASE_STATUS_IDLE,
    LEASE_STATUS_RUNNING,
    LEASE_STATUS_STALLED,
    LEASE_STATUS_WAITING,
)

__all__ = [
    "EXECUTION_PATH_ADMIN_BYPASS",
    "EXECUTION_PATH_CONVERGENCE",
    "EXECUTION_PATH_LEGACY",
    "EXECUTION_PATH_PROGRESSION",
    "FSM_AWAITING_TCRE",
    "FSM_BLOCKED",
    "FSM_CANONICAL_DRAINING",
    "FSM_IDLE",
    "FSM_STALLED",
    "LEASE_STATUS_DIRTY",
    "LEASE_STATUS_IDLE",
    "LEASE_STATUS_RUNNING",
    "LEASE_STATUS_STALLED",
    "LEASE_STATUS_WAITING",
    "emit_admin_bypass_telemetry_v1",
    "emit_execution_path_telemetry_v1",
    "execution_path_from_post_ingestion_path",
]

# Import submodules directly to avoid circular imports via substrate orchestrator:
# ``from vector.domains.cortex.execution.lease import mark_tenant_dirty_v1``

