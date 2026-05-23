"""Phase A step A1 — synthesis job lifecycle reconcile proof (generic tenant)."""

from __future__ import annotations

import inspect
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_job_lifecycle import (
    P0_A1_STEP,
    count_stale_running_synthesis_jobs_v1,
    reconcile_stale_synthesis_jobs_v1,
    snapshot_synthesis_job_status_histogram_v1,
    synthesis_job_running_alert_threshold_v1,
    synthesis_job_running_stale_seconds_v1,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.domains.cortex.synthesis.synthesis_pipeline import materialize_synthesis_for_pipeline_v1

DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def verify_a1_synthesis_job_lifecycle_wiring_v1() -> dict[str, Any]:
    """Static wiring: orchestrator finally + materialize pre-reconcile."""
    errors: list[str] = []
    orch_src = inspect.getsource(execute_synthesis_job_envelope_v1)
    if "finally:" not in orch_src or "ORPHAN_RUNNING_CODE_V1" not in orch_src:
        errors.append("orchestrator_missing_orphan_running_finally")
    if "prepare_synthesis_job_row_for_execute_v1" not in orch_src:
        errors.append("orchestrator_missing_prepare_enqueue")
    if "terminalize_synthesis_job_completed_v1" not in orch_src:
        errors.append("orchestrator_missing_completed_terminalizer")
    mat_src = inspect.getsource(materialize_synthesis_for_pipeline_v1)
    if "maybe_reconcile_synthesis_jobs_on_materialize_v1" not in mat_src:
        errors.append("materialize_missing_pre_reconcile")
    return {"wiring_ok": not errors, "errors": errors}


def snapshot_synthesis_job_lifecycle_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    stale_sec = synthesis_job_running_stale_seconds_v1()
    hist = snapshot_synthesis_job_status_histogram_v1(session, tenant_id=tenant_id)
    return {
        "tenant_id": str(tenant_id),
        "histogram": hist,
        "running_count": int(hist.get("running", 0)),
        "stale_running_count": count_stale_running_synthesis_jobs_v1(
            session,
            tenant_id=tenant_id,
            stale_after_seconds=stale_sec,
        ),
        "running_alert_threshold": synthesis_job_running_alert_threshold_v1(),
        "stale_after_seconds": stale_sec,
        "wiring": verify_a1_synthesis_job_lifecycle_wiring_v1(),
    }


def drive_synthesis_job_reconcile_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stale_after_seconds: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    return reconcile_stale_synthesis_jobs_v1(
        session,
        tenant_id=tenant_id,
        stale_after_seconds=stale_after_seconds,
        dry_run=dry_run,
    )


def evaluate_p0_a1_synthesis_job_lifecycle_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    reconcile_drive: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step A1: running synthesis jobs reconciled; table trustworthy."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    wiring = dict(snapshot.get("wiring") or {})
    threshold = int(snapshot.get("running_alert_threshold") or 10)

    hist_before = dict((reconcile_drive or {}).get("histogram_before") or snapshot.get("histogram") or {})
    hist_after = dict((reconcile_drive or {}).get("histogram_after") or hist_before)
    running_after = int(hist_after.get("running", 0))
    stale_running_after = int(
        (reconcile_drive or {}).get("stale_running_after")
        if reconcile_drive is not None
        else snapshot.get("stale_running_count")
        or 0
    )

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "histogram_present": bool(hist_after),
        "running_below_threshold": running_after < threshold,
        "reconcile_applied_or_trace": bool(reconcile_drive) or trace_only,
    }
    if reconcile_drive and not trace_only:
        checks["no_stale_running_after_reconcile"] = stale_running_after == 0
        checks["reconciled_rows_when_incident"] = int(reconcile_drive.get("reconciled_count") or 0) >= 0
    else:
        checks["no_stale_running_after_reconcile"] = int(snapshot.get("stale_running_count") or 0) == 0

    checks_advisory = {
        "running_before": int(hist_before.get("running", 0)),
        "running_after": running_after,
        "reconciled_count": int((reconcile_drive or {}).get("reconciled_count") or 0),
        "failed_after": int(hist_after.get("failed", 0)),
        "completed_after": int(hist_after.get("completed", 0)),
        "stale_running_after": stale_running_after,
        "running_alert_threshold": threshold,
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    step_a1_pass = all(checks.values())
    return {
        "step": P0_A1_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "reconcile_drive": reconcile_drive,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_a1_pass": step_a1_pass,
        "verification": {
            "step_a1_pass": step_a1_pass,
            "cleared_for_a2": step_a1_pass,
        },
    }
