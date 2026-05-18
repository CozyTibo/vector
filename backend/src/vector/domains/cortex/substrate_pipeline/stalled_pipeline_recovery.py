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
)
from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePipelineRun
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob

_LOGGER = logging.getLogger(__name__)


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
        row.continuation_status = CONTINUATION_STATUS_STALLED
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

    continuation.continuation_status = CONTINUATION_STATUS_RECOVERING
    continuation.retry_count = int(continuation.retry_count or 0) + 1
    touch_continuation_heartbeat_v1(session, continuation=continuation)

    phase07 = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_07_RETRIEVAL)
    if phase07 is not None and phase07.status == "completed":
        from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
            mark_continuation_completed_v1,
        )

        mark_continuation_completed_v1(session, pipeline_run_id=pipeline_run_id)
        return {"recovered": True, "reason": "phase_07_already_complete"}

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
        return {"recovered": False, "reason": "no_tcre_job_to_rebind"}

    job = session.get(CortexTcreReconstructionJob, job_id)
    if job is None:
        return {"recovered": False, "reason": "tcre_job_not_found"}

    if job.status != "completed" and action not in ("replay_callback",):
        return {"recovered": False, "reason": f"tcre_status_{job.status}"}

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
        return {"recovered": bool(out.get("resumed")), **out}

    from vector.domains.cortex.substrate_pipeline.orchestrator import enqueue_next_pipeline_phase_v1

    if action in ("replay_phase_06", "auto") and continuation.waiting_on == WAITING_ON_TCRE_COMPLETION:
        from vector.domains.cortex.substrate_pipeline.phase_runners import run_phase_06_tcre_v1

        run_phase_06_tcre_v1(
            session,
            tenant_id=continuation.tenant_id,
            pipeline_run_id=pipeline_run_id,
        )
        return {"recovered": True, "reason": "phase_06_re_enqueued"}

    chain = enqueue_next_pipeline_phase_v1(
        tenant_id=continuation.tenant_id,
        pipeline_run_id=pipeline_run_id,
        phase_id=PHASE_07_RETRIEVAL,
    )
    return {"recovered": True, "reason": "phase_07_force_enqueued", "next_phase": chain}


def run_stalled_pipeline_watchdog_v1(
    session: Session,
    *,
    stall_threshold_seconds: int = 1800,
    auto_recover: bool = True,
    limit: int = 50,
) -> dict[str, Any]:
    """Periodic watchdog: detect stalls and optionally auto-recover."""
    stalled = detect_stalled_substrate_pipelines_v1(
        session,
        stall_threshold_seconds=stall_threshold_seconds,
        limit=limit,
    )
    recovered: list[dict[str, Any]] = []
    if auto_recover:
        for item in stalled:
            prid = uuid.UUID(str(item["pipeline_run_id"]))
            try:
                rec = recover_stalled_pipeline_v1(session, pipeline_run_id=prid, action="auto")
                recovered.append({"pipeline_run_id": str(prid), **rec})
            except Exception as exc:  # noqa: BLE001
                _LOGGER.exception("stalled_recovery_failed pipeline_run_id=%s", prid)
                recovered.append(
                    {"pipeline_run_id": str(prid), "recovered": False, "error": str(exc)[:300]}
                )
    session.commit()
    return {
        "stalled_count": len(stalled),
        "stalled": stalled,
        "recovered": recovered,
    }
