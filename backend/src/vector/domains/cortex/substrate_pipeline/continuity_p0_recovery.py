"""Phase 0 step 0.3 (P0-C) — recover failed pipeline run or start post-ingestion continuity run."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.blocked import clear_execution_block_for_rerun_v1
from vector.domains.cortex.execution.enqueue import enqueue_tenant_convergence_v1
from vector.domains.cortex.execution.fsm import apply_fsm_transition_v1, fsm_state_for_phase_cursor_v1
from vector.domains.cortex.execution.execution_path_telemetry import (
    EXECUTION_PATH_ADMIN_BYPASS,
    emit_execution_path_telemetry_v1,
)
from vector.domains.cortex.execution.lease import _get_or_create_lease, mark_tenant_dirty_v1
from vector.domains.cortex.execution.tenant_constants import FSM_STALLED, LEASE_STATUS_STALLED
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_STATUS_COMPLETED,
    PHASE_STATUS_QUEUED,
    PIPELINE_STATUS_FAILED,
    PIPELINE_STATUS_RUNNING,
    PIPELINE_TRIGGER_POST_INGESTION,
    SUBSTRATE_PIPELINE_PHASE_ORDER,
)
from vector.domains.cortex.substrate_pipeline.orchestrator import start_substrate_pipeline_run_v1
from vector.domains.cortex.substrate_pipeline.repository import (
    get_phase_run_v1,
    mark_pipeline_running_v1,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
    CortexSubstratePhaseRun,
    CortexSubstratePipelineRun,
)

_LOGGER = logging.getLogger(__name__)

CONTINUITY_P0_RECOVER_TRIGGER_V1: str = "continuity_p0_step03"
CONTINUITY_P0_PHASES_TO_MIRROR_V1: tuple[str, ...] = (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
)

RecoveryStrategyV1 = Literal["new_run", "recover_in_place"]


def get_latest_pipeline_run_for_tenant_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> CortexSubstratePipelineRun | None:
    return session.scalar(
        select(CortexSubstratePipelineRun)
        .where(CortexSubstratePipelineRun.tenant_id == tenant_id)
        .order_by(CortexSubstratePipelineRun.created_at.desc())
        .limit(1)
    )


def get_latest_failed_pipeline_run_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> CortexSubstratePipelineRun | None:
    return session.scalar(
        select(CortexSubstratePipelineRun)
        .where(
            CortexSubstratePipelineRun.tenant_id == tenant_id,
            CortexSubstratePipelineRun.status == PIPELINE_STATUS_FAILED,
        )
        .order_by(CortexSubstratePipelineRun.created_at.desc())
        .limit(1)
    )


def _phase_index_v1(phase_id: str) -> int:
    try:
        return SUBSTRATE_PIPELINE_PHASE_ORDER.index(phase_id)
    except ValueError as exc:
        msg = f"unknown_phase:{phase_id}"
        raise ValueError(msg) from exc


def requeue_pipeline_phases_from_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    from_phase_id: str,
    clear_outputs: bool = True,
) -> list[str]:
    """Reset ``from_phase_id`` and all later phases to ``queued`` (P0-C receipt reset)."""
    start_idx = _phase_index_v1(from_phase_id)
    requeued: list[str] = []
    for phase_id in SUBSTRATE_PIPELINE_PHASE_ORDER[start_idx:]:
        phase = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=phase_id)
        if phase is None:
            continue
        phase.status = PHASE_STATUS_QUEUED
        phase.started_at = None
        phase.completed_at = None
        phase.error_detail = None
        phase.celery_task_id = None
        if clear_outputs:
            phase.output_json = {}
        requeued.append(phase_id)
    session.flush()
    return requeued


def mirror_completed_phases_between_runs_v1(
    session: Session,
    *,
    source_pipeline_run_id: uuid.UUID,
    dest_pipeline_run_id: uuid.UUID,
    phase_ids: tuple[str, ...] = CONTINUITY_P0_PHASES_TO_MIRROR_V1,
) -> list[str]:
    """Copy completed phase receipts from a prior run (skip re-running 02–04)."""
    mirrored: list[str] = []
    for phase_id in phase_ids:
        src = get_phase_run_v1(
            session,
            pipeline_run_id=source_pipeline_run_id,
            phase_id=phase_id,
        )
        dst = get_phase_run_v1(
            session,
            pipeline_run_id=dest_pipeline_run_id,
            phase_id=phase_id,
        )
        if src is None or dst is None or src.status != PHASE_STATUS_COMPLETED:
            continue
        dst.status = PHASE_STATUS_COMPLETED
        dst.output_json = dict(src.output_json or {})
        dst.error_detail = None
        dst.started_at = src.started_at
        dst.completed_at = src.completed_at
        dst.attempt = int(src.attempt or 1)
        mirrored.append(phase_id)
    session.flush()
    return mirrored


def reopen_failed_pipeline_run_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    resume_from_phase: str = PHASE_05_TRAVERSAL,
) -> dict[str, Any]:
    """Re-open a terminal-failed run: run ``running``, phases from cursor re-queued."""
    run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
    if run is None:
        return {"reopened": False, "reason": "pipeline_run_not_found"}
    if run.status != PIPELINE_STATUS_FAILED:
        return {
            "reopened": False,
            "reason": "pipeline_not_failed",
            "status": run.status,
        }
    requeued = requeue_pipeline_phases_from_v1(
        session,
        pipeline_run_id=pipeline_run_id,
        from_phase_id=resume_from_phase,
    )
    run.status = PIPELINE_STATUS_RUNNING
    run.error_detail = None
    run.completed_at = None
    run.current_phase_id = resume_from_phase
    mark_pipeline_running_v1(session, run)
    session.flush()
    return {
        "reopened": True,
        "pipeline_run_id": str(pipeline_run_id),
        "resume_from_phase": resume_from_phase,
        "requeued_phases": requeued,
        "pipeline_status": run.status,
    }


def _attach_lease_and_enqueue_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    phase_cursor: str,
    enqueue_celery: bool = True,
) -> dict[str, Any]:
    lease = _get_or_create_lease(session, tenant_id=tenant_id)
    if (lease.fsm_state or "").strip() == FSM_STALLED or lease.status == LEASE_STATUS_STALLED:
        lease.last_error = None
    clear_execution_block_for_rerun_v1(
        session,
        lease=lease,
        phase_cursor=phase_cursor,
        pipeline_run_id=pipeline_run_id,
    )
    dirty = mark_tenant_dirty_v1(
        session,
        tenant_id=tenant_id,
        reason=CONTINUITY_P0_RECOVER_TRIGGER_V1,
    )
    lease.pipeline_run_id = pipeline_run_id
    lease.phase_cursor = phase_cursor
    apply_fsm_transition_v1(
        session,
        lease=lease,
        to_state=fsm_state_for_phase_cursor_v1(phase_cursor),
        trigger="continuity_p0_recover_fsm_align",
        pipeline_run_id=pipeline_run_id,
        gate_result="pass",
    )
    session.flush()
    telemetry = emit_execution_path_telemetry_v1(
        tenant_id=tenant_id,
        execution_path=EXECUTION_PATH_ADMIN_BYPASS,
        trigger=CONTINUITY_P0_RECOVER_TRIGGER_V1,
        pipeline_run_id=pipeline_run_id,
        detail={"phase_cursor": phase_cursor},
    )
    enqueue: dict[str, Any] = {"enqueued": False, "reason": "enqueue_skipped"}
    if enqueue_celery:
        enqueue = enqueue_tenant_convergence_v1(
            tenant_id,
            reason=f"{CONTINUITY_P0_RECOVER_TRIGGER_V1}:{phase_cursor}",
        )
    else:
        enqueue = {
            "enqueued": False,
            "reason": "deferred_to_convergence_sweeper",
            "hint": "obligation_epoch_bumped; prod sweeper will run execution slice",
        }
    return {
        "dirty": dirty,
        "enqueue": enqueue,
        "execution_path_telemetry": telemetry,
        "lease_fsm_state": lease.fsm_state,
        "lease_status": lease.status,
    }


def recover_continuity_p0_pipeline_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    strategy: RecoveryStrategyV1 = "new_run",
    source_pipeline_run_id: uuid.UUID | None = None,
    resume_from_phase: str = PHASE_05_TRAVERSAL,
    enqueue_celery: bool = True,
) -> dict[str, Any]:
    """P0-C: new post-ingestion run (default) or in-place failed-run recovery + execution enqueue."""
    source = None
    if source_pipeline_run_id is not None:
        source = session.get(CortexSubstratePipelineRun, source_pipeline_run_id)
        if source is None or source.tenant_id != tenant_id:
            return {"recovered": False, "reason": "source_pipeline_run_not_found"}
    if source is None:
        source = get_latest_failed_pipeline_run_v1(session, tenant_id=tenant_id)
    if source is None:
        source = get_latest_pipeline_run_for_tenant_v1(session, tenant_id=tenant_id)

    prior_failed_run_id = (
        str(source.id) if source is not None and source.status == PIPELINE_STATUS_FAILED else None
    )

    if strategy == "recover_in_place":
        if source is None or source.status != PIPELINE_STATUS_FAILED:
            return {"recovered": False, "reason": "no_failed_pipeline_run_for_in_place_recovery"}
        reopen = reopen_failed_pipeline_run_v1(
            session,
            pipeline_run_id=source.id,
            resume_from_phase=resume_from_phase,
        )
        if not reopen.get("reopened"):
            return {"recovered": False, **reopen}
        attach = _attach_lease_and_enqueue_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=source.id,
            phase_cursor=resume_from_phase,
            enqueue_celery=enqueue_celery,
        )
        return {
            "recovered": True,
            "strategy": strategy,
            "tenant_id": str(tenant_id),
            "pipeline_run_id": str(source.id),
            "prior_failed_run_id": prior_failed_run_id,
            "reopen": reopen,
            "execution": attach,
        }

    run_id, created = start_substrate_pipeline_run_v1(
        session,
        tenant_id=tenant_id,
        trigger_kind=PIPELINE_TRIGGER_POST_INGESTION,
        bundle_id=None,
        celery_root_task_id=None,
    )
    run = session.get(CortexSubstratePipelineRun, run_id)
    if run is None:
        return {"recovered": False, "reason": "pipeline_run_create_failed"}

    mirrored: list[str] = []
    if source is not None and source.id != run_id:
        mirrored = mirror_completed_phases_between_runs_v1(
            session,
            source_pipeline_run_id=source.id,
            dest_pipeline_run_id=run_id,
        )

    mark_pipeline_running_v1(session, run)
    run.current_phase_id = resume_from_phase
    requeued = requeue_pipeline_phases_from_v1(
        session,
        pipeline_run_id=run_id,
        from_phase_id=resume_from_phase,
    )
    session.flush()

    attach = _attach_lease_and_enqueue_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=run_id,
        phase_cursor=resume_from_phase,
        enqueue_celery=enqueue_celery,
    )

    _LOGGER.info(
        "continuity_p0_pipeline_recovered tenant_id=%s run_id=%s created=%s mirrored=%s",
        tenant_id,
        run_id,
        created,
        mirrored,
    )

    return {
        "recovered": True,
        "strategy": strategy,
        "tenant_id": str(tenant_id),
        "pipeline_run_id": str(run_id),
        "pipeline_run_created": created,
        "prior_failed_run_id": prior_failed_run_id,
        "mirrored_phases": mirrored,
        "requeued_phases": requeued,
        "resume_from_phase": resume_from_phase,
        "pipeline_status": run.status,
        "execution": attach,
        "recovered_at": datetime.now(UTC).isoformat(),
    }
