"""Canonical downstream progression owner for ingest → substrate → retrieval → synthesis.

Preserves async phase boundaries; drives eventual lawful convergence via continuations,
bounded retries, and periodic progression ticks (**PIPE-085-PROG-CLOSE**).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import PHASE085_NORMATIVE_TREE_V1
from vector.domains.cortex.retrieval.retrieval_index_materialization import (
    get_published_index_epoch_v1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    count_synthesis_eligible_scopes_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
    PHASE_STATUS_COMPLETED,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_QUEUED,
    PHASE_STATUS_RUNNING,
    PHASE_STATUS_SKIPPED,
    PIPELINE_STATUS_COMPLETED,
    PIPELINE_STATUS_RUNNING,
    SUBSTRATE_PIPELINE_PHASE_ORDER,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_COMPLETED,
    CONTINUATION_STATUS_RESUMED,
    CONTINUATION_STATUS_STALLED,
    CONTINUATION_STATUS_WAITING,
    WAITING_ON_TCRE_COMPLETION,
    WAITING_ON_TRAVERSAL_COMPLETION,
    get_continuation_for_pipeline_v1,
    mark_continuation_completed_v1,
    resume_pipeline_after_tcre_completion_v1,
    touch_continuation_heartbeat_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import (
    get_phase_run_v1,
    get_running_pipeline_run_v1,
)
from vector.infrastructure.db.models.cortex_pipeline_continuation import (
    CortexPipelineContinuationState,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePipelineRun
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob

_LOGGER = logging.getLogger(__name__)

PHASE085_SUBSTRATE_PROGRESSION_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_SUBSTRATE_PROGRESSION_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-substrate-continuity-doctrine.md"
)

GP085_PROG_CLOSE_GATE_ID_V1: Final[str] = "G-P085-PROG-CLOSE"

CELERY_SUBSTRATE_PROGRESSION_TICK_TASK_NAME_V1: Final[str] = (
    "vector.cortex.operational_runtime.substrate_progression_tick"
)

PROGRESSION_OWNER_ID_V1: Final[str] = "SubstrateOperationalProgressionCoordinator"

PROGRESSION_TRIGGER_INGEST_V1: Final[str] = "ingest"
PROGRESSION_TRIGGER_TCRE_COMPLETED_V1: Final[str] = "tcre_job_completed"
PROGRESSION_TRIGGER_RETRIEVAL_PUBLISHED_V1: Final[str] = "retrieval_published"
PROGRESSION_TRIGGER_TRAVERSAL_PASS_V1: Final[str] = "traversal_pass"
PROGRESSION_TRIGGER_WATCHDOG_V1: Final[str] = "progression_watchdog"
PROGRESSION_TRIGGER_PROGRESSION_TICK_V1: Final[str] = "progression_tick"
PROGRESSION_TRIGGER_MANUAL_V1: Final[str] = "manual"

MAX_RETRIEVAL_MATERIALIZATION_RETRIES_V1: Final[int] = 3
MAX_PROGRESSION_ACTIONS_PER_INVOCATION_V1: Final[int] = 8

TENANT_PROGRESSION_CLASS_PROGRESSING_V1: Final[str] = "progressing"
TENANT_PROGRESSION_CLASS_STALLED_V1: Final[str] = "stalled"
TENANT_PROGRESSION_CLASS_DEGRADED_V1: Final[str] = "degraded"
TENANT_PROGRESSION_CLASS_WAITING_UPSTREAM_V1: Final[str] = "waiting_upstream"
TENANT_PROGRESSION_CLASS_OPERATIONALLY_ALIVE_V1: Final[str] = "operationally_alive"
TENANT_PROGRESSION_CLASS_IDLE_V1: Final[str] = "idle"


def classify_retrieval_materialization_outcome_v1(
    *,
    entries_materialized: int,
    entry_count: int,
    tcre_candidates: int,
    walks_candidates: int,
    org_link_candidates: int,
) -> str:
    """Truthful retrieval outcome — avoid fake-green on empty publish with upstream work pending."""
    upstream = int(tcre_candidates) + int(walks_candidates) + int(org_link_candidates)
    accepted = int(entries_materialized or entry_count or 0)
    if accepted > 0:
        return "progressing"
    if upstream > 0:
        return "operational_starvation"
    return "healthy_idle"


def _phase_status_map_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for phase_id in SUBSTRATE_PIPELINE_PHASE_ORDER:
        pr = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=phase_id)
        out[phase_id] = pr.status if pr is not None else "missing"
    return out


def _first_incomplete_phase_v1(phase_status: dict[str, str]) -> str | None:
    for phase_id in SUBSTRATE_PIPELINE_PHASE_ORDER:
        st = phase_status.get(phase_id)
        if st in (PHASE_STATUS_COMPLETED, PHASE_STATUS_SKIPPED):
            continue
        return phase_id
    return None


def _retrieval_retry_count_v1(run: CortexSubstratePipelineRun) -> int:
    summary = dict(run.summary_json or {})
    prog = dict(summary.get("progression") or {})
    return int(prog.get("retrieval_materialization_retries") or 0)


def _increment_retrieval_retry_v1(session: Session, *, run: CortexSubstratePipelineRun) -> int:
    summary = dict(run.summary_json or {})
    prog = dict(summary.get("progression") or {})
    n = int(prog.get("retrieval_materialization_retries") or 0) + 1
    prog["retrieval_materialization_retries"] = n
    prog["last_retrieval_retry_at"] = datetime.now(UTC).isoformat()
    summary["progression"] = prog
    run.summary_json = summary
    session.flush()
    return n


def _record_progression_receipt_v1(
    session: Session,
    *,
    run: CortexSubstratePipelineRun,
    action: str,
    outcome: str,
    detail: dict[str, Any] | None = None,
) -> None:
    summary = dict(run.summary_json or {})
    receipts = list(summary.get("progression_receipts") or [])
    receipts.append(
        {
            "action": action,
            "outcome": outcome,
            "at": datetime.now(UTC).isoformat(),
            "detail": dict(detail or {}),
        }
    )
    summary["progression_receipts"] = receipts[-32:]
    run.summary_json = summary
    session.flush()


def build_substrate_operational_progression_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_substrate_progression_runtime_schema_version": int(
            PHASE085_SUBSTRATE_PROGRESSION_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_SUBSTRATE_PROGRESSION_SPEC_REF_V1,
        "primary_gate_id": GP085_PROG_CLOSE_GATE_ID_V1,
        "progression_owner_id": PROGRESSION_OWNER_ID_V1,
        "celery_progression_tick_task": CELERY_SUBSTRATE_PROGRESSION_TICK_TASK_NAME_V1,
        "entrypoint": "continue_substrate_operational_progression_v1",
        "status_entrypoint": "build_substrate_progression_status_v1",
        "max_retrieval_materialization_retries": MAX_RETRIEVAL_MATERIALIZATION_RETRIES_V1,
    }


def build_substrate_progression_status_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Operator-facing progression snapshot — answers 'did ingest propagate downstream?'"""
    run = None
    if pipeline_run_id is not None:
        run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
        if run is None or run.tenant_id != tenant_id:
            run = None
    if run is None:
        run = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    if run is None:
        run = session.scalar(
            select(CortexSubstratePipelineRun)
            .where(CortexSubstratePipelineRun.tenant_id == tenant_id)
            .order_by(CortexSubstratePipelineRun.created_at.desc())
            .limit(1)
        )

    phase_status: dict[str, str] = {}
    continuation_payload: dict[str, Any] | None = None
    if run is not None:
        phase_status = _phase_status_map_v1(session, pipeline_run_id=run.id)
        cont = get_continuation_for_pipeline_v1(session, pipeline_run_id=run.id)
        if cont is not None:
            continuation_payload = {
                "continuation_id": str(cont.id),
                "continuation_status": cont.continuation_status,
                "waiting_on": cont.waiting_on,
                "current_phase": cont.current_phase,
                "async_job_id": str(cont.async_job_id) if cont.async_job_id else None,
                "retry_count": int(cont.retry_count or 0),
                "recovery_required": bool(cont.recovery_required),
                "failure_reason": cont.failure_reason,
                "last_heartbeat_at": (
                    cont.last_heartbeat_at.isoformat() if cont.last_heartbeat_at else None
                ),
            }

    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    synth_scope = count_synthesis_eligible_scopes_v1(session, tenant_id=tenant_id)
    index_count = int(synth_scope.get("index_row_count") or 0)
    eligible = int(synth_scope.get("eligible_scopes") or 0)

    progression_class = TENANT_PROGRESSION_CLASS_IDLE_V1
    stop_reason: str | None = None

    if run is not None and run.status == PIPELINE_STATUS_RUNNING:
        progression_class = TENANT_PROGRESSION_CLASS_PROGRESSING_V1
        if continuation_payload and continuation_payload.get("continuation_status") in (
            CONTINUATION_STATUS_WAITING,
            CONTINUATION_STATUS_STALLED,
        ):
            progression_class = TENANT_PROGRESSION_CLASS_WAITING_UPSTREAM_V1
            stop_reason = str(continuation_payload.get("waiting_on") or "async_wait")
    elif run is not None and run.status == PIPELINE_STATUS_COMPLETED:
        if eligible > 0:
            progression_class = TENANT_PROGRESSION_CLASS_OPERATIONALLY_ALIVE_V1
        elif index_count == 0 and published:
            progression_class = TENANT_PROGRESSION_CLASS_DEGRADED_V1
            stop_reason = "published_epoch_zero_rows"
        else:
            progression_class = TENANT_PROGRESSION_CLASS_IDLE_V1
    elif continuation_payload and continuation_payload.get("recovery_required"):
        progression_class = TENANT_PROGRESSION_CLASS_STALLED_V1
        stop_reason = continuation_payload.get("failure_reason")

    ingest_propagated = bool(
        run is not None
        and phase_status.get(PHASE_07_RETRIEVAL) in (PHASE_STATUS_COMPLETED, PHASE_STATUS_SKIPPED)
    )
    synthesis_propagated = bool(
        run is not None
        and phase_status.get(PHASE_08_SYNTHESIS) in (PHASE_STATUS_COMPLETED, PHASE_STATUS_SKIPPED)
    )

    return {
        "surface_kind": "substrate_operational_progression_status",
        "progression_owner_id": PROGRESSION_OWNER_ID_V1,
        "tenant_id": str(tenant_id),
        "pipeline_run_id": str(run.id) if run is not None else None,
        "pipeline_status": run.status if run is not None else None,
        "trigger_kind": run.trigger_kind if run is not None else None,
        "progression_class": progression_class,
        "stop_reason": stop_reason,
        "active_phase": _first_incomplete_phase_v1(phase_status) if run else None,
        "phase_status": phase_status,
        "continuation": continuation_payload,
        "published_index_epoch": published,
        "retrieval_index_row_count": index_count,
        "synthesis_eligible_scopes": eligible,
        "ingest_propagated_to_retrieval": ingest_propagated,
        "ingest_propagated_to_synthesis": synthesis_propagated,
        "materially_updated_retrieval": index_count > 0,
        "materially_updated_synthesis": eligible > 0,
    }


def list_pipeline_runs_needing_progression_v1(
    session: Session,
    *,
    limit: int = 50,
) -> list[uuid.UUID]:
    """Pipeline runs with active continuations or incomplete downstream phases."""
    lim = max(1, min(int(limit), 200))
    cont_rows = list(
        session.scalars(
            select(CortexPipelineContinuationState.substrate_pipeline_run_id)
            .where(
                CortexPipelineContinuationState.continuation_status.in_(
                    (CONTINUATION_STATUS_WAITING, CONTINUATION_STATUS_STALLED)
                ),
            )
            .distinct()
            .limit(lim)
        ).all()
    )
    run_ids = {uuid.UUID(str(rid)) for rid in cont_rows if rid}
    running = list(
        session.scalars(
            select(CortexSubstratePipelineRun.id)
            .where(CortexSubstratePipelineRun.status == PIPELINE_STATUS_RUNNING)
            .order_by(CortexSubstratePipelineRun.created_at.desc())
            .limit(lim)
        ).all()
    )
    run_ids.update(uuid.UUID(str(rid)) for rid in running if rid)
    return list(run_ids)[:lim]


def _continue_tcre_wait_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    continuation: CortexPipelineContinuationState,
    run: CortexSubstratePipelineRun,
) -> dict[str, Any] | None:
    if continuation.continuation_status in (
        CONTINUATION_STATUS_RESUMED,
        CONTINUATION_STATUS_COMPLETED,
    ):
        return {
            "action": "tcre_continuation_already_advanced",
            "continuation_status": continuation.continuation_status,
        }
    job_id = continuation.async_job_id
    if job_id is None:
        return None
    job = session.get(CortexTcreReconstructionJob, job_id)
    if job is None or job.tenant_id != tenant_id:
        from vector.domains.cortex.substrate_pipeline.stalled_pipeline_recovery import (
            recover_stalled_pipeline_v1,
        )

        return recover_stalled_pipeline_v1(session, pipeline_run_id=pipeline_run_id, action="auto")
    if job.status == "completed":
        out = resume_pipeline_after_tcre_completion_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            tcre_job_id=job_id,
            tcre_job_status="completed",
        )
        _record_progression_receipt_v1(
            session,
            run=run,
            action="resume_after_tcre",
            outcome="resumed" if out.get("resumed") else "skipped",
            detail=out,
        )
        return out
    if job.status == "failed":
        from vector.domains.cortex.substrate_pipeline.stalled_pipeline_recovery import (
            recover_stalled_pipeline_v1,
        )

        return recover_stalled_pipeline_v1(session, pipeline_run_id=pipeline_run_id, action="auto")
    touch_continuation_heartbeat_v1(session, continuation=continuation)
    return {"action": "tcre_still_running", "job_status": job.status}


def _continue_traversal_wait_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    continuation: CortexPipelineContinuationState,
    run: CortexSubstratePipelineRun,
) -> dict[str, Any]:
    """Traversal wait is advisory — close continuation when downstream phase work has started."""
    phase_status = _phase_status_map_v1(session, pipeline_run_id=pipeline_run_id)
    p06 = phase_status.get(PHASE_06_TCRE)
    if p06 in (
        PHASE_STATUS_RUNNING,
        PHASE_STATUS_COMPLETED,
        PHASE_STATUS_QUEUED,
        PHASE_STATUS_SKIPPED,
    ):
        mark_continuation_completed_v1(session, pipeline_run_id=pipeline_run_id)
        _record_progression_receipt_v1(
            session,
            run=run,
            action="close_traversal_wait",
            outcome="completed",
            detail={"phase_06_status": p06},
        )
        return {"action": "traversal_wait_closed", "phase_06_status": p06}

    if phase_status.get(PHASE_05_TRAVERSAL) == PHASE_STATUS_COMPLETED and p06 == PHASE_STATUS_QUEUED:
        from vector.domains.cortex.substrate_pipeline.orchestrator import enqueue_next_pipeline_phase_v1

        chain = enqueue_next_pipeline_phase_v1(
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_06_TCRE,
        )
        _record_progression_receipt_v1(
            session,
            run=run,
            action="enqueue_phase_06_after_traversal",
            outcome="enqueued",
            detail=chain,
        )
        return {"action": "phase_06_enqueued", "next_phase": chain}

    touch_continuation_heartbeat_v1(session, continuation=continuation)
    return {"action": "traversal_wait_heartbeat", "phase_status": phase_status}


def _continue_retrieval_synthesis_closure_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    run: CortexSubstratePipelineRun,
) -> dict[str, Any] | None:
    """Ensure phase 07 → 08 closure and bounded retrieval retries when upstream exists."""
    phase_status = _phase_status_map_v1(session, pipeline_run_id=pipeline_run_id)
    p07 = phase_status.get(PHASE_07_RETRIEVAL)
    p08 = phase_status.get(PHASE_08_SYNTHESIS)

    if p07 == PHASE_STATUS_COMPLETED and p08 not in (
        PHASE_STATUS_COMPLETED,
        PHASE_STATUS_RUNNING,
        PHASE_STATUS_SKIPPED,
    ):
        from vector.domains.cortex.operational_runtime.substrate_synthesis_activation_scheduling import (
            chain_synthesis_activation_after_phase07_v1,
        )

        published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
        out = chain_synthesis_activation_after_phase07_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            published_index_epoch=published,
        )
        _record_progression_receipt_v1(
            session,
            run=run,
            action="chain_synthesis_after_retrieval",
            outcome="chained" if out.get("chained") else "skipped",
            detail=out,
        )
        return out

    if p07 in (PHASE_STATUS_COMPLETED, PHASE_STATUS_FAILED) and p08 in (
        PHASE_STATUS_COMPLETED,
        PHASE_STATUS_SKIPPED,
    ):
        mark_continuation_completed_v1(session, pipeline_run_id=pipeline_run_id)
        from vector.domains.cortex.substrate_pipeline.orchestrator import finalize_pipeline_if_complete_v1

        fin = finalize_pipeline_if_complete_v1(session, pipeline_run_id=pipeline_run_id)
        _record_progression_receipt_v1(
            session,
            run=run,
            action="finalize_pipeline",
            outcome="finalized" if fin.get("finalized") else "waiting",
            detail=fin,
        )
        return fin

    if p07 == PHASE_STATUS_COMPLETED:
        scope = count_synthesis_eligible_scopes_v1(session, tenant_id=tenant_id)
        index_count = int(scope.get("index_row_count") or 0)
        if index_count > 0:
            return None
        retries = _retrieval_retry_count_v1(run)
        if retries >= MAX_RETRIEVAL_MATERIALIZATION_RETRIES_V1:
            _record_progression_receipt_v1(
                session,
                run=run,
                action="retrieval_retry_exhausted",
                outcome="degraded",
                detail={"retries": retries},
            )
            return {
                "action": "retrieval_retry_exhausted",
                "retries": retries,
                "progression_class": TENANT_PROGRESSION_CLASS_DEGRADED_V1,
            }
        tcre_done = int(
            session.scalar(
                select(func.count())
                .select_from(CortexTcreReconstructionJob)
                .where(
                    CortexTcreReconstructionJob.tenant_id == tenant_id,
                    CortexTcreReconstructionJob.status == "completed",
                )
            )
            or 0
        )
        if tcre_done == 0:
            from vector.domains.cortex.substrate_pipeline.orchestrator import enqueue_next_pipeline_phase_v1

            chain = enqueue_next_pipeline_phase_v1(
                tenant_id=tenant_id,
                pipeline_run_id=pipeline_run_id,
                phase_id=PHASE_06_TCRE,
            )
            _record_progression_receipt_v1(
                session,
                run=run,
                action="re_enqueue_phase_06_no_tcre",
                outcome="enqueued",
                detail=chain,
            )
            return chain

        from vector.domains.cortex.substrate_pipeline.orchestrator import enqueue_next_pipeline_phase_v1

        n = _increment_retrieval_retry_v1(session, run=run)
        chain = enqueue_next_pipeline_phase_v1(
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_07_RETRIEVAL,
        )
        _record_progression_receipt_v1(
            session,
            run=run,
            action="retrieval_materialization_retry",
            outcome="enqueued",
            detail={"retry": n, "chain": chain},
        )
        return {"action": "retrieval_retry", "retry": n, "next_phase": chain}

    return None


def _enqueue_stuck_phase_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    run: CortexSubstratePipelineRun,
) -> dict[str, Any] | None:
    phase_status = _phase_status_map_v1(session, pipeline_run_id=pipeline_run_id)
    target = _first_incomplete_phase_v1(phase_status)
    if target is None:
        return None
    st = phase_status.get(target)
    if st not in (PHASE_STATUS_QUEUED, PHASE_STATUS_FAILED):
        return None
    if target == PHASE_06_TCRE:
        from vector.domains.cortex.substrate_pipeline.phase_runners import run_phase_06_tcre_v1

        out = run_phase_06_tcre_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
        )
        _record_progression_receipt_v1(
            session,
            run=run,
            action="inline_phase_06_enqueue",
            outcome="enqueued",
            detail=out,
        )
        return out
    if target in (PHASE_07_RETRIEVAL, PHASE_08_SYNTHESIS):
        from vector.domains.cortex.substrate_pipeline.orchestrator import enqueue_next_pipeline_phase_v1

        chain = enqueue_next_pipeline_phase_v1(
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            phase_id=target,
        )
        _record_progression_receipt_v1(
            session,
            run=run,
            action=f"enqueue_{target}",
            outcome="enqueued",
            detail=chain,
        )
        return chain
    return None


def continue_substrate_operational_progression_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    trigger: str = PROGRESSION_TRIGGER_MANUAL_V1,
    pipeline_run_id: uuid.UUID | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Drive lawful downstream continuation for one tenant (async-safe, idempotent)."""
    run = None
    if pipeline_run_id is not None:
        run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
        if run is None or run.tenant_id != tenant_id:
            run = None
    if run is None:
        run = get_running_pipeline_run_v1(session, tenant_id=tenant_id)

    actions: list[dict[str, Any]] = []

    if run is None:
        status = build_substrate_progression_status_v1(session, tenant_id=tenant_id)
        return {
            "progression_owner_id": PROGRESSION_OWNER_ID_V1,
            "trigger": trigger,
            "continued": False,
            "reason": "no_active_pipeline_run",
            "status": status,
            "actions": actions,
        }

    prid = run.id
    continuation = get_continuation_for_pipeline_v1(session, pipeline_run_id=prid)

    if continuation is not None and continuation.waiting_on == WAITING_ON_TCRE_COMPLETION:
        out = _continue_tcre_wait_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=prid,
            continuation=continuation,
            run=run,
        )
        if out is not None:
            actions.append(out)

    if continuation is not None and continuation.waiting_on == WAITING_ON_TRAVERSAL_COMPLETION:
        out = _continue_traversal_wait_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=prid,
            continuation=continuation,
            run=run,
        )
        actions.append(out)

    if len(actions) < MAX_PROGRESSION_ACTIONS_PER_INVOCATION_V1:
        out = _continue_retrieval_synthesis_closure_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=prid,
            run=run,
        )
        if out is not None:
            actions.append(out)

    if len(actions) < MAX_PROGRESSION_ACTIONS_PER_INVOCATION_V1 and run.status == PIPELINE_STATUS_RUNNING:
        out = _enqueue_stuck_phase_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=prid,
            run=run,
        )
        if out is not None:
            actions.append(out)

    status = build_substrate_progression_status_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=prid,
    )
    return {
        "progression_owner_id": PROGRESSION_OWNER_ID_V1,
        "trigger": trigger,
        "continued": bool(actions),
        "pipeline_run_id": str(prid),
        "actions": actions[:MAX_PROGRESSION_ACTIONS_PER_INVOCATION_V1],
        "status": status,
        "force": force,
    }


def run_substrate_progression_tick_v1(
    session: Session,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    """Periodic sweep — eventual convergence for active pipeline runs."""
    run_ids = list_pipeline_runs_needing_progression_v1(session, limit=limit)
    results: list[dict[str, Any]] = []
    for prid in run_ids:
        run = session.get(CortexSubstratePipelineRun, prid)
        if run is None:
            continue
        try:
            out = continue_substrate_operational_progression_v1(
                session,
                tenant_id=run.tenant_id,
                pipeline_run_id=prid,
                trigger=PROGRESSION_TRIGGER_PROGRESSION_TICK_V1,
            )
            results.append({"pipeline_run_id": str(prid), **out})
        except Exception as exc:  # noqa: BLE001
            _LOGGER.exception(
                "substrate_progression_tick_failed pipeline_run_id=%s", prid, exc_info=exc
            )
            results.append(
                {
                    "pipeline_run_id": str(prid),
                    "error": str(exc)[:500],
                }
            )
    return {
        "tick": PROGRESSION_TRIGGER_PROGRESSION_TICK_V1,
        "pipeline_runs_examined": len(run_ids),
        "results": results,
    }
