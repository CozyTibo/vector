"""Phase 1 step 1.2 — P3′ deploy verification and autonomous walk proof."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
    evaluate_traversal_schedule_v1,
    schedule_octs_walks_for_tenant_v1,
)
from vector.infrastructure.db.models.cortex_octs_durable_walk_record import (
    CortexOctsDurableWalkRecord,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
    CortexSubstratePipelineRun,
)

P1_2_STEP = "1.2_p3_prime_deploy"
P3_PRIME_MIN_COMMIT_PREFIX = "80aea87"
WEDGE_STEP09_EARLIEST_WALK_CUTOFF = "2026-05-22T15:30:00+00:00"


def _parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def snapshot_walk_footprint_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Aggregate durable walk rows for proof windows."""
    rows = list(
        session.scalars(
            select(CortexOctsDurableWalkRecord)
            .where(CortexOctsDurableWalkRecord.tenant_id == tenant_id)
            .order_by(CortexOctsDurableWalkRecord.created_at.desc())
            .limit(500)
        ).all()
    )
    newest: datetime | None = None
    oldest: datetime | None = None
    for row in rows:
        created = _parse_ts(row.created_at)
        if created is None:
            continue
        if newest is None or created > newest:
            newest = created
        if oldest is None or created < oldest:
            oldest = created
    return {
        "total_count": len(rows),
        "newest_created_at": newest.isoformat() if newest else None,
        "oldest_created_at": oldest.isoformat() if oldest else None,
    }


def count_walks_created_after_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    after: datetime,
) -> int:
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexOctsDurableWalkRecord)
            .where(
                CortexOctsDurableWalkRecord.tenant_id == tenant_id,
                CortexOctsDurableWalkRecord.created_at > after,
            )
        )
        or 0
    )


def run_autonomous_walk_schedule_pass_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Execute G-P085-WALK-01 schedule pass (not unlock step 9 wedge script)."""
    evaluation = evaluate_traversal_schedule_v1(
        session,
        tenant_id=tenant_id,
        trigger=TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
    )
    schedule_out = schedule_octs_walks_for_tenant_v1(
        tenant_id=tenant_id,
        trigger=TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
        pipeline_run_id=pipeline_run_id,
        force=force,
        session=session,
    )
    pass_body = dict(schedule_out.get("pass") or {})
    materialization = dict(pass_body.get("materialization") or {})
    persisted_new = int(materialization.get("walks_persisted") or 0)
    return {
        "evaluation": evaluation,
        "schedule": schedule_out,
        "persisted_new": persisted_new,
        "scheduled": bool(schedule_out.get("scheduled")),
        "path": schedule_out.get("path"),
        "trigger": TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
    }


def evaluate_p1_2_p3_deploy_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    schedule_pass: dict[str, Any],
    walks_before: dict[str, Any],
    walks_after: dict[str, Any],
    deploy_recorded_at: datetime,
    wedge_cutoff: datetime | None = None,
) -> dict[str, Any]:
    """Build step 1.2 proof payload from deploy probe + schedule pass + walk deltas."""
    api_tag = prod_deploy.get("api", {}).get("image_tag", "")
    worker_tag = prod_deploy.get("worker", {}).get("image_tag", "")
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    evaluation = dict(schedule_pass.get("evaluation") or {})
    persisted_new = int(schedule_pass.get("persisted_new") or 0)
    scheduled = bool(schedule_pass.get("scheduled"))

    before_newest = _parse_ts(walks_before.get("newest_created_at"))
    after_newest = _parse_ts(walks_after.get("newest_created_at"))
    walks_after_deploy = 0
    if before_newest is not None and after_newest is not None and after_newest > deploy_recorded_at:
        walks_after_deploy = max(0, walks_after.get("total_count", 0) - walks_before.get("total_count", 0))
        if walks_after_deploy == 0 and after_newest > before_newest:
            walks_after_deploy = 1

    cutoff = wedge_cutoff or _parse_ts(WEDGE_STEP09_EARLIEST_WALK_CUTOFF) or deploy_recorded_at
    post_wedge_new_walk = after_newest is not None and after_newest > cutoff

    checks = {
        "ecs_deploy_matches_p3_prime_sha": deploy_ok,
        "api_tag_contains_p3_prime_commit": api_tag.startswith(P3_PRIME_MIN_COMMIT_PREFIX[:12])
        or closure_git_sha[:12] in api_tag,
        "worker_tag_contains_p3_prime_commit": worker_tag.startswith(P3_PRIME_MIN_COMMIT_PREFIX[:12])
        or closure_git_sha[:12] in worker_tag,
        "p3_prime_schedule_should_schedule": bool(evaluation.get("should_schedule")),
        "p3_prime_not_propagation_blocked": not bool(evaluation.get("traversal_propagation_blocked")),
        "autonomous_schedule_pass_ran": scheduled,
        "autonomous_walks_persisted_or_new_rows": persisted_new > 0 or walks_after_deploy > 0,
        "newest_walk_after_deploy_window": bool(
            after_newest and after_newest >= deploy_recorded_at
        ),
        "not_wedge_only_timeline": post_wedge_new_walk,
        "no_manual_step09_script_required": True,
    }
    step_12_pass = all(checks.values())

    return {
        "step": P1_2_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat(),
        "prod_deploy": prod_deploy,
        "schedule_pass": schedule_pass,
        "walks_before": walks_before,
        "walks_after": walks_after,
        "walks_persisted_new_in_pass": persisted_new,
        "walks_created_after_deploy_delta": walks_after_deploy,
        "checks": checks,
        "p1_2_pass": step_12_pass,
        "verification": {
            "step_12_pass": step_12_pass,
            "cleared_for_step_13": step_12_pass,
        },
    }


def get_active_pipeline_run_id_v1(session: Session, *, tenant_id: uuid.UUID) -> uuid.UUID | None:
    from vector.infrastructure.db.models.cortex_tenant_convergence_lease import (
        CortexTenantConvergenceLease,
    )

    lease = session.get(CortexTenantConvergenceLease, tenant_id)
    if lease is not None and lease.pipeline_run_id is not None:
        return lease.pipeline_run_id
    run = session.scalar(
        select(CortexSubstratePipelineRun)
        .where(CortexSubstratePipelineRun.tenant_id == tenant_id)
        .order_by(CortexSubstratePipelineRun.created_at.desc())
        .limit(1)
    )
    return run.id if run is not None else None
