"""Phase A step A6 — synthesis job terminal transitions (orchestrator hardening)."""

from __future__ import annotations

import inspect
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_job_lifecycle import (
    P0_A6_STEP,
    PHASE_A_SYNTHESIS_TERMINAL_RUNTIME_SCHEMA_VERSION,
    reconcile_stale_queued_synthesis_jobs_v1,
    reconcile_stale_synthesis_jobs_v1,
    snapshot_synthesis_job_terminal_health_v1,
    synthesis_job_running_alert_threshold_v1,
)
from vector.domains.cortex.synthesis.synthesis_orchestrator import execute_synthesis_job_envelope_v1
from vector.domains.cortex.synthesis.synthesis_pipeline import materialize_synthesis_for_pipeline_v1

DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def verify_a6_synthesis_terminal_transitions_wiring_v1() -> dict[str, Any]:
    """Static wiring: single prepare path + symmetric terminalizers + finally guard."""
    errors: list[str] = []
    orch_src = inspect.getsource(execute_synthesis_job_envelope_v1)
    if "prepare_synthesis_job_row_for_execute_v1" not in orch_src:
        errors.append("orchestrator_missing_prepare_enqueue")
    if "find_idempotent_synthesis_job_v1" in orch_src:
        errors.append("orchestrator_still_calls_find_idempotent_inline")
    if "create_synthesis_job_row_v1" in orch_src:
        errors.append("orchestrator_still_calls_create_inline")
    if "terminalize_synthesis_job_completed_v1" not in orch_src:
        errors.append("orchestrator_missing_completed_terminalizer")
    if "ensure_synthesis_job_terminal_after_execute_v1" not in orch_src:
        errors.append("orchestrator_missing_terminal_guard_finally")
    mat_src = inspect.getsource(materialize_synthesis_for_pipeline_v1)
    if "maybe_reconcile_synthesis_jobs_on_materialize_v1" not in mat_src:
        errors.append("materialize_missing_pre_reconcile")
    from vector.domains.cortex.synthesis import synthesis_job_lifecycle as _lifecycle

    maybe_src = inspect.getsource(_lifecycle.maybe_reconcile_synthesis_jobs_on_materialize_v1)
    if (
        "reconcile_stale_queued_synthesis_jobs_v1" not in maybe_src
        and "reconcile_all_stale_synthesis_jobs_v1" not in maybe_src
    ):
        errors.append("materialize_reconcile_missing_queued_stale")
    return {"wiring_ok": not errors, "errors": errors}


def snapshot_synthesis_terminal_transitions_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    health = snapshot_synthesis_job_terminal_health_v1(session, tenant_id=tenant_id)
    return {
        "tenant_id": str(tenant_id),
        **health,
        "wiring": verify_a6_synthesis_terminal_transitions_wiring_v1(),
        "phase_a_synthesis_terminal_runtime_schema_version": (
            PHASE_A_SYNTHESIS_TERMINAL_RUNTIME_SCHEMA_VERSION
        ),
    }


def drive_synthesis_terminal_reconcile_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    running_stale_seconds: int | None = None,
    queued_stale_seconds: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    running = reconcile_stale_synthesis_jobs_v1(
        session,
        tenant_id=tenant_id,
        stale_after_seconds=running_stale_seconds,
        dry_run=dry_run,
    )
    queued = reconcile_stale_queued_synthesis_jobs_v1(
        session,
        tenant_id=tenant_id,
        stale_after_seconds=queued_stale_seconds or 3600,
        dry_run=dry_run,
    )
    after = snapshot_synthesis_job_terminal_health_v1(session, tenant_id=tenant_id)
    return {
        "running_reconcile": running,
        "queued_reconcile": queued,
        "health_after": after,
    }


def evaluate_p0_a6_synthesis_terminal_transitions_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    reconcile_drive: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step A6: orchestrator terminal transitions; running/queued inflight bounded."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    wiring = dict(snapshot.get("wiring") or {})
    threshold = int(snapshot.get("running_alert_threshold") or synthesis_job_running_alert_threshold_v1())

    health_after = dict((reconcile_drive or {}).get("health_after") or snapshot)
    hist = dict(health_after.get("histogram") or snapshot.get("histogram") or {})
    running_after = int(hist.get("running", health_after.get("running_count", 0)))
    stale_running_after = int(
        health_after.get("stale_running_count", snapshot.get("stale_running_count", 0))
    )
    stale_queued_after = int(
        health_after.get("stale_queued_count", snapshot.get("stale_queued_count", 0))
    )

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "histogram_present": bool(hist),
        "running_below_threshold": running_after < threshold,
        "no_stale_running_inflight": stale_running_after == 0,
        "no_stale_queued_inflight": stale_queued_after == 0,
        "terminal_runtime_schema_version": int(
            snapshot.get("phase_a_synthesis_terminal_runtime_schema_version") or 0
        )
        >= PHASE_A_SYNTHESIS_TERMINAL_RUNTIME_SCHEMA_VERSION,
    }
    checks_advisory = {
        "running_after": running_after,
        "queued_after": int(hist.get("queued", health_after.get("queued_count", 0))),
        "stale_running_after": stale_running_after,
        "stale_queued_after": stale_queued_after,
        "running_reconciled": int(
            ((reconcile_drive or {}).get("running_reconcile") or {}).get("reconciled_count") or 0
        ),
        "stale_queued_reconciled": int(
            ((reconcile_drive or {}).get("queued_reconcile") or {}).get("stale_queued_count") or 0
        ),
        "sql_recurrence_histogram": hist,
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    step_a6_pass = all(checks.values())
    return {
        "step": P0_A6_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "reconcile_drive": reconcile_drive,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_a6_pass": step_a6_pass,
        "verification": {
            "step_a6_pass": step_a6_pass,
            "cleared_for_phase_b": step_a6_pass,
        },
    }
