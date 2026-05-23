"""P2-A — dual-lane convergence worker (canonical budget A + execution budget B)."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.candidate_selection import (
    untreated_routable_drainable_exists_v1,
)
from vector.domains.cortex.canonical.forward_progress.constants import (
    CANONICAL_OUTCOME_PARTIAL_PROGRESS,
    CANONICAL_OUTCOME_TOPOLOGY_WAIT,
)
from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform
from vector.domains.cortex.execution.dual_lane_lease import (
    is_execution_dual_lane_enabled_v1,
    is_execution_lane_phase_cursor_v1,
    should_mark_execution_lane_stalled_v1,
    sync_dual_lane_fields_on_lease_v1,
)
from vector.domains.cortex.execution.enqueue import enqueue_tenant_convergence_v1
from vector.domains.cortex.execution.execution_path_telemetry import (
    EXECUTION_PATH_CONVERGENCE,
    emit_execution_path_telemetry_v1,
)
from vector.domains.cortex.execution.fsm import apply_fsm_transition_v1, fsm_state_for_phase_cursor_v1
from vector.domains.cortex.execution.lease import (
    complete_convergence_lease_v1,
    mark_tenant_stalled_v1,
    mark_tenant_waiting_v1,
    schedule_convergence_retry_v1,
    touch_convergence_heartbeat_v1,
)
from vector.domains.cortex.execution.phase_outcomes import (
    WORKER_OUTCOME_BLOCKED_RETRIEVAL,
    WORKER_OUTCOME_CANONICAL_PARTIAL,
    WORKER_OUTCOME_CANONICAL_TOPOLOGY_WAIT,
    WORKER_OUTCOME_TIME_BUDGET,
    WORKER_OUTCOME_WAITING_TCRE,
    is_waiting_async_phase06_v1,
    store_last_phase_receipt_on_lease_v1,
    worker_outcome_label_for_phase02_continue_v1,
)
from vector.domains.cortex.execution.tenant_constants import (
    FSM_BLOCKED,
    LEASE_STATUS_DIRTY,
    LEASE_STATUS_WAITING,
)
from vector.domains.cortex.substrate_pipeline.canonical_phase_gate import (
    canonical_needs_more_work_v1,
    untreated_raw_exists_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
    SUBSTRATE_PIPELINE_PHASE_ORDER,
)
from vector.domains.cortex.substrate_pipeline.orchestrator import finalize_pipeline_if_complete_v1
from vector.domains.cortex.substrate_pipeline.phase_runners import (
    run_phase_02_canonical_v1,
    run_phase_03_identity_v1,
    run_phase_04_graph_v1,
    run_phase_05_traversal_v1,
    run_phase_06_tcre_v1,
    run_phase_07_retrieval_v1,
    run_phase_08_synthesis_v1,
)
from vector.infrastructure.db.models.cortex_tenant_convergence_lease import CortexTenantConvergenceLease
from vector.settings import Settings, get_settings

_LOGGER = logging.getLogger(__name__)

DETAIL_KEY_LAST_DUAL_LANE_SLICE_V1: Final[str] = "last_dual_lane_slice"
WORKER_OUTCOME_DUAL_LANE_SLICE_V1: Final[str] = "dual_lane_slice"


def is_dual_lane_execution_on_topology_wait_enabled_v1(*, settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    return bool(getattr(cfg, "cortex_dual_lane_run_execution_on_topology_wait", True))


def resolve_canonical_lane_budget_for_slice_v1(
    cfg: Settings,
    *,
    base_canonical_budget: int,
    execution_lane_owed: bool,
) -> int:
    """Cap canonical drain when execution heartbeat (03–08) is owed (R1)."""
    canon = max(30, int(base_canonical_budget))
    if not execution_lane_owed:
        return canon
    cap = int(getattr(cfg, "cortex_dual_lane_canonical_cap_when_execution_owed_seconds", 90) or 90)
    return max(30, min(canon, max(30, cap)))


def resolve_dual_lane_budgets_v1(cfg: Settings) -> tuple[int, int, int]:
    """Return (total, canonical_budget_seconds, execution_budget_seconds)."""
    total = max(30, int(cfg.cortex_convergence_time_budget_seconds))
    canon_cfg = int(getattr(cfg, "cortex_execution_canonical_lane_budget_seconds", 0) or 0)
    exec_cfg = int(getattr(cfg, "cortex_execution_execution_lane_budget_seconds", 0) or 0)
    if canon_cfg <= 0 and exec_cfg <= 0:
        canon = max(60, min(180, total // 3))
        exec_b = max(60, total - canon)
        return total, canon, exec_b
    canon = max(30, canon_cfg) if canon_cfg > 0 else max(60, total // 3)
    exec_b = max(30, exec_cfg) if exec_cfg > 0 else max(60, total - canon)
    if canon + exec_b > total:
        scale = total / float(canon + exec_b)
        canon = max(30, int(canon * scale))
        exec_b = max(30, total - canon)
    return total, canon, exec_b


def canonical_lane_owed_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str,
) -> bool:
    """True when canonical drain still has routable or raw backlog (parallel to execution lane)."""
    if untreated_raw_exists_v1(session, tenant_id=tenant_id):
        return True
    return untreated_routable_drainable_exists_v1(
        session, tenant_id=tenant_id, bundle_id=bundle_id
    )


def execution_lane_owed_v1(lease: CortexTenantConvergenceLease) -> bool:
    """True when execution substrate phases 03–08 should advance (not blocked on async TCRE wait)."""
    if (lease.block_reason_code or "").strip():
        return False
    if str(lease.fsm_state or "") == FSM_BLOCKED:
        return False
    detail = dict(lease.detail_json or {})
    if lease.status == LEASE_STATUS_WAITING and detail.get("waiting_reason") == "tcre_async":
        return False
    return is_execution_lane_phase_cursor_v1(lease.phase_cursor)


def _persist_dual_lane_slice_manifest_v1(
    lease: CortexTenantConvergenceLease,
    *,
    manifest: dict[str, Any],
) -> None:
    detail = dict(lease.detail_json or {})
    detail[DETAIL_KEY_LAST_DUAL_LANE_SLICE_V1] = manifest
    lease.detail_json = detail


def _store_canonical_outcome(
    session: Session,
    lease: CortexTenantConvergenceLease,
    *,
    outcome: str,
    convergence_health: str | None,
) -> None:
    detail = dict(lease.detail_json or {})
    for stale in ("canonical_pass_index", "pass_cooldown_until", "pass_topology_stall_counts"):
        detail.pop(stale, None)
    if outcome:
        detail["last_canonical_outcome"] = outcome
    if convergence_health:
        detail["convergence_health"] = convergence_health
    lease.detail_json = detail
    sync_dual_lane_fields_on_lease_v1(session, lease=lease)


def _set_phase_cursor_fsm(
    session: Session,
    *,
    lease: CortexTenantConvergenceLease,
    phase: str,
    pipeline_run_id: uuid.UUID | None,
) -> None:
    lease.phase_cursor = phase
    apply_fsm_transition_v1(
        session,
        lease=lease,
        to_state=fsm_state_for_phase_cursor_v1(phase),
        trigger="dual_lane_slice_phase",
        pipeline_run_id=pipeline_run_id,
        detail={"phase_cursor": phase, "dual_lane": True},
    )
    session.flush()


def _run_canonical_lane_slice_v1(
    session: Session,
    *,
    cfg: Settings,
    tenant_id: uuid.UUID,
    lease: CortexTenantConvergenceLease,
    pipeline_run_id: uuid.UUID,
    bundle_id: str,
    deadline: float,
    preserved_cursor: str,
) -> dict[str, Any] | None:
    """Budget A — one phase 02 slice; does not move execution ``phase_cursor`` off 03–08."""
    if time.monotonic() >= deadline:
        return None
    touch_convergence_heartbeat_v1(session, lease=lease, settings=cfg)
    out = run_phase_02_canonical_v1(
        session,
        cfg,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        bundle_id=bundle_id,
        batch_limit=cfg.cortex_post_ingestion_canonical_batch_limit,
    )
    summary = out.get("canonical_summary") if isinstance(out.get("canonical_summary"), dict) else {}
    store_last_phase_receipt_on_lease_v1(lease, phase_output=out, session=session)
    outcome = str(summary.get("canonical_outcome") or "")
    _store_canonical_outcome(
        session,
        lease,
        outcome=outcome,
        convergence_health=str(summary.get("convergence_health") or "") or None,
    )
    if preserved_cursor != PHASE_02_CANONICAL:
        lease.phase_cursor = preserved_cursor
        session.flush()
    if canonical_needs_more_work_v1(
        session,
        canonical_summary=summary,
        tenant_id=tenant_id,
        bundle_id=bundle_id,
    ):
        delay = 0
        if outcome == CANONICAL_OUTCOME_TOPOLOGY_WAIT:
            base_delay = max(30, int(cfg.cortex_canonical_topology_wait_cooldown_seconds))
            if not bool(summary.get("progress_made")):
                storm_floor = max(
                    base_delay,
                    int(getattr(cfg, "cortex_canonical_deferral_retry_storm_cooldown_seconds", 300) or 300),
                )
                delay = storm_floor
            else:
                delay = base_delay
        elif not (bool(summary.get("progress_made")) or outcome == CANONICAL_OUTCOME_PARTIAL_PROGRESS):
            delay = 0
        schedule_convergence_retry_v1(
            session,
            tenant_id=tenant_id,
            phase_cursor=preserved_cursor if is_execution_lane_phase_cursor_v1(preserved_cursor) else PHASE_02_CANONICAL,
            delay_seconds=delay,
        )
        worker_outcome = worker_outcome_label_for_phase02_continue_v1(
            phase_output=out,
            canonical_summary=summary,
        )
        return {
            "lane": "canonical",
            "outcome": worker_outcome,
            "canonical_outcome": outcome,
            "phase_output": out,
            "cursor_preserved": preserved_cursor,
        }
    return {
        "lane": "canonical",
        "outcome": "canonical_lane_complete_for_slice",
        "canonical_outcome": outcome,
        "phase_output": out,
        "cursor_preserved": preserved_cursor,
    }


def _run_execution_lane_slice_v1(
    session: Session,
    *,
    cfg: Settings,
    tenant_id: uuid.UUID,
    lease: CortexTenantConvergenceLease,
    pipeline_run_id: uuid.UUID,
    bundle_id: str,
    deadline: float,
    reason: str,
) -> dict[str, Any]:
    """Budget B — advance execution lane from ``phase_cursor`` (never re-run phase 02 here)."""
    phase = (lease.phase_cursor or PHASE_03_IDENTITY).strip()
    if phase == PHASE_02_CANONICAL or phase not in SUBSTRATE_PIPELINE_PHASE_ORDER:
        phase = PHASE_03_IDENTITY
    graph_hash: str | None = None
    identity_trigger = f"execution:{reason}"
    requeue = False
    waiting_async = False

    while phase in SUBSTRATE_PIPELINE_PHASE_ORDER:
        if time.monotonic() >= deadline:
            requeue = True
            break
        touch_convergence_heartbeat_v1(session, lease=lease, settings=cfg)
        _set_phase_cursor_fsm(
            session,
            lease=lease,
            phase=phase,
            pipeline_run_id=pipeline_run_id,
        )

        if phase == PHASE_03_IDENTITY:
            p03 = run_phase_03_identity_v1(
                session,
                tenant_id=tenant_id,
                pipeline_run_id=pipeline_run_id,
                bundle_id=bundle_id,
                identity_substrate_trigger=identity_trigger,
            )
            store_last_phase_receipt_on_lease_v1(lease, phase_output=p03, session=session)
            phase = PHASE_04_GRAPH
            continue

        if phase == PHASE_04_GRAPH:
            out = run_phase_04_graph_v1(session, tenant_id=tenant_id, pipeline_run_id=pipeline_run_id)
            store_last_phase_receipt_on_lease_v1(lease, phase_output=out, session=session)
            from vector.domains.cortex.substrate_pipeline.post_ingestion_fresh_pipeline_run import (
                resolve_pipeline_run_id_after_phase04_v1,
            )

            pipeline_run_id, switch = resolve_pipeline_run_id_after_phase04_v1(
                out,
                current_pipeline_run_id=pipeline_run_id,
            )
            if switch.get("switched"):
                lease.pipeline_run_id = pipeline_run_id
                session.flush()
                graph_hash = out.get("graph_projection_stable_hash_sha256")
                phase = PHASE_03_IDENTITY
                continue
            graph_hash = out.get("graph_projection_stable_hash_sha256")
            phase = PHASE_05_TRAVERSAL
            continue

        if phase == PHASE_05_TRAVERSAL:
            p05 = run_phase_05_traversal_v1(
                session,
                tenant_id=tenant_id,
                pipeline_run_id=pipeline_run_id,
                graph_projection_stable_hash=graph_hash,
            )
            store_last_phase_receipt_on_lease_v1(lease, phase_output=p05, session=session)
            phase = PHASE_06_TCRE
            continue

        if phase == PHASE_06_TCRE:
            p06 = run_phase_06_tcre_v1(session, tenant_id=tenant_id, pipeline_run_id=pipeline_run_id)
            store_last_phase_receipt_on_lease_v1(lease, phase_output=p06, session=session)
            mark_tenant_waiting_v1(
                session,
                tenant_id=tenant_id,
                pipeline_run_id=pipeline_run_id,
                phase_cursor=PHASE_07_RETRIEVAL,
                waiting_reason="tcre_async",
            )
            sync_dual_lane_fields_on_lease_v1(session, lease=lease)
            from vector.domains.cortex.execution.phase06_contract import (
                assert_pipe085_chain_after_phase06_legal_v1,
            )

            assert_pipe085_chain_after_phase06_legal_v1(
                session,
                tenant_id=tenant_id,
                pipeline_run_id=pipeline_run_id,
            )
            waiting_async = is_waiting_async_phase06_v1(p06)
            return {
                "lane": "execution",
                "outcome": WORKER_OUTCOME_WAITING_TCRE,
                "phase_outcome": p06.get("outcome"),
                "receipt_hash": p06.get("receipt_hash"),
                "waiting_async": waiting_async,
            }

        if phase == PHASE_07_RETRIEVAL:
            out = run_phase_07_retrieval_v1(
                session,
                tenant_id=tenant_id,
                pipeline_run_id=pipeline_run_id,
            )
            store_last_phase_receipt_on_lease_v1(lease, phase_output=out, session=session)
            from vector.domains.cortex.execution.blocked import apply_post_phase07_retrieval_policy_v1

            policy = apply_post_phase07_retrieval_policy_v1(
                session,
                tenant_id=tenant_id,
                pipeline_run_id=pipeline_run_id,
                phase07_output=out if isinstance(out, dict) else {},
            )
            if policy == "blocked":
                return {
                    "lane": "execution",
                    "outcome": WORKER_OUTCOME_BLOCKED_RETRIEVAL,
                    "phase_outcome": out.get("outcome"),
                    "receipt_hash": out.get("receipt_hash"),
                }
            if policy == "retry_07":
                phase = PHASE_07_RETRIEVAL
                continue
            phase = PHASE_08_SYNTHESIS
            continue

        if phase == PHASE_08_SYNTHESIS:
            p08 = run_phase_08_synthesis_v1(
                session,
                tenant_id=tenant_id,
                pipeline_run_id=pipeline_run_id,
            )
            store_last_phase_receipt_on_lease_v1(lease, phase_output=p08, session=session)
            finalize_pipeline_if_complete_v1(session, pipeline_run_id=pipeline_run_id)
            return {
                "lane": "execution",
                "outcome": "converged_slice",
                "phase_outcome": p08.get("outcome"),
                "receipt_hash": p08.get("receipt_hash"),
            }

    if requeue:
        schedule_convergence_retry_v1(
            session,
            tenant_id=tenant_id,
            phase_cursor=lease.phase_cursor or PHASE_03_IDENTITY,
        )
        return {"lane": "execution", "outcome": WORKER_OUTCOME_TIME_BUDGET}
    return {"lane": "execution", "outcome": "execution_lane_idle"}


def evaluate_dual_lane_schedule_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    lease: CortexTenantConvergenceLease | None,
    bundle_id: str | None,
) -> dict[str, Any]:
    """Inspect which lanes are owed (read-only schedule surface)."""
    owed_canonical = False
    if bundle_id:
        owed_canonical = canonical_lane_owed_v1(session, tenant_id=tenant_id, bundle_id=bundle_id)
    owed_execution = execution_lane_owed_v1(lease) if lease is not None else False
    cursor = str(lease.phase_cursor or "") if lease else ""
    return {
        "dual_lane_enabled": is_execution_dual_lane_enabled_v1(),
        "canonical_lane_owed": owed_canonical,
        "execution_lane_owed": owed_execution,
        "execution_phase_cursor": cursor,
        "canonical_parallel_while_execution": owed_canonical
        and is_execution_lane_phase_cursor_v1(cursor),
    }


def run_dual_lane_convergence_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    lease: CortexTenantConvergenceLease,
    pipeline_run_id: uuid.UUID,
    bundle_id: str,
    cfg: Settings,
    started: float,
    reason: str,
    celery_task_id: str | None = None,
) -> dict[str, Any]:
    """P2-A worker path: canonical slice (budget A) then execution slice (budget B)."""
    from vector.domains.cortex.synthesis.synthesis_job_lifecycle import (
        maybe_reconcile_synthesis_jobs_on_materialize_v1,
    )

    maybe_reconcile_synthesis_jobs_on_materialize_v1(session, tenant_id=tenant_id)

    total_budget, canon_budget, exec_budget = resolve_dual_lane_budgets_v1(cfg)
    preserved_cursor = str(lease.phase_cursor or PHASE_02_CANONICAL)
    exec_start = started

    schedule = evaluate_dual_lane_schedule_v1(
        session,
        tenant_id=tenant_id,
        lease=lease,
        bundle_id=bundle_id,
    )
    execution_owed = bool(schedule.get("execution_lane_owed"))
    canon_budget_effective = resolve_canonical_lane_budget_for_slice_v1(
        cfg,
        base_canonical_budget=canon_budget,
        execution_lane_owed=execution_owed,
    )
    canon_deadline = started + float(canon_budget_effective)
    exec_deadline = started + float(total_budget)

    manifest: dict[str, Any] = {
        "dual_lane_mode": True,
        "total_budget_seconds": total_budget,
        "canonical_budget_seconds": canon_budget,
        "canonical_budget_effective_seconds": canon_budget_effective,
        "execution_budget_seconds": exec_budget,
        "execution_phase_cursor_before": preserved_cursor,
        "canonical_lane_ran": False,
        "execution_lane_ran": False,
        "execution_on_topology_wait_enabled": is_dual_lane_execution_on_topology_wait_enabled_v1(
            settings=cfg
        ),
        "schedule": schedule,
    }

    emit_execution_path_telemetry_v1(
        tenant_id=tenant_id,
        execution_path=EXECUTION_PATH_CONVERGENCE,
        trigger=f"dual_lane_slice:{reason}",
        pipeline_run_id=pipeline_run_id,
        celery_task_id=celery_task_id,
        detail=manifest,
    )

    from vector.domains.cortex.operational_runtime.graph_density_promotion import (
        schedule_graph_density_promotion_on_convergence_worker_v1,
    )

    manifest["graph_density_promotion_schedule"] = (
        schedule_graph_density_promotion_on_convergence_worker_v1(
            session,
            tenant_id=tenant_id,
            convergence_reason=f"dual_lane:{reason}",
        )
    )

    canon_result: dict[str, Any] | None = None
    if schedule["canonical_lane_owed"]:
        canon_result = _run_canonical_lane_slice_v1(
            session,
            cfg=cfg,
            tenant_id=tenant_id,
            lease=lease,
            pipeline_run_id=pipeline_run_id,
            bundle_id=bundle_id,
            deadline=canon_deadline,
            preserved_cursor=preserved_cursor,
        )
        manifest["canonical_lane_ran"] = True
        manifest["canonical_lane_result"] = (
            canon_result.get("outcome") if canon_result else None
        )
        sync_dual_lane_fields_on_lease_v1(session, lease=lease)
        canon_outcome = str(canon_result.get("outcome") or "") if canon_result else ""
        manifest["canonical_topology_nonblocking"] = canon_outcome in (
            WORKER_OUTCOME_CANONICAL_TOPOLOGY_WAIT,
            WORKER_OUTCOME_CANONICAL_PARTIAL,
        )
        if (
            not is_dual_lane_execution_on_topology_wait_enabled_v1(settings=cfg)
            and canon_outcome
            in (WORKER_OUTCOME_CANONICAL_TOPOLOGY_WAIT, WORKER_OUTCOME_CANONICAL_PARTIAL)
            and not schedule["execution_lane_owed"]
        ):
            manifest["execution_phase_cursor_after"] = lease.phase_cursor
            _persist_dual_lane_slice_manifest_v1(lease, manifest=manifest)
            session.commit()
            enqueue_tenant_convergence_v1(tenant_id, reason="dual_lane_canonical_continue")
            return {
                "tenant_id": str(tenant_id),
                "acquired": True,
                "outcome": canon_outcome,
                "dual_lane": manifest,
                "pipeline_run_id": str(pipeline_run_id),
                "fsm_state": lease.fsm_state,
            }

    exec_start = max(exec_start, time.monotonic())
    exec_deadline = exec_start + float(exec_budget)
    if schedule["execution_lane_owed"]:
        manifest["execution_lane_ran"] = True
        exec_result = _run_execution_lane_slice_v1(
            session,
            cfg=cfg,
            tenant_id=tenant_id,
            lease=lease,
            pipeline_run_id=pipeline_run_id,
            bundle_id=bundle_id,
            deadline=exec_deadline,
            reason=reason,
        )
        manifest["execution_lane_result"] = exec_result.get("outcome")
        manifest["execution_phase_cursor_after"] = lease.phase_cursor
        sync_dual_lane_fields_on_lease_v1(session, lease=lease)
        _persist_dual_lane_slice_manifest_v1(lease, manifest=manifest)
        outcome = str(exec_result.get("outcome") or WORKER_OUTCOME_DUAL_LANE_SLICE_V1)
        if outcome == WORKER_OUTCOME_WAITING_TCRE:
            session.commit()
            return {
                "tenant_id": str(tenant_id),
                "acquired": True,
                "outcome": WORKER_OUTCOME_WAITING_TCRE,
                "dual_lane": manifest,
                "pipeline_run_id": str(pipeline_run_id),
                "fsm_state": lease.fsm_state,
            }
        if outcome == WORKER_OUTCOME_BLOCKED_RETRIEVAL:
            session.commit()
            return {
                "tenant_id": str(tenant_id),
                "acquired": True,
                "outcome": WORKER_OUTCOME_BLOCKED_RETRIEVAL,
                "dual_lane": manifest,
                "pipeline_run_id": str(pipeline_run_id),
                "fsm_state": lease.fsm_state,
            }
        if outcome == WORKER_OUTCOME_TIME_BUDGET:
            session.commit()
            enqueue_tenant_convergence_v1(tenant_id, reason="dual_lane_time_budget")
            return {
                "tenant_id": str(tenant_id),
                "acquired": True,
                "outcome": WORKER_OUTCOME_TIME_BUDGET,
                "dual_lane": manifest,
                "pipeline_run_id": str(pipeline_run_id),
            }
        if outcome == "converged_slice":
            if bool(getattr(cfg, "cortex_execution_heartbeat_reset_cursor_to_phase05", True)):
                _set_phase_cursor_fsm(
                    session,
                    lease=lease,
                    phase=PHASE_05_TRAVERSAL,
                    pipeline_run_id=pipeline_run_id,
                )
                manifest["heartbeat_cursor_reset_to"] = PHASE_05_TRAVERSAL
            complete_convergence_lease_v1(
                session,
                lease=lease,
                pipeline_run_id=pipeline_run_id,
                phase_cursor=lease.phase_cursor,
            )
            session.commit()
            if lease.status == LEASE_STATUS_DIRTY:
                enqueue_tenant_convergence_v1(tenant_id, reason="epoch_behind")
            else:
                enqueue_tenant_convergence_v1(tenant_id, reason="heartbeat_continue")
            return {
                "tenant_id": str(tenant_id),
                "acquired": True,
                "outcome": "converged_slice",
                "dual_lane": manifest,
                "pipeline_run_id": str(pipeline_run_id),
            }

    manifest["execution_phase_cursor_after"] = lease.phase_cursor
    _persist_dual_lane_slice_manifest_v1(lease, manifest=manifest)
    sync_dual_lane_fields_on_lease_v1(session, lease=lease)
    session.commit()
    if schedule["canonical_lane_owed"] or schedule["execution_lane_owed"]:
        enqueue_tenant_convergence_v1(tenant_id, reason="dual_lane_continue")
    return {
        "tenant_id": str(tenant_id),
        "acquired": True,
        "outcome": WORKER_OUTCOME_DUAL_LANE_SLICE_V1,
        "dual_lane": manifest,
        "pipeline_run_id": str(pipeline_run_id),
        "fsm_state": lease.fsm_state,
    }
