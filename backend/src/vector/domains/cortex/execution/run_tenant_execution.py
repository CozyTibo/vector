"""Single authoritative tenant execution worker — substrate phases under durable lease + FSM."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.constants import (
    CANONICAL_OUTCOME_PARTIAL_PROGRESS,
    CANONICAL_OUTCOME_TOPOLOGY_WAIT,
)
from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform
from vector.domains.cortex.execution.enqueue import enqueue_tenant_convergence_v1
from vector.domains.cortex.execution.phase_outcomes import (
    WORKER_OUTCOME_BLOCKED_RETRIEVAL,
    WORKER_OUTCOME_TIME_BUDGET,
    WORKER_OUTCOME_WAITING_TCRE,
    is_waiting_async_phase06_v1,
    store_last_phase_receipt_on_lease_v1,
    worker_outcome_label_for_phase02_continue_v1,
)
from vector.domains.cortex.execution.execution_path_telemetry import (
    EXECUTION_PATH_CONVERGENCE,
    emit_execution_path_telemetry_v1,
)
from vector.domains.cortex.execution.fsm import apply_fsm_transition_v1, fsm_state_for_phase_cursor_v1
from vector.domains.cortex.execution.dual_lane_lease import (
    is_execution_dual_lane_enabled_v1,
    should_mark_execution_lane_stalled_v1,
    sync_dual_lane_fields_on_lease_v1,
)
from vector.domains.cortex.execution.dual_lane_worker import run_dual_lane_convergence_v1
from vector.domains.cortex.execution.lease import (
    complete_convergence_lease_v1,
    mark_tenant_stalled_v1,
    mark_tenant_waiting_v1,
    schedule_convergence_retry_v1,
    touch_convergence_heartbeat_v1,
    try_acquire_convergence_lease_v1,
)
from vector.domains.cortex.execution.tenant_constants import LEASE_STATUS_DIRTY
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
    PIPELINE_TRIGGER_POST_INGESTION,
    SUBSTRATE_PIPELINE_PHASE_ORDER,
)
from vector.domains.cortex.substrate_pipeline.canonical_phase_gate import (
    canonical_needs_more_work_v1,
)
from vector.domains.cortex.substrate_pipeline.orchestrator import (
    finalize_pipeline_if_complete_v1,
    start_substrate_pipeline_run_v1,
)
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


def _store_canonical_slice_outcome_on_lease(
    lease: CortexTenantConvergenceLease,
    *,
    outcome: str,
    convergence_health: str | None = None,
) -> None:
    """Persist slice outcome hints only — no pass-fairness cursor state on the lease ."""
    detail = dict(lease.detail_json or {})
    for stale in ("canonical_pass_index", "pass_cooldown_until", "pass_topology_stall_counts"):
        detail.pop(stale, None)
    if outcome:
        detail["last_canonical_outcome"] = outcome
    if isinstance(convergence_health, str) and convergence_health.strip():
        detail["convergence_health"] = convergence_health.strip()
    lease.detail_json = detail


def _store_canonical_slice_outcome_on_lease_with_session(
    session: Session,
    lease: CortexTenantConvergenceLease,
    *,
    outcome: str,
    convergence_health: str | None = None,
) -> None:
    _store_canonical_slice_outcome_on_lease(
        lease,
        outcome=outcome,
        convergence_health=convergence_health,
    )
    sync_dual_lane_fields_on_lease_v1(session, lease=lease)


def _resolve_start_phase(lease: CortexTenantConvergenceLease) -> str:
    cursor = (lease.phase_cursor or "").strip()
    if cursor in SUBSTRATE_PIPELINE_PHASE_ORDER:
        return cursor
    return PHASE_02_CANONICAL


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
        trigger="slice_phase_start",
        pipeline_run_id=pipeline_run_id,
        detail={"phase_cursor": phase},
    )
    session.flush()


def run_tenant_convergence_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
    reason: str = "worker",
    celery_task_id: str | None = None,
) -> dict[str, Any]:
    """Execute one execution slice for a tenant; self-requeue when incomplete."""
    cfg = settings or get_settings()
    started = time.monotonic()
    budget_s = max(30, int(cfg.cortex_convergence_time_budget_seconds))

    lease, block_reason = try_acquire_convergence_lease_v1(session, tenant_id=tenant_id, settings=cfg)
    if lease is None:
        return {"tenant_id": str(tenant_id), "acquired": False, "reason": block_reason}

    emit_execution_path_telemetry_v1(
        tenant_id=tenant_id,
        execution_path=EXECUTION_PATH_CONVERGENCE,
        trigger=f"execution_slice:{reason}",
        pipeline_run_id=lease.pipeline_run_id,
        celery_task_id=celery_task_id,
        detail={
            "phase_cursor": lease.phase_cursor,
            "lease_status": lease.status,
            "fsm_state": lease.fsm_state,
        },
    )

    pipeline_run_id: uuid.UUID | None = lease.pipeline_run_id
    bundle_id: str | None = None
    graph_hash: str | None = None
    identity_trigger = f"execution:{reason}"

    try:
        if pipeline_run_id is None:
            pipeline_run_id, _created = start_substrate_pipeline_run_v1(
                session,
                tenant_id=tenant_id,
                trigger_kind=PIPELINE_TRIGGER_POST_INGESTION,
                bundle_id=None,
                celery_root_task_id=celery_task_id,
            )
            lease.pipeline_run_id = pipeline_run_id
            session.flush()

        bundle_id = resolve_default_bundle_id_for_stub_transform(session, tenant_id)
        if bundle_id is None:
            complete_convergence_lease_v1(session, lease=lease, pipeline_run_id=pipeline_run_id)
            session.commit()
            return {
                "tenant_id": str(tenant_id),
                "acquired": True,
                "outcome": "no_transformable_bundle",
                "fsm_state": lease.fsm_state,
            }

        if is_execution_dual_lane_enabled_v1():
            return run_dual_lane_convergence_v1(
                session,
                tenant_id=tenant_id,
                lease=lease,
                pipeline_run_id=pipeline_run_id,
                bundle_id=bundle_id,
                cfg=cfg,
                started=started,
                reason=reason,
                celery_task_id=celery_task_id,
            )

        phase = _resolve_start_phase(lease)
        requeue = False
        waiting_async = False

        while phase in SUBSTRATE_PIPELINE_PHASE_ORDER:
            if time.monotonic() - started >= budget_s:
                requeue = True
                break
            touch_convergence_heartbeat_v1(session, lease=lease, settings=cfg)
            _set_phase_cursor_fsm(
                session,
                lease=lease,
                phase=phase,
                pipeline_run_id=pipeline_run_id,
            )

            if phase == PHASE_02_CANONICAL:
                out = run_phase_02_canonical_v1(
                    session,
                    cfg,
                    tenant_id=tenant_id,
                    pipeline_run_id=pipeline_run_id,
                    bundle_id=bundle_id,
                    batch_limit=cfg.cortex_post_ingestion_canonical_batch_limit,
                )
                raw_summary = out.get("canonical_summary")
                summary: dict[str, Any] = raw_summary if isinstance(raw_summary, dict) else {}
                store_last_phase_receipt_on_lease_v1(lease, phase_output=out, session=session)
                if canonical_needs_more_work_v1(
                    session,
                    canonical_summary=summary,
                    tenant_id=tenant_id,
                    bundle_id=bundle_id,
                ):
                    outcome = str(summary.get("canonical_outcome") or "")
                    progress_made = bool(summary.get("progress_made"))
                    if progress_made or outcome == CANONICAL_OUTCOME_PARTIAL_PROGRESS:
                        delay = 0
                    elif outcome == CANONICAL_OUTCOME_TOPOLOGY_WAIT:
                        delay = max(
                            30,
                            int(cfg.cortex_canonical_topology_wait_cooldown_seconds),
                        )
                    else:
                        delay = 0
                    schedule_convergence_retry_v1(
                        session,
                        tenant_id=tenant_id,
                        phase_cursor=PHASE_02_CANONICAL,
                        delay_seconds=delay,
                    )
                    _store_canonical_slice_outcome_on_lease_with_session(
                        session,
                        lease,
                        outcome=outcome,
                        convergence_health=str(summary.get("convergence_health") or "") or None,
                    )
                    session.commit()
                    enqueue_tenant_convergence_v1(tenant_id, reason="canonical_continue")
                    worker_outcome = worker_outcome_label_for_phase02_continue_v1(
                        phase_output=out,
                        canonical_summary=summary,
                    )
                    return {
                        "tenant_id": str(tenant_id),
                        "acquired": True,
                        "outcome": worker_outcome,
                        "phase_outcome": out.get("outcome"),
                        "receipt_hash": out.get("receipt_hash"),
                        "canonical_outcome": outcome,
                        "convergence_health": summary.get("convergence_health"),
                        "pipeline_run_id": str(pipeline_run_id),
                        "fsm_state": lease.fsm_state,
                    }
                _store_canonical_slice_outcome_on_lease_with_session(
                    session,
                    lease,
                    outcome=str(summary.get("canonical_outcome") or ""),
                    convergence_health=str(summary.get("convergence_health") or "") or None,
                )
                phase = PHASE_03_IDENTITY
                continue

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
                session.commit()
                waiting_async = is_waiting_async_phase06_v1(p06)
                return {
                    "tenant_id": str(tenant_id),
                    "acquired": True,
                    "outcome": WORKER_OUTCOME_WAITING_TCRE,
                    "phase_outcome": p06.get("outcome"),
                    "receipt_hash": p06.get("receipt_hash"),
                    "pipeline_run_id": str(pipeline_run_id),
                    "fsm_state": lease.fsm_state,
                }

            if phase == PHASE_07_RETRIEVAL:
                out = run_phase_07_retrieval_v1(
                    session,
                    tenant_id=tenant_id,
                    pipeline_run_id=pipeline_run_id,
                )
                store_last_phase_receipt_on_lease_v1(lease, phase_output=out, session=session)
                from vector.domains.cortex.execution.blocked import (
                    apply_post_phase07_retrieval_policy_v1,
                )

                policy = apply_post_phase07_retrieval_policy_v1(
                    session,
                    tenant_id=tenant_id,
                    pipeline_run_id=pipeline_run_id,
                    phase07_output=out if isinstance(out, dict) else {},
                )
                if policy == "blocked":
                    session.commit()
                    return {
                        "tenant_id": str(tenant_id),
                        "acquired": True,
                        "outcome": WORKER_OUTCOME_BLOCKED_RETRIEVAL,
                        "phase_outcome": out.get("outcome"),
                        "receipt_hash": out.get("receipt_hash"),
                        "pipeline_run_id": str(pipeline_run_id),
                        "fsm_state": lease.fsm_state,
                        "block_reason_code": lease.block_reason_code,
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
                phase = ""
                break

        if requeue:
            schedule_convergence_retry_v1(
                session,
                tenant_id=tenant_id,
                phase_cursor=lease.phase_cursor or PHASE_02_CANONICAL,
            )
            session.commit()
            enqueue_tenant_convergence_v1(tenant_id, reason="time_budget")
            return {
                "tenant_id": str(tenant_id),
                "acquired": True,
                "outcome": WORKER_OUTCOME_TIME_BUDGET,
                "pipeline_run_id": str(pipeline_run_id),
                "fsm_state": lease.fsm_state,
            }

        if not waiting_async:
            complete_convergence_lease_v1(
                session,
                lease=lease,
                pipeline_run_id=pipeline_run_id,
                phase_cursor=None,
            )
            session.commit()
            if lease.status == LEASE_STATUS_DIRTY:
                enqueue_tenant_convergence_v1(tenant_id, reason="epoch_behind")
            return {
                "tenant_id": str(tenant_id),
                "acquired": True,
                "outcome": "converged_slice",
                "pipeline_run_id": str(pipeline_run_id),
                "lease_status": lease.status,
                "fsm_state": lease.fsm_state,
            }

    except Exception as exc:  # noqa: BLE001
        if should_mark_execution_lane_stalled_v1(lease):
            mark_tenant_stalled_v1(session, tenant_id=tenant_id, error=str(exc))
        else:
            schedule_convergence_retry_v1(
                session,
                tenant_id=tenant_id,
                phase_cursor=PHASE_02_CANONICAL,
                last_error=str(exc)[:500],
            )
            sync_dual_lane_fields_on_lease_v1(session, lease=lease)
        session.commit()
        enqueue_tenant_convergence_v1(tenant_id, reason="stalled_retry")
        _LOGGER.exception(
            "execution_worker_failed tenant_id=%s pipeline_run_id=%s",
            tenant_id,
            pipeline_run_id,
        )
        raise

    return {"tenant_id": str(tenant_id), "acquired": True, "outcome": "unknown"}


run_tenant_execution_v1 = run_tenant_convergence_v1
