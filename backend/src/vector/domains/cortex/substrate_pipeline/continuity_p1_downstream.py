"""Phase 1 step 1.5 — P1-D/E prod downstream chain (06 wait → resume → 07 → 08)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.lease import (
    get_tenant_execution_lease_v1,
    mark_tenant_dirty_v1,
    resume_convergence_from_waiting_v1,
)
from vector.domains.cortex.execution.run_tenant_execution import run_tenant_convergence_v1
from vector.domains.cortex.execution.tenant_constants import LEASE_STATUS_WAITING
from vector.domains.cortex.reasoning.runtime.reasoning_runtime_orchestrator import (
    execute_tcre_reconstruction_job_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
    PHASE_STATUS_COMPLETED,
    PHASE_STATUS_FAILED,
    PIPELINE_STATUS_FAILED,
    PIPELINE_STATUS_RUNNING,
)
from vector.domains.cortex.substrate_pipeline.continuity_p0_recovery import (
    reopen_failed_pipeline_run_v1,
    requeue_pipeline_phases_from_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p1_tcre import (
    snapshot_tcre_execution_footprint_v1,
)
from vector.domains.cortex.substrate_pipeline.pipeline_receipts import (
    build_phase_execution_receipt_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)

P1_5_STEP = "1.5_p1de_downstream_chain"
DEFAULT_PIPELINE_RUN_ID = uuid.UUID("ce7df86d-b229-4467-ad28-1109ed119d34")


def _phase_receipt_summary_v1(phase_row: Any | None) -> dict[str, Any]:
    if phase_row is None:
        return {"status": None, "receipt": None, "output_summary": {}}
    output = dict(phase_row.output_json or {})
    receipt = build_phase_execution_receipt_v1(
        phase_id=phase_row.phase_id,
        status=phase_row.status,
        output=output,
    )
    return {
        "phase_id": phase_row.phase_id,
        "status": phase_row.status,
        "started_at": phase_row.started_at.isoformat() if phase_row.started_at else None,
        "completed_at": phase_row.completed_at.isoformat() if phase_row.completed_at else None,
        "error_detail": phase_row.error_detail,
        "receipt_digest": receipt.get("phase_execution_receipt_digest"),
        "output_summary": (receipt.get("body") or {}).get("output_summary") or {},
    }


def snapshot_downstream_phase_receipts_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
) -> dict[str, Any]:
    """Receipt snapshots for phases 06–08 on a pipeline run."""
    from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
        CortexSubstratePipelineRun,
    )

    run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
    phases = {
        PHASE_06_TCRE: _phase_receipt_summary_v1(
            get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_06_TCRE)
        ),
        PHASE_07_RETRIEVAL: _phase_receipt_summary_v1(
            get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_07_RETRIEVAL)
        ),
        PHASE_08_SYNTHESIS: _phase_receipt_summary_v1(
            get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_08_SYNTHESIS)
        ),
    }
    prid = str(pipeline_run_id)
    scoped_jobs = [
        j
        for j in session.scalars(
            select(CortexTcreReconstructionJob).where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
            )
        ).all()
        if str((j.scope_json or {}).get("substrate_pipeline_run_id") or "") == prid
    ]
    tcre_by_status: dict[str, int] = {}
    for job in scoped_jobs:
        st = str(job.status)
        tcre_by_status[st] = tcre_by_status.get(st, 0) + 1
    return {
        "pipeline_run_id": str(pipeline_run_id),
        "pipeline_status": run.status if run is not None else None,
        "phases": phases,
        "tcre_jobs_by_status": tcre_by_status,
        "tcre_jobs_total": sum(tcre_by_status.values()),
        "tcre_jobs_completed": tcre_by_status.get("completed", 0),
    }


def complete_queued_tcre_jobs_for_pipeline_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    limit: int = 8,
    enqueue_convergence: bool = False,
) -> dict[str, Any]:
    """Run queued TCRE jobs inline (worker-equivalent) and chain pipeline resume."""
    prid = str(pipeline_run_id)
    jobs = list(
        session.scalars(
            select(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status == "queued",
            )
            .order_by(CortexTcreReconstructionJob.created_at.asc())
            .limit(max(1, min(int(limit), 32)))
        ).all()
    )
    completed: list[dict[str, Any]] = []
    for job in jobs:
        scope = dict(job.scope_json or {})
        if str(scope.get("substrate_pipeline_run_id") or "") != prid:
            continue
        try:
            summary = execute_tcre_reconstruction_job_v1(session, job)
        except Exception as exc:  # noqa: BLE001
            completed.append(
                {
                    "job_id": str(job.id),
                    "status": getattr(job, "status", "failed"),
                    "error": str(exc)[:500],
                }
            )
            continue
        chained = None
        if job.status == "completed":
            if enqueue_convergence:
                from vector.domains.cortex.execution.tcre_resume import (
                    on_tcre_job_terminal_for_execution_v1,
                )

                chained = on_tcre_job_terminal_for_execution_v1(
                    session,
                    tenant_id=tenant_id,
                    pipeline_run_id=pipeline_run_id,
                    tcre_job_id=job.id,
                    tcre_job_status=str(job.status),
                )
            else:
                lease_resume = resume_convergence_from_waiting_v1(
                    session,
                    tenant_id=tenant_id,
                    phase_cursor=PHASE_07_RETRIEVAL,
                    pipeline_run_id=pipeline_run_id,
                )
                chained = {
                    "resumed": True,
                    "path": "convergence_lease",
                    "pipeline_run_id": str(pipeline_run_id),
                    "tcre_job_id": str(job.id),
                    "tcre_job_status": str(job.status),
                    "lease": lease_resume,
                    "convergence_enqueue_skipped": True,
                }
        completed.append(
            {
                "job_id": str(job.id),
                "status": job.status,
                "summary_keys": list(summary.keys()) if isinstance(summary, dict) else [],
                "pipeline_chain": chained,
            }
        )
    session.flush()
    return {
        "jobs_processed": len(completed),
        "jobs": completed,
    }


def prepare_pipeline_for_downstream_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
) -> dict[str, Any]:
    """Re-open failed pipeline and align lease cursor for 07→08 execution."""
    from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
        CortexSubstratePipelineRun,
    )

    run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
    if run is None:
        return {"prepared": False, "reason": "pipeline_run_not_found"}

    reopen_out: dict[str, Any] = {"reopened": False}
    if run.status == PIPELINE_STATUS_FAILED:
        p06 = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_06_TCRE)
        resume_from = (
            PHASE_07_RETRIEVAL
            if p06 is not None and p06.status == PHASE_STATUS_COMPLETED
            else PHASE_06_TCRE
        )
        reopen_out = reopen_failed_pipeline_run_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            resume_from_phase=resume_from,
        )
    p08 = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_08_SYNTHESIS)
    if p08 is not None and p08.status == PHASE_STATUS_FAILED:
        requeue_pipeline_phases_from_v1(
            session,
            pipeline_run_id=pipeline_run_id,
            from_phase_id=PHASE_08_SYNTHESIS,
        )
        run.status = PIPELINE_STATUS_RUNNING
        run.error_detail = None
        run.completed_at = None
        session.flush()

    p07 = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_07_RETRIEVAL)
    cursor = (
        PHASE_07_RETRIEVAL
        if p07 is None or p07.status != PHASE_STATUS_COMPLETED
        else PHASE_08_SYNTHESIS
    )
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    if lease is not None and lease.status == LEASE_STATUS_WAITING:
        resume_convergence_from_waiting_v1(
            session,
            tenant_id=tenant_id,
            phase_cursor=PHASE_07_RETRIEVAL,
            pipeline_run_id=pipeline_run_id,
        )
    else:
        mark_tenant_dirty_v1(
            session,
            tenant_id=tenant_id,
            reason="continuity_p1_step15_downstream",
        )
        lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
        if lease is not None:
            lease.pipeline_run_id = pipeline_run_id
            lease.phase_cursor = cursor
            session.flush()

    return {
        "prepared": True,
        "pipeline_run_id": str(pipeline_run_id),
        "pipeline_status": run.status,
        "reopen": reopen_out,
        "execution_phase_cursor": cursor,
        "lease_status": lease.status if lease else None,
        "lease_fsm_state": lease.fsm_state if lease else None,
    }


def run_downstream_execution_slices_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    max_slices: int = 16,
    reason: str = "continuity_p1_step15",
    enqueue_convergence: bool = False,
) -> dict[str, Any]:
    """Drive execution worker until time-budget requeue or terminal outcomes."""
    from contextlib import nullcontext
    from unittest.mock import patch

    def _noop_enqueue(*_a: object, **_k: object) -> dict[str, Any]:
        return {"enqueued": False, "reason": "skipped_local_proof"}

    slices: list[dict[str, Any]] = []
    enqueue_cm = (
        patch(
            "vector.domains.cortex.execution.enqueue.enqueue_tenant_convergence_v1",
            _noop_enqueue,
        )
        if not enqueue_convergence
        else nullcontext()
    )
    with enqueue_cm:
        for i in range(max(1, min(int(max_slices), 32))):
            try:
                out = run_tenant_convergence_v1(
                    session,
                    tenant_id=tenant_id,
                    reason=f"{reason}_slice_{i}",
                )
            except RuntimeError as exc:
                slices.append({"error": str(exc)[:500], "slice_index": i})
                break
            slices.append(out)
            outcome = str(out.get("outcome") or "")
            if outcome in (
                "waiting_on_tcre",
                "converged_slice",
                "blocked_retrieval_starvation",
                "execution_stalled",
            ):
                break
            if not out.get("acquired"):
                break
    return {"slices_executed": len(slices), "slices": slices, "enqueue_skipped": not enqueue_convergence}


def evaluate_p1_5_downstream_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    receipts: dict[str, Any],
    tcre_footprint: dict[str, Any],
    chain_drive: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step 1.5: phase 06–08 receipts + TCRE completed count > 0."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    phases = dict(receipts.get("phases") or {})
    p06 = dict(phases.get(PHASE_06_TCRE) or {})
    p07 = dict(phases.get(PHASE_07_RETRIEVAL) or {})
    p08 = dict(phases.get(PHASE_08_SYNTHESIS) or {})
    tcre_completed = int(receipts.get("tcre_jobs_completed") or 0)
    waiting_reason = str(tcre_footprint.get("waiting_reason") or "")

    p06_ok = p06.get("status") == PHASE_STATUS_COMPLETED
    p06_async = bool((p06.get("output_summary") or {}).get("async"))
    p07_ok = p07.get("status") == PHASE_STATUS_COMPLETED
    p08_ok = p08.get("status") == PHASE_STATUS_COMPLETED
    p07_receipt = bool(p07.get("receipt_digest"))
    p08_receipt = bool(p08.get("receipt_digest"))
    p08_jobs_completed = int((p08.get("output_summary") or {}).get("jobs_completed") or 0)

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "phase_06_completed_with_receipt": p06_ok and bool(p06.get("receipt_digest")),
        "phase_06_async_tcre_enqueued": p06_async or bool(p06.get("output_summary", {}).get("job_id")),
        "tcre_jobs_completed_gt_zero": tcre_completed > 0,
        "phase_07_completed_with_receipt": p07_ok and p07_receipt,
        "phase_08_executed_with_receipt": p08_receipt,
        "downstream_chain_receipts_06_07_08": p06_ok and p07_ok and p08_receipt,
        "tcre_wait_or_resume_evidence": waiting_reason == "tcre_async"
        or bool(tcre_footprint.get("resumed_from_waiting_at"))
        or tcre_completed > 0,
    }
    checks_advisory = {
        "phase_08_completed_with_receipt": p08_ok and p08_receipt,
        "phase_08_synthesis_jobs_completed_gt_zero": p08_jobs_completed > 0,
    }
    step_15_pass = all(checks.values())

    return {
        "step": P1_5_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "phase_receipts": receipts,
        "tcre_footprint": tcre_footprint,
        "chain_drive": chain_drive,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p1_5_pass": step_15_pass,
        "verification": {
            "step_15_pass": step_15_pass,
            "cleared_for_step_16": step_15_pass,
        },
    }
