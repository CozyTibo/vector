"""Stalled substrate pipeline detection and replay-safe recovery."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.constants import PHASE_06_TCRE, PHASE_07_RETRIEVAL
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_RECOVERING,
    CONTINUATION_STATUS_STALLED,
    CONTINUATION_STATUS_WAITING,
    WAITING_ON_TCRE_COMPLETION,
    get_continuation_for_pipeline_v1,
    list_stalled_continuations_v1,
    resume_pipeline_after_tcre_completion_v1,
    touch_continuation_heartbeat_v1,
    transition_continuation_status_v1,
)
from vector.domains.cortex.operational_runtime.recovery_continuity import (
    increment_dlq_metric_v1,
)
from vector.domains.cortex.operational_runtime.substrate_continuity import (
    increment_continuation_metric_v1,
)
from vector.domains.cortex.substrate_pipeline.pipeline_dead_letter import (
    FAILURE_CLASS_CELERY_LOST,
    FAILURE_CLASS_PHASE_ENQUEUE_FAILED,
    FAILURE_CLASS_TCRE_FAILED,
    PipelineDeadLetterError,
    assert_dlq_auto_retry_budget_v1,
    record_pipeline_dead_letter_v1,
    resolve_open_dlq_for_pipeline_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePipelineRun
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob

_LOGGER = logging.getLogger(__name__)


def _finish_stalled_recovery_v1(
    session: Session,
    *,
    continuation: Any,
    operator_action: str,
    result: dict[str, Any],
    recommendation: str | None = None,
) -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.recovery_receipts import (
        persist_stalled_recovery_receipt_v1,
    )

    receipt = persist_stalled_recovery_receipt_v1(
        session,
        continuation=continuation,
        operator_action=operator_action,
        result=result,
        recommendation=recommendation,
    )
    return {**result, "recovery_receipt": receipt}


def detect_stalled_substrate_pipelines_v1(
    session: Session,
    *,
    stall_threshold_seconds: int = 1800,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Find continuations waiting on TCRE with stale heartbeats."""
    stalled_rows = list_stalled_continuations_v1(
        session,
        stall_threshold_seconds=stall_threshold_seconds,
        limit=limit,
    )
    out: list[dict[str, Any]] = []
    now = datetime.now(UTC)
    for row in stalled_rows:
        touch_continuation_heartbeat_v1(session, continuation=row)
        if row.continuation_status != CONTINUATION_STATUS_STALLED:
            transition_continuation_status_v1(
                session,
                continuation=row,
                to_status=CONTINUATION_STATUS_STALLED,
            )
            increment_continuation_metric_v1("substrate_continuation_stall_total")
        row.recovery_required = True
        if not row.failure_reason:
            row.failure_reason = "stalled_waiting_on_tcre"
        session.flush()
        hb = row.last_heartbeat_at
        stalled_seconds = int((now - hb).total_seconds()) if hb else None
        run = session.get(CortexSubstratePipelineRun, row.substrate_pipeline_run_id)
        out.append(
            {
                "tenant_id": str(row.tenant_id),
                "pipeline_run_id": str(row.substrate_pipeline_run_id),
                "current_phase": row.current_phase,
                "waiting_on": row.waiting_on,
                "continuation_status": row.continuation_status,
                "async_job_id": str(row.async_job_id) if row.async_job_id else None,
                "stalled_seconds": stalled_seconds,
                "retry_count": row.retry_count,
                "pipeline_run_status": run.status if run else None,
                "recovery_recommendation": _recovery_recommendation_v1(session, row=row),
            }
        )
    return out


def _recovery_recommendation_v1(
    session: Session,
    *,
    row: Any,
) -> str:
    if row.async_job_id is None:
        return "rebind_tcre_job"
    job = session.get(CortexTcreReconstructionJob, row.async_job_id)
    if job is None:
        return "rebind_tcre_job"
    if job.status == "completed":
        return "resume_phase_07"
    if job.status == "failed":
        return "replay_phase_06_or_mark_unrecoverable"
    return "retry_tcre_callback"


def _record_recovery_dlq_v1(
    session: Session,
    *,
    continuation: Any,
    pipeline_run_id: uuid.UUID,
    failure_class: str,
    failure_detail: str,
    auto_retry_increment: int = 0,
) -> None:
    record_pipeline_dead_letter_v1(
        session,
        tenant_id=continuation.tenant_id,
        pipeline_run_id=pipeline_run_id,
        phase_id=str(continuation.current_phase or PHASE_06_TCRE),
        failure_class=failure_class,
        async_job_id=continuation.async_job_id,
        resume_receipt_hash=continuation.resume_receipt_hash,
        failure_detail=failure_detail,
        auto_retry_increment=auto_retry_increment,
    )


def recover_stalled_pipeline_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    action: str = "auto",
) -> dict[str, Any]:
    """Replay-safe recovery for one stalled pipeline."""
    continuation = get_continuation_for_pipeline_v1(session, pipeline_run_id=pipeline_run_id)
    if continuation is None:
        return {"recovered": False, "reason": "continuation_not_found"}

    if action == "auto" and continuation.resume_receipt_hash:
        try:
            assert_dlq_auto_retry_budget_v1(
                session,
                resume_receipt_hash=continuation.resume_receipt_hash,
            )
        except PipelineDeadLetterError as exc:
            increment_dlq_metric_v1("substrate_dlq_auto_retry_blocked_total")
            _record_recovery_dlq_v1(
                session,
                continuation=continuation,
                pipeline_run_id=pipeline_run_id,
                failure_class=FAILURE_CLASS_PHASE_ENQUEUE_FAILED,
                failure_detail=str(exc.code),
            )
            result = {
                "recovered": False,
                "reason": exc.code,
                "detail": exc.detail,
                "dlq_recorded": True,
            }
            return _finish_stalled_recovery_v1(
                session,
                continuation=continuation,
                operator_action=action,
                result=result,
            )

    if continuation.continuation_status == CONTINUATION_STATUS_WAITING:
        transition_continuation_status_v1(
            session,
            continuation=continuation,
            to_status=CONTINUATION_STATUS_STALLED,
        )
    transition_continuation_status_v1(
        session,
        continuation=continuation,
        to_status=CONTINUATION_STATUS_RECOVERING,
    )
    continuation.retry_count = int(continuation.retry_count or 0) + 1
    touch_continuation_heartbeat_v1(session, continuation=continuation)

    phase07 = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_07_RETRIEVAL)
    if phase07 is not None and phase07.status == "completed":
        from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
            mark_continuation_completed_v1,
        )

        mark_continuation_completed_v1(session, pipeline_run_id=pipeline_run_id)
        return _finish_stalled_recovery_v1(
            session,
            continuation=continuation,
            operator_action=action,
            result={"recovered": True, "reason": "phase_07_already_complete"},
        )

    job_id = continuation.async_job_id
    if job_id is None and action in ("auto", "rebind_tcre"):
        job = session.scalar(
            select(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == continuation.tenant_id,
                CortexTcreReconstructionJob.status == "completed",
                CortexTcreReconstructionJob.job_kind == "reconstruct",
            )
            .order_by(CortexTcreReconstructionJob.completed_at.desc())
            .limit(1)
        )
        if job is not None:
            job_id = job.id
            continuation.async_job_id = job_id

    if job_id is None:
        continuation.failure_reason = "recovery_no_tcre_job"
        continuation.recovery_required = True
        session.flush()
        _record_recovery_dlq_v1(
            session,
            continuation=continuation,
            pipeline_run_id=pipeline_run_id,
            failure_class=FAILURE_CLASS_CELERY_LOST,
            failure_detail="recovery_no_tcre_job",
            auto_retry_increment=1 if action == "auto" else 0,
        )
        return _finish_stalled_recovery_v1(
            session,
            continuation=continuation,
            operator_action=action,
            result={"recovered": False, "reason": "no_tcre_job_to_rebind", "dlq_recorded": True},
            recommendation="rebind_tcre_job",
        )

    job = session.get(CortexTcreReconstructionJob, job_id)
    if job is None:
        _record_recovery_dlq_v1(
            session,
            continuation=continuation,
            pipeline_run_id=pipeline_run_id,
            failure_class=FAILURE_CLASS_CELERY_LOST,
            failure_detail="tcre_job_not_found",
            auto_retry_increment=1 if action == "auto" else 0,
        )
        return _finish_stalled_recovery_v1(
            session,
            continuation=continuation,
            operator_action=action,
            result={"recovered": False, "reason": "tcre_job_not_found", "dlq_recorded": True},
            recommendation="rebind_tcre_job",
        )

    if job.status != "completed" and action not in ("replay_callback",):
        _record_recovery_dlq_v1(
            session,
            continuation=continuation,
            pipeline_run_id=pipeline_run_id,
            failure_class=FAILURE_CLASS_TCRE_FAILED,
            failure_detail=f"tcre_status_{job.status}",
            auto_retry_increment=1 if action == "auto" else 0,
        )
        return _finish_stalled_recovery_v1(
            session,
            continuation=continuation,
            operator_action=action,
            result={
                "recovered": False,
                "reason": f"tcre_status_{job.status}",
                "dlq_recorded": True,
            },
            recommendation="replay_phase_06_or_mark_unrecoverable",
        )

    if job.status == "completed":
        out = resume_pipeline_after_tcre_completion_v1(
            session,
            tenant_id=continuation.tenant_id,
            pipeline_run_id=pipeline_run_id,
            tcre_job_id=job_id,
            tcre_job_status=str(job.status),
        )
        continuation.recovery_required = False
        session.flush()
        recovered = bool(out.get("resumed"))
        if recovered:
            resolve_open_dlq_for_pipeline_v1(
                session,
                pipeline_run_id=pipeline_run_id,
                detail={"recovery_action": action},
            )
        elif action == "auto":
            _record_recovery_dlq_v1(
                session,
                continuation=continuation,
                pipeline_run_id=pipeline_run_id,
                failure_class=FAILURE_CLASS_PHASE_ENQUEUE_FAILED,
                failure_detail=str(out.get("reason") or "resume_not_applied"),
                auto_retry_increment=1,
            )
        return _finish_stalled_recovery_v1(
            session,
            continuation=continuation,
            operator_action=action,
            result={"recovered": recovered, **out},
            recommendation="resume_phase_07",
        )

    from vector.domains.cortex.substrate_pipeline.orchestrator import enqueue_next_pipeline_phase_v1

    if action in ("replay_phase_06", "auto") and continuation.waiting_on == WAITING_ON_TCRE_COMPLETION:
        from vector.domains.cortex.substrate_pipeline.phase_runners import run_phase_06_tcre_v1

        run_phase_06_tcre_v1(
            session,
            tenant_id=continuation.tenant_id,
            pipeline_run_id=pipeline_run_id,
        )
        return _finish_stalled_recovery_v1(
            session,
            continuation=continuation,
            operator_action=action,
            result={"recovered": True, "reason": "phase_06_re_enqueued"},
        )

    chain = enqueue_next_pipeline_phase_v1(
        tenant_id=continuation.tenant_id,
        pipeline_run_id=pipeline_run_id,
        phase_id=PHASE_07_RETRIEVAL,
    )
    return _finish_stalled_recovery_v1(
        session,
        continuation=continuation,
        operator_action=action,
        result={"recovered": True, "reason": "phase_07_force_enqueued", "next_phase": chain},
    )


def run_stalled_pipeline_watchdog_v1(
    session: Session,
    *,
    stall_threshold_seconds: int = 1800,
    auto_recover: bool = True,
    limit: int = 50,
    watchdog_run_id: str | None = None,
) -> dict[str, Any]:
    """Periodic watchdog: detect stalls and optionally auto-recover (**G-P085-WATCH-01**)."""
    from vector.domains.cortex.operational_runtime.substrate_continuity_watchdog import (
        build_watchdog_audit_record_v1,
        increment_watchdog_metric_v1,
    )

    run_id = watchdog_run_id or str(uuid.uuid4())
    started_at = datetime.now(UTC).isoformat()
    increment_watchdog_metric_v1("substrate_watchdog_tick_total")

    stalled = detect_stalled_substrate_pipelines_v1(
        session,
        stall_threshold_seconds=stall_threshold_seconds,
        limit=limit,
    )
    if stalled:
        increment_watchdog_metric_v1(
            "substrate_watchdog_stalls_detected_total",
            delta=len(stalled),
        )

    recovered: list[dict[str, Any]] = []
    if auto_recover:
        for item in stalled:
            prid = uuid.UUID(str(item["pipeline_run_id"]))
            increment_watchdog_metric_v1("substrate_watchdog_recoveries_attempted_total")
            try:
                rec = recover_stalled_pipeline_v1(session, pipeline_run_id=prid, action="auto")
                recovered.append({"pipeline_run_id": str(prid), **rec})
                if rec.get("recovered"):
                    increment_watchdog_metric_v1("substrate_watchdog_recoveries_succeeded_total")
                    from vector.domains.cortex.operational_runtime.substrate_operational_progression import (
                        PROGRESSION_TRIGGER_WATCHDOG_V1,
                        continue_substrate_operational_progression_v1,
                    )

                    run_row = session.get(CortexSubstratePipelineRun, prid)
                    if run_row is not None:
                        prog = continue_substrate_operational_progression_v1(
                            session,
                            tenant_id=run_row.tenant_id,
                            pipeline_run_id=prid,
                            trigger=PROGRESSION_TRIGGER_WATCHDOG_V1,
                        )
                        rec["progression"] = prog
                else:
                    increment_watchdog_metric_v1("substrate_watchdog_recoveries_failed_total")
            except Exception as exc:  # noqa: BLE001
                _LOGGER.exception("stalled_recovery_failed pipeline_run_id=%s", prid)
                increment_watchdog_metric_v1("substrate_watchdog_recoveries_failed_total")
                cont = get_continuation_for_pipeline_v1(session, pipeline_run_id=prid)
                if cont is not None:
                    _record_recovery_dlq_v1(
                        session,
                        continuation=cont,
                        pipeline_run_id=prid,
                        failure_class=FAILURE_CLASS_PHASE_ENQUEUE_FAILED,
                        failure_detail=str(exc)[:500],
                        auto_retry_increment=1,
                    )
                recovered.append(
                    {
                        "pipeline_run_id": str(prid),
                        "recovered": False,
                        "error": str(exc)[:300],
                        "dlq_recorded": cont is not None,
                    }
                )

    from vector.domains.cortex.operational_runtime.substrate_tcre_saturation_scheduling import (
        run_tcre_saturation_watchdog_hook_v1,
    )

    tcre_saturation_outcomes = run_tcre_saturation_watchdog_hook_v1(
        session,
        stalled_pipelines=stalled,
        limit=limit,
    )

    audit = build_watchdog_audit_record_v1(
        watchdog_run_id=run_id,
        stall_threshold_seconds=stall_threshold_seconds,
        auto_recover=auto_recover,
        stalled=stalled,
        recovered=recovered,
        started_at=started_at,
        completed_at=datetime.now(UTC).isoformat(),
    )
    _LOGGER.info(
        "substrate_continuity_watchdog_audit watchdog_run_id=%s stalled=%s succeeded=%s failed=%s digest=%s",
        run_id,
        audit["stalled_count"],
        audit["recoveries_succeeded"],
        audit["recoveries_failed"],
        audit["watchdog_run_digest"],
    )
    session.commit()
    return {
        "watchdog_run_id": run_id,
        "stalled_count": len(stalled),
        "stalled": stalled,
        "recovered": recovered,
        "tcre_saturation_outcomes": tcre_saturation_outcomes,
        "audit": audit,
    }
