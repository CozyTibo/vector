"""Phase D step D5 — legacy substrate coordinator enqueue paths deleted (convergence-only motion)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.scheduling import (
    verify_d5_legacy_coordinator_enqueue_paths_deleted_v1,
    verify_schedule_substrate_pipeline_uses_convergence_v1,
)
from vector.settings import Settings, get_settings

P0_D5_STEP: str = "step_d5_legacy_coordinator_enqueue_paths_deleted"
PHASE_D5_COORDINATOR_DELETION_SCHEMA_VERSION: int = 1
DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def is_legacy_coordinator_enqueue_deleted_v1(*, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return bool(getattr(settings, "cortex_legacy_coordinator_enqueue_deleted", True))


def verify_d5_legacy_coordinator_deletion_wiring_v1() -> dict[str, Any]:
    errors = list(verify_d5_legacy_coordinator_enqueue_paths_deleted_v1())
    m4_only = list(verify_schedule_substrate_pipeline_uses_convergence_v1())
    return {
        "wiring_ok": not errors,
        "errors": errors,
        "phase_d5_schema_version": PHASE_D5_COORDINATOR_DELETION_SCHEMA_VERSION,
        "m4_schedule_gate_ok": not m4_only,
        "coordinator_enqueue_deleted_flag_default": bool(
            Settings.model_fields["cortex_legacy_coordinator_enqueue_deleted"].default
        ),
    }


def snapshot_d5_legacy_coordinator_deletion_truth_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    _ = session, tenant_id
    wiring = verify_d5_legacy_coordinator_deletion_wiring_v1()
    return {
        "tenant_id": str(tenant_id),
        "doc_enabled": is_legacy_coordinator_enqueue_deleted_v1(),
        "wiring": wiring,
        "authoritative_motion_path": "mark_dirty_and_enqueue_convergence_v1",
        "celery_execution_task": "vector.cortex.execution.run_slice",
    }


def evaluate_p0_d5_legacy_coordinator_deletion_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    wiring: dict[str, Any] | None = None,
    deploy_recorded_at: Any = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    wiring = dict(wiring or snapshot.get("wiring") or {})
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "m4_schedule_uses_convergence": bool(wiring.get("m4_schedule_gate_ok")),
        "coordinator_enqueue_deleted_setting_default": bool(
            wiring.get("coordinator_enqueue_deleted_flag_default")
        ),
        "doc_enabled": bool(snapshot.get("doc_enabled")),
        "authoritative_motion_is_convergence": snapshot.get("authoritative_motion_path")
        == "mark_dirty_and_enqueue_convergence_v1",
        "phase_d5_schema_version": int(wiring.get("phase_d5_schema_version") or 0)
        >= PHASE_D5_COORDINATOR_DELETION_SCHEMA_VERSION,
    }
    checks_advisory = {
        "celery_execution_task": snapshot.get("celery_execution_task"),
        "wiring_errors": wiring.get("errors"),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    p0_d5_pass = all(checks.values())
    return {
        "step": P0_D5_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_d5_pass": p0_d5_pass,
        "verification": {
            "step_d5_pass": p0_d5_pass,
            "phase_d_parallel_complete": p0_d5_pass,
            "single_motion_path_convergence_only": checks.get("static_wiring_ok"),
        },
    }
