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
from vector.domains.cortex.canonical.forward_progress.pass_fairness import (
    parse_pass_cooldown_until,
    parse_pass_topology_stall_counts,
)
from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform
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


def _canonical_pass_index_from_lease(lease: CortexTenantConvergenceLease) -> int:
    detail = lease.detail_json if isinstance(lease.detail_json, dict) else {}
    raw = detail.get("canonical_pass_index")
    if raw is None:
        return 0
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def _store_canonical_pass_index_on_lease(lease: CortexTenantConvergenceLease, pass_index: int) -> None:
    detail = dict(lease.detail_json or {})
    detail["canonical_pass_index"] = int(pass_index)
    lease.detail_json = detail


def _store_pass_fairness_on_lease(lease: CortexTenantConvergenceLease, summary: dict[str, Any]) -> None:
    detail = dict(lease.detail_json or {})
    cooldowns = summary.get("pass_cooldown_until")
    if isinstance(cooldowns, dict):
        detail["pass_cooldown_until"] = cooldowns
    stalls = summary.get("pass_topology_stall_counts")
    if isinstance(stalls, dict):
        detail["pass_topology_stall_counts"] = stalls
    health = summary.get("convergence_health")
    if isinstance(health, str) and health.strip():
        detail["convergence_health"] = health.strip()
    lease.detail_json = detail


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
                pass_idx = _canonical_pass_index_from_lease(lease)
                lease_detail = lease.detail_json if isinstance(lease.detail_json, dict) else {}
                out = run_phase_02_canonical_v1(
                    session,
                    cfg,
                    tenant_id=tenant_id,
                    pipeline_run_id=pipeline_run_id,
                    bundle_id=bundle_id,
                    batch_limit=cfg.cortex_post_ingestion_canonical_batch_limit,
                    pass_index=pass_idx,
                    pass_cooldowns=parse_pass_cooldown_until(lease_detail),
                    pass_stall_counts=parse_pass_topology_stall_counts(lease_detail),
                )
                raw_summary = out.get("canonical_summary")
                summary: dict[str, Any] = raw_summary if isinstance(raw_summary, dict) else {}
                next_pass = summary.get("pass_index_next")
                if isinstance(next_pass, int):
                    _store_canonical_pass_index_on_lease(lease, next_pass)
                _store_pass_fairness_on_lease(lease, summary)
                if canonical_needs_more_work_v1(session, canonical_summary=summary, tenant_id=tenant_id):
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
                    detail = dict(lease.detail_json or {})
                    detail["last_canonical_outcome"] = outcome
                    lease.detail_json = detail
                    session.commit()
                    enqueue_tenant_convergence_v1(tenant_id, reason="canonical_continue")
                    worker_outcome = (
                        "canonical_topology_wait"
                        if outcome == CANONICAL_OUTCOME_TOPOLOGY_WAIT and not progress_made
                        else "canonical_partial"
                    )
                    return {
                        "tenant_id": str(tenant_id),
                        "acquired": True,
                        "outcome": worker_outcome,
                        "canonical_outcome": outcome,
                        "convergence_health": summary.get("convergence_health"),
                        "pipeline_run_id": str(pipeline_run_id),
                        "fsm_state": lease.fsm_state,
                    }
                _store_canonical_pass_index_on_lease(lease, 0)
                phase = PHASE_03_IDENTITY
                continue

            if phase == PHASE_03_IDENTITY:
                run_phase_03_identity_v1(
                    session,
                    tenant_id=tenant_id,
                    pipeline_run_id=pipeline_run_id,
                    bundle_id=bundle_id,
                    identity_substrate_trigger=identity_trigger,
                )
                phase = PHASE_04_GRAPH
                continue

            if phase == PHASE_04_GRAPH:
                out = run_phase_04_graph_v1(session, tenant_id=tenant_id, pipeline_run_id=pipeline_run_id)
                graph_hash = out.get("graph_projection_stable_hash_sha256")
                phase = PHASE_05_TRAVERSAL
                continue

            if phase == PHASE_05_TRAVERSAL:
                run_phase_05_traversal_v1(
                    session,
                    tenant_id=tenant_id,
                    pipeline_run_id=pipeline_run_id,
                    graph_projection_stable_hash=graph_hash,
                )
                phase = PHASE_06_TCRE
                continue

            if phase == PHASE_06_TCRE:
                run_phase_06_tcre_v1(session, tenant_id=tenant_id, pipeline_run_id=pipeline_run_id)
                mark_tenant_waiting_v1(
                    session,
                    tenant_id=tenant_id,
                    pipeline_run_id=pipeline_run_id,
                    phase_cursor=PHASE_07_RETRIEVAL,
                    waiting_reason="tcre_async",
                )
                session.commit()
                waiting_async = True
                return {
                    "tenant_id": str(tenant_id),
                    "acquired": True,
                    "outcome": "waiting_on_tcre",
                    "pipeline_run_id": str(pipeline_run_id),
                    "fsm_state": lease.fsm_state,
                }

            if phase == PHASE_07_RETRIEVAL:
                out = run_phase_07_retrieval_v1(
                    session,
                    tenant_id=tenant_id,
                    pipeline_run_id=pipeline_run_id,
                )
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
                        "outcome": "blocked_retrieval_starvation",
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
                run_phase_08_synthesis_v1(
                    session,
                    tenant_id=tenant_id,
                    pipeline_run_id=pipeline_run_id,
                )
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
                "outcome": "time_budget_requeue",
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
        mark_tenant_stalled_v1(session, tenant_id=tenant_id, error=str(exc))
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
