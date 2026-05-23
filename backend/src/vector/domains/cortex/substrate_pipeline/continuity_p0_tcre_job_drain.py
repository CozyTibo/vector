"""Phase A step A3 — TCRE stale queued job drain proof (generic tenant)."""

from __future__ import annotations

import inspect
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.tcre_job_lifecycle import (
    P0_A3_STEP,
    count_stale_queued_tcre_jobs_v1,
    drain_stale_queued_tcre_jobs_v1,
    snapshot_tcre_job_status_histogram_v1,
    tcre_job_queued_stale_seconds_v1,
)
from vector.domains.cortex.execution.tcre_resume import on_tcre_job_terminal_for_execution_v1
from vector.domains.cortex.reasoning.runtime.reasoning_runtime_orchestrator import (
    execute_tcre_reconstruction_job_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p1_tcre import (
    snapshot_tcre_execution_footprint_v1,
    verify_p1_d_static_boundaries_v1,
)

DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def verify_a3_tcre_job_drain_wiring_v1() -> dict[str, Any]:
    """Static wiring: inline drain + resume_convergence_from_waiting path."""
    errors: list[str] = []
    drain_src = inspect.getsource(drain_stale_queued_tcre_jobs_v1)
    if "execute_tcre_reconstruction_job_v1" not in drain_src:
        errors.append("drain_missing_inline_execute")
    if "on_tcre_job_terminal_for_execution_v1" not in drain_src:
        errors.append("drain_missing_tcre_resume_hook")
    resume_src = inspect.getsource(on_tcre_job_terminal_for_execution_v1)
    if "resume_convergence_from_waiting_v1" not in resume_src:
        errors.append("tcre_resume_missing_lease_resume")
    exec_src = inspect.getsource(execute_tcre_reconstruction_job_v1)
    if "finally:" not in exec_src or "ORPHAN_RUNNING_CODE_V1" not in exec_src:
        errors.append("tcre_execute_missing_orphan_running_finally")
    p1d = verify_p1_d_static_boundaries_v1()
    if not p1d.get("static_boundaries_ok"):
        errors.extend([f"p1d:{e}" for e in p1d.get("errors") or []])
    return {"wiring_ok": not errors, "errors": errors, "p1_d_boundaries": p1d}


def snapshot_tcre_job_drain_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    stale_sec = tcre_job_queued_stale_seconds_v1()
    hist = snapshot_tcre_job_status_histogram_v1(session, tenant_id=tenant_id)
    footprint = snapshot_tcre_execution_footprint_v1(session, tenant_id=tenant_id)
    return {
        "tenant_id": str(tenant_id),
        "histogram": hist,
        "stale_queued_count": count_stale_queued_tcre_jobs_v1(
            session,
            tenant_id=tenant_id,
            stale_after_seconds=stale_sec,
        ),
        "queued_stale_seconds": stale_sec,
        "execution_footprint": footprint,
        "wiring": verify_a3_tcre_job_drain_wiring_v1(),
    }


def drive_tcre_queued_drain_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stale_after_seconds: int | None = None,
    dry_run: bool = False,
    enqueue_convergence: bool = True,
) -> dict[str, Any]:
    return drain_stale_queued_tcre_jobs_v1(
        session,
        tenant_id=tenant_id,
        stale_after_seconds=stale_after_seconds,
        dry_run=dry_run,
        enqueue_convergence=enqueue_convergence,
    )


def evaluate_p0_a3_tcre_job_drain_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    drain_drive: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step A3: no queued TCRE jobs older than threshold; drain path exercised."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    wiring = dict(snapshot.get("wiring") or {})
    stale_sec = int(snapshot.get("queued_stale_seconds") or 3600)
    stale_after = int(
        (drain_drive or {}).get("stale_queued_after")
        if drain_drive is not None
        else snapshot.get("stale_queued_count")
        or 0
    )
    hist_after = dict((drain_drive or {}).get("histogram_after") or snapshot.get("histogram") or {})
    queued_after = int(hist_after.get("queued", 0))

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "histogram_present": bool(hist_after),
        "no_stale_queued_after_drain": stale_after == 0,
        "queued_count_acceptable": queued_after == 0 or stale_after == 0,
        "drain_applied_or_trace": bool(drain_drive) or trace_only,
    }
    if drain_drive and not trace_only:
        checks["resume_trace_present"] = any(
            bool((row.get("resume") or {}).get("resumed"))
            for row in (drain_drive.get("drained_jobs") or [])
            if row.get("status") == "completed"
        ) or int(drain_drive.get("jobs_drained") or 0) == 0
        checks["lease_resume_recorded"] = any(
            (row.get("resume") or {}).get("lease") is not None
            for row in (drain_drive.get("drained_jobs") or [])
        ) or int(drain_drive.get("jobs_drained") or 0) == 0
    else:
        checks["resume_trace_present"] = True

    checks_advisory = {
        "stale_queued_before": int((drain_drive or {}).get("stale_queued_before") or 0),
        "stale_queued_after": stale_after,
        "jobs_drained": int((drain_drive or {}).get("jobs_drained") or 0),
        "queued_after": queued_after,
        "completed_after": int(hist_after.get("completed", 0)),
        "lease_phase_cursor": (snapshot.get("execution_footprint") or {}).get("lease_phase_cursor"),
    }
    step_a3_pass = all(checks.values())
    return {
        "step": P0_A3_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "drain_drive": drain_drive,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_a3_pass": step_a3_pass,
        "verification": {
            "step_a3_pass": step_a3_pass,
            "cleared_for_a4": step_a3_pass,
        },
    }
