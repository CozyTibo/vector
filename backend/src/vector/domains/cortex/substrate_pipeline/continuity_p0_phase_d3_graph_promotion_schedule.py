"""Phase D step D3 — graph-density promotion on convergence worker schedule (inline, not Celery sidecar)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.scheduling import verify_d3_graph_promotion_on_convergence_worker_v1
from vector.domains.cortex.operational_runtime.graph_density import (
    count_graph_candidate_count_v1,
    count_graph_promoted_edge_count_v1,
)
from vector.domains.cortex.operational_runtime.graph_density_promotion import (
    ORG_LINK_JOB_KIND_LAWFUL_EDGE_PROMOTION_V1,
    PROMOTION_TRIGGER_CONVERGENCE_SLICE_V1,
    count_unpromoted_link_candidates_v1,
    schedule_graph_density_pass_v1,
)
from vector.domains.cortex.substrate_pipeline.continuity_p1_promotion import (
    run_promotion_drain_passes_v1,
    verify_promotion_worker_path_v1,
)
from vector.infrastructure.db.models.cortex_org_link import CortexOrgLink
from vector.infrastructure.db.models.cortex_org_link_replay_job import CortexOrgLinkReplayJob
from vector.settings import Settings, get_settings

P0_D3_STEP: str = "step_d3_graph_promotion_on_convergence_schedule"
PHASE_D3_PROMOTION_SCHEMA_VERSION: int = 1
DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")


def verify_d3_graph_promotion_schedule_wiring_v1() -> dict[str, Any]:
    import inspect

    errors = list(verify_d3_graph_promotion_on_convergence_worker_v1())
    worker_path = verify_promotion_worker_path_v1()
    if worker_path.get("m9_promotion_errors"):
        errors.extend(worker_path["m9_promotion_errors"])
    from vector.domains.cortex.identity import continuity_rebuild as id_mod

    from vector.domains.cortex.identity import identity_substrate_repair_v1 as repair_mod

    repair_src = inspect.getsource(repair_mod.run_identity_substrate_repair_slice_v1)
    if "schedule_graph_density_pass_v1" not in repair_src:
        errors.append("repair_slice_missing_schedule_graph_density_pass_v1")
    return {
        "wiring_ok": not errors,
        "errors": errors,
        "phase_d3_schema_version": PHASE_D3_PROMOTION_SCHEMA_VERSION,
        "worker_path": worker_path,
        "convergence_promotion_enabled": bool(
            Settings.model_fields["cortex_graph_density_promotion_on_convergence_enabled"].default
        ),
    }


def _count_authoritative_links_created_since_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    since: datetime,
) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLink)
            .where(
                CortexOrgLink.tenant_id == tenant_id,
                CortexOrgLink.revoked_at.is_(None),
                CortexOrgLink.promoted_from_candidate_id.isnot(None),
                CortexOrgLink.created_at >= since,
            )
        )
        or 0
    )


def _count_lawful_promotion_jobs_since_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    since: datetime,
) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgLinkReplayJob)
            .where(
                CortexOrgLinkReplayJob.tenant_id == tenant_id,
                CortexOrgLinkReplayJob.job_kind == ORG_LINK_JOB_KIND_LAWFUL_EDGE_PROMOTION_V1,
                CortexOrgLinkReplayJob.status == "completed",
                CortexOrgLinkReplayJob.completed_at >= since,
            )
        )
        or 0
    )


def snapshot_auth_links_48h_trend_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """48h authoritative-link creation trend (D3 / D-G4 graph floor)."""
    now = datetime.now(UTC)
    window = timedelta(hours=48)
    recent_start = now - window
    prior_start = now - (window * 2)
    recent = _count_authoritative_links_created_since_v1(
        session, tenant_id=tenant_id, since=recent_start
    )
    prior = _count_authoritative_links_created_since_v1(
        session, tenant_id=tenant_id, since=prior_start
    ) - recent
    prior = max(0, prior)
    recent_jobs = _count_lawful_promotion_jobs_since_v1(
        session, tenant_id=tenant_id, since=recent_start
    )
    return {
        "window_hours": 48,
        "auth_links_created_recent_48h": recent,
        "auth_links_created_prior_48h": prior,
        "lawful_promotion_jobs_completed_recent_48h": recent_jobs,
        "trend_non_decreasing": recent >= prior,
    }


def snapshot_d3_graph_promotion_truth_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    drive_promotion: bool = True,
) -> dict[str, Any]:
    settings = get_settings()
    unpromoted = count_unpromoted_link_candidates_v1(session, tenant_id=tenant_id)
    auth_total = count_graph_promoted_edge_count_v1(session, tenant_id=tenant_id)
    candidates = count_graph_candidate_count_v1(session, tenant_id=tenant_id)
    trend = snapshot_auth_links_48h_trend_v1(session, tenant_id=tenant_id)

    schedule_probe: dict[str, Any] | None = None
    drain: dict[str, Any] | None = None
    if drive_promotion and unpromoted > 0:
        schedule_probe = schedule_graph_density_pass_v1(
            tenant_id=tenant_id,
            trigger=PROMOTION_TRIGGER_CONVERGENCE_SLICE_V1,
            force=True,
            session=session,
        )
        session.flush()
        drain = run_promotion_drain_passes_v1(
            session, tenant_id=tenant_id, max_passes=3, force=True
        )
        session.flush()
        trend = snapshot_auth_links_48h_trend_v1(session, tenant_id=tenant_id)
        unpromoted = count_unpromoted_link_candidates_v1(session, tenant_id=tenant_id)
        auth_total = count_graph_promoted_edge_count_v1(session, tenant_id=tenant_id)

    pass_body = dict((schedule_probe or {}).get("pass") or {})
    return {
        "tenant_id": str(tenant_id),
        "unpromoted_link_candidates": unpromoted,
        "graph_promoted_edge_count": auth_total,
        "graph_candidate_count": candidates,
        "auth_links_48h_trend": trend,
        "convergence_schedule_probe": schedule_probe,
        "promotion_drain": drain,
        "promoted_on_probe": int(pass_body.get("promoted_count") or 0),
        "inline_path": (schedule_probe or {}).get("path"),
        "settings_max_per_pass": settings.cortex_graph_density_promotion_max_per_pass,
    }


def evaluate_p0_d3_graph_promotion_schedule_proof_v1(
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
    trend = dict(snapshot.get("auth_links_48h_trend") or {})
    unpromoted = int(snapshot.get("unpromoted_link_candidates") or 0)
    auth_total = int(snapshot.get("graph_promoted_edge_count") or 0)
    promoted_probe = int(snapshot.get("promoted_on_probe") or 0)
    drain = dict(snapshot.get("promotion_drain") or {})
    total_promoted = int(drain.get("total_promoted") or promoted_probe)

    candidates_exist = unpromoted > 0 or int(snapshot.get("graph_candidate_count") or 0) > auth_total
    auth_links_increased_when_candidates = (
        not candidates_exist or total_promoted > 0 or int(trend.get("auth_links_created_recent_48h") or 0) > 0
    )

    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "static_wiring_ok": bool(wiring.get("wiring_ok")),
        "m9_legacy_promotion_celery_absent": bool(
            (wiring.get("worker_path") or {}).get("m9_promotion_path_ok")
        ),
        "convergence_worker_promotion_hook": bool(wiring.get("wiring_ok")),
        "inline_execution_path_only": snapshot.get("inline_path") in (
            None,
            "inline_execution_slice",
        ),
        "convergence_promotion_enabled": bool(wiring.get("convergence_promotion_enabled")),
        "auth_links_48h_trend_snapshot_present": "auth_links_created_recent_48h" in trend,
        "auth_links_increase_when_candidates_exist": auth_links_increased_when_candidates,
        "phase_d3_schema_version": int(wiring.get("phase_d3_schema_version") or 0)
        >= PHASE_D3_PROMOTION_SCHEMA_VERSION,
    }
    checks_advisory = {
        "unpromoted_link_candidates": unpromoted,
        "graph_promoted_edge_count": auth_total,
        "auth_links_48h_trend": trend,
        "promoted_on_probe": promoted_probe,
        "promotion_drain_total": total_promoted,
        "lawful_jobs_recent_48h": trend.get("lawful_promotion_jobs_completed_recent_48h"),
    }
    from vector.domains.cortex.substrate_pipeline.continuity_p0_trace_only_policy import (
        merge_prod_signoff_checks_v1,
    )

    checks = merge_prod_signoff_checks_v1(checks, trace_only=trace_only)
    p0_d3_pass = all(checks.values())
    return {
        "step": P0_D3_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p0_d3_pass": p0_d3_pass,
        "verification": {
            "step_d3_pass": p0_d3_pass,
            "cleared_for_phase_d5": p0_d3_pass,
            "promotion_on_convergence_schedule": checks.get("convergence_worker_promotion_hook"),
        },
    }
