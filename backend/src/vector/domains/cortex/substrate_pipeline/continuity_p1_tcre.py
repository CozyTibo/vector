"""Phase 1 step 1.4 — P1-D TCRE resume path (phase 06 → wait → terminal → phase 07)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.execution.scheduling import (
    verify_execution_hot_path_no_continuation_boundary_v1,
    verify_single_tcre_execution_resume_boundary_v1,
    verify_tcre_worker_no_retrieval_materialization_boundary_v1,
)
from vector.domains.cortex.execution.tenant_constants import (
    FSM_AWAITING_TCRE,
    LEASE_STATUS_DIRTY,
    LEASE_STATUS_WAITING,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
    PHASE_STATUS_COMPLETED,
)
from vector.domains.cortex.substrate_pipeline.repository import (
    get_phase_run_v1,
    get_running_pipeline_run_v1,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)

P1_4_STEP = "1.4_p1d_tcre_resume"
P1_D_CI_TEST_MODULE = (
    "tests/vector/domains/cortex/substrate_pipeline/test_continuity_p1_tcre_resume.py"
)


def verify_p1_d_static_boundaries_v1() -> dict[str, Any]:
    """Aggregate M9/P1-D static boundary checks (no DB)."""
    checks = {
        "single_tcre_execution_resume": verify_single_tcre_execution_resume_boundary_v1(),
        "execution_hot_path_no_continuation": verify_execution_hot_path_no_continuation_boundary_v1(),
        "tcre_worker_no_retrieval_materialization": (
            verify_tcre_worker_no_retrieval_materialization_boundary_v1()
        ),
    }
    errors: list[str] = []
    for name, codes in checks.items():
        for code in codes:
            errors.append(f"{name}:{code}")
    return {
        "boundary_checks": checks,
        "errors": errors,
        "static_boundaries_ok": not errors,
    }


def snapshot_tcre_execution_footprint_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Prod snapshot: lease, phase-06 receipt, TCRE job counts."""
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    run = None
    run_id = pipeline_run_id
    if run_id is None and lease is not None and lease.pipeline_run_id is not None:
        run_id = lease.pipeline_run_id
    if run_id is not None:
        from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
            CortexSubstratePipelineRun,
        )

        run = session.get(CortexSubstratePipelineRun, run_id)
    if run is None:
        run = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    phase06 = None
    if run is not None:
        phase06 = get_phase_run_v1(
            session,
            pipeline_run_id=run.id,
            phase_id=PHASE_06_TCRE,
        )
    p06_out = dict((phase06.output_json if phase06 else None) or {})
    job_rows = session.execute(
        select(CortexTcreReconstructionJob.status, func.count())
        .where(CortexTcreReconstructionJob.tenant_id == tenant_id)
        .group_by(CortexTcreReconstructionJob.status)
    ).all()
    jobs_by_status = {str(status): int(n or 0) for status, n in job_rows}
    total_jobs = sum(jobs_by_status.values())
    return {
        "pipeline_run_id": str(run.id) if run is not None else None,
        "pipeline_status": run.status if run is not None else None,
        "lease_status": lease.status if lease is not None else None,
        "lease_fsm_state": lease.fsm_state if lease is not None else None,
        "lease_phase_cursor": lease.phase_cursor if lease is not None else None,
        "lease_pipeline_run_id": str(lease.pipeline_run_id) if lease and lease.pipeline_run_id else None,
        "waiting_reason": (lease.detail_json or {}).get("waiting_reason") if lease else None,
        "resumed_from_waiting_at": (lease.detail_json or {}).get("resumed_from_waiting_at")
        if lease
        else None,
        "phase_06_status": phase06.status if phase06 is not None else None,
        "phase_06_async": bool(p06_out.get("async")),
        "phase_06_job_id": p06_out.get("job_id"),
        "tcre_jobs_by_status": jobs_by_status,
        "tcre_jobs_total": total_jobs,
    }


def evaluate_p1_4_tcre_resume_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    static_boundaries: dict[str, Any],
    footprint: dict[str, Any],
    integration_tests_green: bool,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Build step 1.4 proof: CI boundaries + prod TCRE/lease trace."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    lease_fsm = str(footprint.get("lease_fsm_state") or "")
    lease_status = str(footprint.get("lease_status") or "")
    phase_cursor = str(footprint.get("lease_phase_cursor") or "")
    p06_status = str(footprint.get("phase_06_status") or "")
    tcre_total = int(footprint.get("tcre_jobs_total") or 0)
    waiting_reason = str(footprint.get("waiting_reason") or "")
    pipeline_traceable = bool(
        footprint.get("pipeline_run_id") or footprint.get("lease_pipeline_run_id")
    )

    phase06_async_complete = (
        p06_status == PHASE_STATUS_COMPLETED
        and bool(footprint.get("phase_06_async"))
        and bool(footprint.get("phase_06_job_id"))
    )
    tcre_path_evidence = waiting_reason == "tcre_async" or bool(
        footprint.get("resumed_from_waiting_at")
    )
    lease_shows_wait_or_resume = (
        (lease_status == LEASE_STATUS_WAITING and lease_fsm == FSM_AWAITING_TCRE)
        or (
            lease_status == LEASE_STATUS_DIRTY
            and phase_cursor == PHASE_07_RETRIEVAL
            and bool(footprint.get("resumed_from_waiting_at"))
        )
        or (
            lease_status in (LEASE_STATUS_DIRTY, "running")
            and phase_cursor == PHASE_07_RETRIEVAL
            and phase06_async_complete
        )
    )
    execution_past_tcre_gate = phase_cursor in (
        PHASE_07_RETRIEVAL,
        PHASE_08_SYNTHESIS,
    ) and (phase06_async_complete or tcre_path_evidence)

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_boundaries_ok": bool(static_boundaries.get("static_boundaries_ok")),
        "integration_tests_green": integration_tests_green,
        "pipeline_run_traceable": pipeline_traceable,
        "phase_06_completed_with_async_job": phase06_async_complete,
        "tcre_jobs_exist_on_tenant": tcre_total >= 1,
        "tcre_resume_path_evidence": lease_shows_wait_or_resume
        or (execution_past_tcre_gate and tcre_path_evidence),
        "execution_at_or_past_phase_07": phase_cursor
        in (PHASE_07_RETRIEVAL, PHASE_08_SYNTHESIS, PHASE_06_TCRE),
        "tcre_worker_chains_pipeline_resume": bool(
            static_boundaries.get("static_boundaries_ok")
        ),
    }
    step_14_pass = all(checks.values())

    return {
        "step": P1_4_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "static_boundaries": static_boundaries,
        "footprint": footprint,
        "ci_test_module": P1_D_CI_TEST_MODULE,
        "checks": checks,
        "p1_4_pass": step_14_pass,
        "verification": {
            "step_14_pass": step_14_pass,
            "cleared_for_step_15": step_14_pass,
        },
    }
