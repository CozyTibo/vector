"""Phase 06 TCRE output + post-enqueue lease contract (execution slice)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.execution.tenant_constants import FSM_AWAITING_TCRE, LEASE_STATUS_WAITING
from vector.domains.cortex.substrate_pipeline.constants import PHASE_07_RETRIEVAL
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePipelineRun


class ExecutionProgressionError(ValueError):
    """Illegal phase-06 / TCRE wait transition on the execution lease."""

    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def assert_pipe085_chain_after_phase06_legal_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    tenant_id: uuid.UUID | None = None,
) -> None:
    """After phase 06 async enqueue: execution lease must be AWAITING_TCRE → phase 07 cursor."""
    tid = tenant_id
    if tid is None:
        run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
        if run is None:
            raise ExecutionProgressionError(
                "pipe085_pipeline_run_not_found",
                detail={"pipeline_run_id": str(pipeline_run_id)},
            )
        tid = run.tenant_id

    lease = get_tenant_execution_lease_v1(session, tenant_id=tid)
    if lease is None:
        raise ExecutionProgressionError(
            "pipe085_missing_execution_lease_after_phase06",
            detail={
                "pipeline_run_id": str(pipeline_run_id),
                "tenant_id": str(tid),
            },
        )
    if lease.status != LEASE_STATUS_WAITING:
        raise ExecutionProgressionError(
            "pipe085_execution_lease_not_waiting",
            detail={"status": lease.status, "expected": LEASE_STATUS_WAITING},
        )
    if lease.fsm_state != FSM_AWAITING_TCRE:
        raise ExecutionProgressionError(
            "pipe085_execution_lease_not_awaiting_tcre",
            detail={"fsm_state": lease.fsm_state, "expected": FSM_AWAITING_TCRE},
        )
    if lease.pipeline_run_id != pipeline_run_id:
        raise ExecutionProgressionError(
            "pipe085_execution_lease_pipeline_mismatch",
            detail={
                "lease_pipeline_run_id": str(lease.pipeline_run_id),
                "expected": str(pipeline_run_id),
            },
        )
    if lease.phase_cursor != PHASE_07_RETRIEVAL:
        raise ExecutionProgressionError(
            "pipe085_execution_lease_wrong_phase_cursor",
            detail={"phase_cursor": lease.phase_cursor, "expected": PHASE_07_RETRIEVAL},
        )


def enforce_phase06_progression_law_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    phase06_output: Mapping[str, Any],
) -> None:
    """After phase 06 enqueue, require async TCRE job contract on phase output."""
    _ = (session, tenant_id, pipeline_run_id)
    if not phase06_output.get("async"):
        raise ExecutionProgressionError(
            "phase06_must_be_async",
            detail={"output": dict(phase06_output)},
        )
    job_id = phase06_output.get("job_id")
    if not job_id:
        raise ExecutionProgressionError(
            "phase06_missing_tcre_job_id",
            detail={"required": "enqueue_reconstruction_job_v1.job_id"},
        )
