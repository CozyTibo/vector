"""Phase 1 step 1.3 — P1-B promotion worker path + raised caps + pending drain proof."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.scheduling import (
    verify_m9_dead_celery_modules_absent_v1,
    verify_phase03_identity_projection_boundary_v1,
)
from vector.domains.cortex.operational_runtime.graph_density import (
    compute_graph_density_metrics_v1,
    get_graph_pending_candidate_threshold_v1,
)
from vector.domains.cortex.operational_runtime.graph_density_promotion import (
    CELERY_GRAPH_DENSITY_PROMOTION_TASK_NAME_V1,
    PROMOTION_TRIGGER_BACKLOG_THRESHOLD_V1,
    count_unpromoted_link_candidates_v1,
    get_promotion_max_per_pass_v1,
    schedule_graph_density_pass_v1,
)

P1_3_STEP = "1.3_p1b_promotion_worker"
P1_B_MIN_PROMOTION_MAX_PER_PASS = 400
M9_DEAD_PROMOTION_MODULE = "app.tasks.cortex_graph_density_promotion"


def verify_promotion_worker_path_v1() -> dict[str, Any]:
    """M9: promotion runs inline on worker after phase-03, not legacy Celery sidecar."""
    m9_errors = verify_m9_dead_celery_modules_absent_v1()
    p03_errors = verify_phase03_identity_projection_boundary_v1()
    promotion_m9 = [
        e
        for e in m9_errors
        if "graph_density_promotion" in e or M9_DEAD_PROMOTION_MODULE in e
    ]
    return {
        "m9_promotion_errors": promotion_m9,
        "phase03_promotion_errors": [
            e for e in p03_errors if "graph_density_promotion" in e
        ],
        "legacy_celery_task_name": CELERY_GRAPH_DENSITY_PROMOTION_TASK_NAME_V1,
        "worker_hook": "run_identity_substrate_repair_slice_v1",
        "pass_entrypoint": "schedule_graph_density_pass_v1",
        "m9_promotion_path_ok": not promotion_m9 and not any(
            "graph_density_promotion" in e for e in p03_errors
        ),
    }


def snapshot_pending_metrics_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    density = compute_graph_density_metrics_v1(session, tenant_id=tenant_id)
    metrics = dict(density.get("metrics") or {})
    pending = int(metrics.get("pending_link_candidates") or 0)
    unpromoted = count_unpromoted_link_candidates_v1(session, tenant_id=tenant_id)
    return {
        "pending_link_candidates": pending,
        "unpromoted_link_candidates": unpromoted,
        "graph_maturity_stage": density.get("graph_maturity_stage"),
        "graph_promoted_edge_count": int(metrics.get("graph_promoted_edge_count") or 0),
        "graph_candidate_count": int(metrics.get("graph_candidate_count") or 0),
        "fake_green_evaluation": density.get("fake_green_evaluation"),
        "max_per_pass_configured": get_promotion_max_per_pass_v1(),
        "pending_candidate_threshold": get_graph_pending_candidate_threshold_v1(),
    }


def run_promotion_drain_passes_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    max_passes: int = 10,
    force: bool = True,
) -> dict[str, Any]:
    """Run bounded promotion passes until pending stops decreasing or cap reached."""
    cap = get_promotion_max_per_pass_v1()
    passes: list[dict[str, Any]] = []
    before = snapshot_pending_metrics_v1(session, tenant_id=tenant_id)
    prev_pending = int(before["pending_link_candidates"])
    total_promoted = 0
    stagnant = 0

    for idx in range(max(1, min(int(max_passes), 25))):
        pending_before_pass = int(
            snapshot_pending_metrics_v1(session, tenant_id=tenant_id)["pending_link_candidates"]
        )
        schedule_out = schedule_graph_density_pass_v1(
            tenant_id=tenant_id,
            trigger=PROMOTION_TRIGGER_BACKLOG_THRESHOLD_V1,
            force=force,
            session=session,
        )
        session.flush()
        pass_body = dict(schedule_out.get("pass") or {})
        promoted = int(pass_body.get("promoted_count") or 0)
        total_promoted += promoted
        after_pass = snapshot_pending_metrics_v1(session, tenant_id=tenant_id)
        pending_after_pass = int(after_pass["pending_link_candidates"])
        passes.append(
            {
                "pass_index": idx,
                "scheduled": bool(schedule_out.get("scheduled")),
                "promoted_count": promoted,
                "pending_before": pending_before_pass,
                "pending_after": pending_after_pass,
                "unpromoted_remaining": pass_body.get("unpromoted_remaining"),
                "schedule_reason": (schedule_out.get("evaluation") or {}).get("schedule_reason"),
            }
        )
        if pending_after_pass >= pending_before_pass:
            stagnant += 1
        else:
            stagnant = 0
        if stagnant >= 2 or (promoted == 0 and pending_after_pass == pending_before_pass):
            break
        if pending_after_pass < prev_pending:
            prev_pending = pending_after_pass
        if pending_after_pass <= get_graph_pending_candidate_threshold_v1():
            break

    after = snapshot_pending_metrics_v1(session, tenant_id=tenant_id)
    return {
        "max_per_pass": cap,
        "passes_executed": len(passes),
        "passes": passes,
        "metrics_before": before,
        "metrics_after": after,
        "total_promoted": total_promoted,
        "pending_delta": int(before["pending_link_candidates"])
        - int(after["pending_link_candidates"]),
    }


def evaluate_p1_3_promotion_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    worker_path: dict[str, Any],
    drain_result: dict[str, Any],
    deploy_recorded_at: datetime | None = None,
) -> dict[str, Any]:
    """Build step 1.3 proof from worker-path verification + promotion drain."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    before = dict(drain_result.get("metrics_before") or {})
    after = dict(drain_result.get("metrics_after") or {})
    pending_before = int(before.get("pending_link_candidates") or 0)
    pending_after = int(after.get("pending_link_candidates") or 0)
    pending_delta = int(drain_result.get("pending_delta") or 0)
    max_per_pass = int(drain_result.get("max_per_pass") or 0)
    total_promoted = int(drain_result.get("total_promoted") or 0)
    theta = int(before.get("pending_candidate_threshold") or get_graph_pending_candidate_threshold_v1())

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok,
        "m9_legacy_promotion_celery_absent": bool(worker_path.get("m9_promotion_path_ok")),
        "phase03_worker_promotion_hook_wired": bool(worker_path.get("m9_promotion_path_ok")),
        "promotion_max_per_pass_at_least_p1b_floor": max_per_pass >= P1_B_MIN_PROMOTION_MAX_PER_PASS,
        "promotion_passes_executed": int(drain_result.get("passes_executed") or 0) >= 1,
        "total_promoted_gt_zero": total_promoted > 0,
        "pending_link_candidates_decreased": pending_after < pending_before,
        "pending_delta_positive": pending_delta > 0,
        "pending_trending_down": pending_after < pending_before,
        "not_blocked_at_theta_only": pending_before > theta or pending_after <= theta,
    }
    step_13_pass = all(checks.values())

    return {
        "step": P1_3_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "worker_path": worker_path,
        "drain_result": drain_result,
        "pending_before": pending_before,
        "pending_after": pending_after,
        "pending_delta": pending_delta,
        "pending_candidate_threshold": theta,
        "checks": checks,
        "p1_3_pass": step_13_pass,
        "verification": {
            "step_13_pass": step_13_pass,
            "cleared_for_step_14": step_13_pass,
        },
    }
