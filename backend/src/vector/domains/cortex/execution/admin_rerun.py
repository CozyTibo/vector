"""Operator admin rerun — mark dirty and enqueue execution slice (M7)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.blocked import clear_execution_block_for_rerun_v1
from vector.domains.cortex.execution.enqueue import enqueue_execution_slice_at_phase_v1
from vector.domains.cortex.execution.execution_path_telemetry import (
    EXECUTION_PATH_ADMIN_BYPASS,
    emit_execution_path_telemetry_v1,
)
from vector.domains.cortex.execution.lease import _get_or_create_lease, mark_tenant_dirty_v1
from vector.domains.cortex.execution.progression_status import first_incomplete_phase_v1, phase_status_map_v1
from vector.domains.cortex.execution.tenant_constants import FSM_BLOCKED
from vector.domains.cortex.substrate_pipeline.constants import PHASE_02_CANONICAL
from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePipelineRun

ADMIN_RERUN_TRIGGER_V1 = "admin_manual_rerun"


def admin_rerun_substrate_execution_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    phase_cursor: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Replace progression coordinator: set lease cursor, mark dirty, enqueue execution slice."""
    run: CortexSubstratePipelineRun | None = None
    if pipeline_run_id is not None:
        run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
        if run is None or run.tenant_id != tenant_id:
            return {"reran": False, "reason": "pipeline_run_not_found"}
    if run is None:
        run = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    if run is None:
        return {"reran": False, "reason": "no_active_pipeline_run", "continued": False}

    phase_status = phase_status_map_v1(session, pipeline_run_id=run.id)
    cursor = (phase_cursor or "").strip() or first_incomplete_phase_v1(phase_status)
    if not cursor:
        return {
            "reran": False,
            "reason": "pipeline_phases_complete",
            "continued": False,
            "pipeline_run_id": str(run.id),
        }

    lease = _get_or_create_lease(session, tenant_id=tenant_id)
    blocked = (lease.fsm_state or "").strip() == FSM_BLOCKED
    if blocked or force:
        clear_execution_block_for_rerun_v1(
            session,
            lease=lease,
            phase_cursor=cursor,
            pipeline_run_id=run.id,
        )

    dirty = mark_tenant_dirty_v1(
        session,
        tenant_id=tenant_id,
        reason=f"{ADMIN_RERUN_TRIGGER_V1}:{cursor}",
    )
    lease.phase_cursor = cursor
    lease.pipeline_run_id = run.id
    session.flush()

    telemetry = emit_execution_path_telemetry_v1(
        tenant_id=tenant_id,
        execution_path=EXECUTION_PATH_ADMIN_BYPASS,
        trigger=ADMIN_RERUN_TRIGGER_V1,
        pipeline_run_id=run.id,
        detail={"phase_cursor": cursor, "force": force, "was_blocked": blocked},
    )

    hint = enqueue_execution_slice_at_phase_v1(
        tenant_id=tenant_id,
        pipeline_run_id=run.id,
        phase_cursor=cursor or PHASE_02_CANONICAL,
        reason=ADMIN_RERUN_TRIGGER_V1,
    )

    return {
        "reran": True,
        "continued": True,
        "tenant_id": str(tenant_id),
        "pipeline_run_id": str(run.id),
        "phase_cursor": cursor,
        "was_blocked": blocked,
        "force": force,
        "dirty": dirty,
        "enqueue": hint,
        "execution_path_telemetry": telemetry,
    }
