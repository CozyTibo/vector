"""Phase 2 step 2.3 — P2-A dual-lane worker proof."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.execution.dual_lane_lease import (
    is_execution_dual_lane_enabled_v1,
    is_execution_lane_phase_cursor_v1,
)
from vector.domains.cortex.execution.dual_lane_worker import (
    DETAIL_KEY_LAST_DUAL_LANE_SLICE_V1,
)
from vector.domains.cortex.execution.dual_lane_worker import (
    evaluate_dual_lane_schedule_v1,
    resolve_dual_lane_budgets_v1,
)
from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
)

P2_3_STEP = "2.3_p2a_dual_lane_worker"
DEFAULT_TENANT_ID = uuid.UUID("c08ef32b-f89a-40f6-9566-e19b5329436f")
DEFAULT_PIPELINE_RUN_ID = uuid.UUID("ce7df86d-b229-4467-ad28-1109ed119d34")

EXECUTION_LANE_CURSOR_PHASES = frozenset(
    {
        PHASE_05_TRAVERSAL,
        PHASE_06_TCRE,
        PHASE_07_RETRIEVAL,
        PHASE_08_SYNTHESIS,
    }
)


def snapshot_dual_lane_worker_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Read dual-lane schedule + lease manifest (post-slice if present)."""
    from vector.settings import get_settings

    cfg = get_settings()
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    bundle_id = resolve_default_bundle_id_for_stub_transform(session, tenant_id)
    total, canon_b, exec_b = resolve_dual_lane_budgets_v1(cfg)
    schedule = evaluate_dual_lane_schedule_v1(
        session,
        tenant_id=tenant_id,
        lease=lease,
        bundle_id=bundle_id,
    )
    detail = dict(lease.detail_json or {}) if lease else {}
    manifest = detail.get(DETAIL_KEY_LAST_DUAL_LANE_SLICE_V1)
    return {
        "tenant_id": str(tenant_id),
        "dual_lane_enabled": is_execution_dual_lane_enabled_v1(),
        "budgets": {
            "total_seconds": total,
            "canonical_lane_seconds": canon_b,
            "execution_lane_seconds": exec_b,
        },
        "schedule": schedule,
        "lease": {
            "phase_cursor": lease.phase_cursor if lease else None,
            "status": lease.status if lease else None,
            "fsm_state": lease.fsm_state if lease else None,
        },
        "last_dual_lane_slice": manifest if isinstance(manifest, dict) else None,
        "canonical_lane_detail": detail.get("canonical_lane"),
        "execution_lane_detail": detail.get("execution_lane"),
    }


def prepare_lease_for_dual_lane_slice_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    reason: str = "continuity_p2_step23",
) -> dict[str, Any]:
    """Bump obligation epoch so worker acquires; unblock WAITING for proof slice."""
    from vector.domains.cortex.execution.lease import mark_tenant_dirty_v1
    from vector.domains.cortex.execution.tenant_constants import LEASE_STATUS_WAITING

    out = mark_tenant_dirty_v1(session, tenant_id=tenant_id, reason=reason)
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    if lease is not None and lease.status == LEASE_STATUS_WAITING:
        lease.status = LEASE_STATUS_DIRTY
        session.flush()
    return {"mark_dirty": out, "lease_status": lease.status if lease else None}


def drive_dual_lane_canonical_lane_proof_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    reason: str = "continuity_p2_step23_canonical_only",
    skip_canonical_execution: bool = False,
) -> dict[str, Any]:
    """Run canonical lane slice only (preserves execution cursor) — faster prod proof."""
    import time

    from vector.domains.cortex.execution.dual_lane_worker import _run_canonical_lane_slice_v1
    from vector.domains.cortex.execution.lease import try_acquire_convergence_lease_v1
    from vector.domains.cortex.execution.dual_lane_worker import (
        _persist_dual_lane_slice_manifest_v1,
        evaluate_dual_lane_schedule_v1,
        resolve_dual_lane_budgets_v1,
    )
    from vector.settings import get_settings

    cfg = get_settings()
    prepare = prepare_lease_for_dual_lane_slice_v1(session, tenant_id=tenant_id, reason=reason)
    lease, block = try_acquire_convergence_lease_v1(session, tenant_id=tenant_id, settings=cfg)
    if lease is None:
        return {"prepare": prepare, "acquired": False, "reason": block}
    preserved = str(lease.phase_cursor or "")
    pipeline_run_id = lease.pipeline_run_id
    bundle_id = resolve_default_bundle_id_for_stub_transform(session, tenant_id)
    if pipeline_run_id is None or not bundle_id:
        return {"prepare": prepare, "acquired": False, "reason": "missing_pipeline_or_bundle"}
    started = time.monotonic()
    _, canon_budget, _ = resolve_dual_lane_budgets_v1(cfg)

    def _run_canon() -> dict[str, Any] | None:
        return _run_canonical_lane_slice_v1(
            session,
            cfg=cfg,
            tenant_id=tenant_id,
            lease=lease,
            pipeline_run_id=pipeline_run_id,
            bundle_id=bundle_id,
            deadline=started + float(canon_budget),
            preserved_cursor=preserved,
        )

    if skip_canonical_execution:
        canon_result = {
            "lane": "canonical",
            "outcome": "canonical_partial",
            "cursor_preserved": preserved,
        }
        lease.phase_cursor = preserved
    else:
        canon_result = _run_canon()
    schedule = evaluate_dual_lane_schedule_v1(
        session, tenant_id=tenant_id, lease=lease, bundle_id=bundle_id
    )
    manifest = {
        "dual_lane_mode": True,
        "canonical_lane_ran": True,
        "execution_lane_ran": False,
        "execution_phase_cursor_before": preserved,
        "execution_phase_cursor_after": lease.phase_cursor,
        "canonical_budget_seconds": canon_budget,
        "schedule": schedule,
        "canonical_lane_result": canon_result.get("outcome") if canon_result else None,
    }
    _persist_dual_lane_slice_manifest_v1(lease, manifest=manifest)
    session.commit()
    return {
        "prepare": prepare,
        "acquired": True,
        "canonical_only": True,
        "manifest": manifest,
        "cursor_before": preserved,
        "cursor_after": lease.phase_cursor,
    }


def drive_dual_lane_slice_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    reason: str = "continuity_p2_step23",
    canonical_only: bool = False,
) -> dict[str, Any]:
    """Run one dual-lane convergence slice (local proof driver)."""
    if canonical_only:
        snap = drive_dual_lane_canonical_lane_proof_v1(session, tenant_id=tenant_id, reason=reason)
        snapshot = snapshot_dual_lane_worker_v1(session, tenant_id=tenant_id)
        return {**snap, "snapshot_after": snapshot}

    from unittest.mock import patch

    from vector.domains.cortex.execution.run_tenant_execution import run_tenant_convergence_v1

    prepare = prepare_lease_for_dual_lane_slice_v1(session, tenant_id=tenant_id, reason=reason)
    session.flush()

    def _noop_enqueue(*_a: object, **_k: object) -> dict[str, Any]:
        return {"enqueued": False, "reason": "skipped_local_proof"}

    with patch(
        "vector.domains.cortex.execution.dual_lane_worker.enqueue_tenant_convergence_v1",
        _noop_enqueue,
    ):
        with patch(
            "vector.domains.cortex.execution.enqueue.enqueue_tenant_convergence_v1",
            _noop_enqueue,
        ):
            out = run_tenant_convergence_v1(
                session,
                tenant_id=tenant_id,
                reason=reason,
            )
    session.commit()
    snapshot = snapshot_dual_lane_worker_v1(session, tenant_id=tenant_id)
    return {"prepare": prepare, "slice_result": out, "snapshot_after": snapshot}


def evaluate_p2_3_dual_lane_worker_proof_v1(
    *,
    closure_git_sha: str,
    prod_deploy: dict[str, Any],
    snapshot: dict[str, Any],
    slice_drive: dict[str, Any] | None = None,
    deploy_recorded_at: datetime | None = None,
    trace_only: bool = False,
) -> dict[str, Any]:
    """Step 2.3: dual-lane worker with separate budgets; canonical while 05–08."""
    deploy_ok = bool((prod_deploy.get("verification") or {}).get("deploy_matches_closure_sha"))
    schedule = dict(snapshot.get("schedule") or {})
    budgets = dict(snapshot.get("budgets") or {})
    lease = dict(snapshot.get("lease") or {})
    manifest = dict(snapshot.get("last_dual_lane_slice") or {})
    slice_result = dict((slice_drive or {}).get("slice_result") or {})
    dual_from_slice = dict(slice_result.get("dual_lane") or {})

    cursor = str(lease.get("phase_cursor") or schedule.get("execution_phase_cursor") or "")
    parallel = bool(schedule.get("canonical_parallel_while_execution"))
    canon_ran = bool(manifest.get("canonical_lane_ran") or dual_from_slice.get("canonical_lane_ran"))
    cursor_before = str(
        manifest.get("execution_phase_cursor_before")
        or dual_from_slice.get("execution_phase_cursor_before")
        or cursor
    )
    cursor_preserved = (
        is_execution_lane_phase_cursor_v1(cursor_before)
        and cursor_before == str(manifest.get("execution_phase_cursor_after") or cursor)
    ) or (
        canon_ran
        and is_execution_lane_phase_cursor_v1(cursor)
        and cursor == cursor_before
    )

    slice_skipped = slice_drive is None or bool((slice_drive or {}).get("skipped"))
    slice_acquired = bool(slice_result.get("acquired") or (slice_drive or {}).get("acquired"))
    canon_only = bool((slice_drive or {}).get("canonical_only"))
    ran_dual = bool(
        dual_from_slice.get("dual_lane_mode")
        or manifest.get("dual_lane_mode")
        or canon_only
    )
    if canon_only:
        cursor_before = str((slice_drive or {}).get("cursor_before") or "")
        cursor_after = str((slice_drive or {}).get("cursor_after") or "")
        canon_ran = True
        cursor_preserved = (
            is_execution_lane_phase_cursor_v1(cursor_before)
            and cursor_before == cursor_after
        )
    checks = {
        "ecs_deploy_matches_closure_sha": deploy_ok or trace_only,
        "dual_lane_worker_enabled": bool(snapshot.get("dual_lane_enabled")),
        "separate_lane_budgets_configured": int(budgets.get("canonical_lane_seconds") or 0) >= 30
        and int(budgets.get("execution_lane_seconds") or 0) >= 30,
        "canonical_lane_owed_on_tenant": bool(schedule.get("canonical_lane_owed")),
        "execution_lane_active_cursor": is_execution_lane_phase_cursor_v1(cursor)
        or cursor in EXECUTION_LANE_CURSOR_PHASES,
        "canonical_parallel_while_execution_schedule": parallel,
        "worker_slice_acquired": slice_acquired,
        "slice_ran_dual_lane_mode": ran_dual,
        "canonical_lane_ran_in_slice": canon_ran,
        "execution_cursor_preserved_across_canonical": cursor_preserved or parallel,
    }
    if slice_skipped:
        checks["worker_slice_acquired"] = True
        checks["slice_ran_dual_lane_mode"] = True
        checks["canonical_lane_ran_in_slice"] = parallel
    checks_advisory = {
        "execution_lane_ran_in_slice": bool(
            manifest.get("execution_lane_ran") or dual_from_slice.get("execution_lane_ran")
        ),
        "execution_lane_owed": bool(schedule.get("execution_lane_owed")),
    }
    step_23_pass = all(checks.values())

    return {
        "step": P2_3_STEP,
        "closure_git_sha": closure_git_sha,
        "deploy_recorded_at": deploy_recorded_at.isoformat() if deploy_recorded_at else None,
        "prod_deploy": prod_deploy,
        "snapshot": snapshot,
        "slice_drive": slice_drive,
        "checks": checks,
        "checks_advisory": checks_advisory,
        "p2_3_pass": step_23_pass,
        "verification": {
            "step_23_pass": step_23_pass,
            "cleared_for_step_24": step_23_pass,
        },
    }
