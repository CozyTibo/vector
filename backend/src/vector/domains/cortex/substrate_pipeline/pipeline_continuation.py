"""Durable substrate pipeline continuation across async TCRE gaps."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
)
from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1
from vector.infrastructure.db.models.cortex_pipeline_continuation import CortexPipelineContinuationState

_LOGGER = logging.getLogger(__name__)

CONTINUATION_STATUS_WAITING: Final[str] = "WAITING"
CONTINUATION_STATUS_RESUMED: Final[str] = "RESUMED"
CONTINUATION_STATUS_COMPLETED: Final[str] = "COMPLETED"
CONTINUATION_STATUS_FAILED: Final[str] = "FAILED"
CONTINUATION_STATUS_STALLED: Final[str] = "STALLED"
CONTINUATION_STATUS_RECOVERING: Final[str] = "RECOVERING"

WAITING_ON_TCRE_COMPLETION: Final[str] = "TCRE_COMPLETION"
ASYNC_JOB_TYPE_TCRE: Final[str] = "TCRE_RECONSTRUCTION"

DEFAULT_STALL_THRESHOLD_SECONDS: Final[int] = 1800


def compute_continuation_nonce_v1(
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    waiting_on: str,
) -> str:
    return hash_reasoning_canonical_json_sha256_v1(
        {
            "tenant_id": str(tenant_id),
            "pipeline_run_id": str(pipeline_run_id),
            "waiting_on": waiting_on,
            "purpose": "pipeline_continuation_nonce_v1",
        }
    )[:32]


def compute_resume_identity_digest_v1(
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    async_job_id: uuid.UUID,
    waiting_on: str,
) -> str:
    return hash_reasoning_canonical_json_sha256_v1(
        {
            "tenant_id": str(tenant_id),
            "pipeline_run_id": str(pipeline_run_id),
            "async_job_id": str(async_job_id),
            "waiting_on": waiting_on,
            "purpose": "pipeline_resume_identity_v1",
        }
    )


def compute_resume_receipt_hash_v1(
    *,
    resume_identity_digest: str,
    continuation_nonce: str,
    tcre_job_status: str,
) -> str:
    return hash_reasoning_canonical_json_sha256_v1(
        {
            "resume_identity_digest": resume_identity_digest,
            "continuation_nonce": continuation_nonce,
            "tcre_job_status": tcre_job_status,
            "purpose": "pipeline_resume_receipt_v1",
        }
    )


def get_continuation_for_pipeline_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
) -> CortexPipelineContinuationState | None:
    return session.scalar(
        select(CortexPipelineContinuationState).where(
            CortexPipelineContinuationState.substrate_pipeline_run_id == pipeline_run_id,
        )
    )


def mark_pipeline_waiting_on_tcre_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    tcre_job_id: uuid.UUID,
    celery_task_id: str | None = None,
) -> CortexPipelineContinuationState:
    """Persist WAITING continuation after phase 06 enqueues async TCRE."""
    now = datetime.now(UTC)
    waiting_on = WAITING_ON_TCRE_COMPLETION
    nonce = compute_continuation_nonce_v1(
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        waiting_on=waiting_on,
    )
    existing = get_continuation_for_pipeline_v1(session, pipeline_run_id=pipeline_run_id)
    if existing is not None:
        existing.waiting_on = waiting_on
        existing.async_job_id = tcre_job_id
        existing.async_job_type = ASYNC_JOB_TYPE_TCRE
        existing.continuation_status = CONTINUATION_STATUS_WAITING
        existing.current_phase = PHASE_06_TCRE
        existing.last_heartbeat_at = now
        existing.recovery_required = False
        existing.failure_reason = None
        detail = dict(existing.detail_json or {})
        if celery_task_id:
            detail["celery_task_id"] = celery_task_id
        existing.detail_json = detail
        session.flush()
        return existing

    row = CortexPipelineContinuationState(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        substrate_pipeline_run_id=pipeline_run_id,
        current_phase=PHASE_06_TCRE,
        waiting_on=waiting_on,
        async_job_id=tcre_job_id,
        async_job_type=ASYNC_JOB_TYPE_TCRE,
        continuation_status=CONTINUATION_STATUS_WAITING,
        continuation_nonce=nonce,
        last_heartbeat_at=now,
        retry_count=0,
        recovery_required=False,
        detail_json={"celery_task_id": celery_task_id} if celery_task_id else {},
    )
    session.add(row)
    session.flush()
    return row


def touch_continuation_heartbeat_v1(
    session: Session,
    *,
    continuation: CortexPipelineContinuationState,
) -> None:
    continuation.last_heartbeat_at = datetime.now(UTC)
    session.flush()


def resume_pipeline_after_tcre_completion_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    tcre_job_id: uuid.UUID,
    tcre_job_status: str,
) -> dict[str, Any]:
    """Idempotent resume: enqueue phase 07 once per TCRE completion receipt."""
    from vector.domains.cortex.substrate_pipeline.orchestrator import enqueue_next_pipeline_phase_v1

    continuation = get_continuation_for_pipeline_v1(session, pipeline_run_id=pipeline_run_id)
    if continuation is None:
        _LOGGER.critical(
            "pipeline_continuation_missing tenant_id=%s pipeline_run_id=%s tcre_job_id=%s",
            tenant_id,
            pipeline_run_id,
            tcre_job_id,
        )
        continuation = mark_pipeline_waiting_on_tcre_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            tcre_job_id=tcre_job_id,
        )
        continuation.recovery_required = True
        continuation.failure_reason = "continuation_state_missing_on_tcre_complete"
        detail = dict(continuation.detail_json or {})
        detail["recovered_from_missing_continuation"] = True
        continuation.detail_json = detail

    resume_digest = compute_resume_identity_digest_v1(
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        async_job_id=tcre_job_id,
        waiting_on=WAITING_ON_TCRE_COMPLETION,
    )
    receipt_hash = compute_resume_receipt_hash_v1(
        resume_identity_digest=resume_digest,
        continuation_nonce=continuation.continuation_nonce,
        tcre_job_status=tcre_job_status,
    )

    phase07 = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_07_RETRIEVAL)
    if phase07 is not None and phase07.status == "completed":
        continuation.continuation_status = CONTINUATION_STATUS_COMPLETED
        continuation.completed_at = datetime.now(UTC)
        continuation.resume_identity_digest = resume_digest
        continuation.resume_receipt_hash = receipt_hash
        session.flush()
        return {
            "resumed": False,
            "reason": "phase_07_already_completed",
            "resume_receipt_hash": receipt_hash,
        }

    if (
        continuation.resume_receipt_hash == receipt_hash
        and continuation.continuation_status in (CONTINUATION_STATUS_RESUMED, CONTINUATION_STATUS_COMPLETED)
    ):
        touch_continuation_heartbeat_v1(session, continuation=continuation)
        return {
            "resumed": False,
            "reason": "duplicate_resume_receipt",
            "resume_receipt_hash": receipt_hash,
        }

    now = datetime.now(UTC)
    continuation.resume_identity_digest = resume_digest
    continuation.resume_receipt_hash = receipt_hash
    continuation.continuation_status = CONTINUATION_STATUS_RESUMED
    continuation.resumed_at = now
    continuation.current_phase = PHASE_07_RETRIEVAL
    continuation.last_heartbeat_at = now
    touch_continuation_heartbeat_v1(session, continuation=continuation)

    chain = enqueue_next_pipeline_phase_v1(
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        phase_id=PHASE_07_RETRIEVAL,
    )
    return {
        "resumed": True,
        "resume_receipt_hash": receipt_hash,
        "resume_identity_digest": resume_digest,
        "continuation_nonce": continuation.continuation_nonce,
        "next_phase": chain,
    }


def mark_continuation_completed_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
) -> None:
    continuation = get_continuation_for_pipeline_v1(session, pipeline_run_id=pipeline_run_id)
    if continuation is None:
        return
    continuation.continuation_status = CONTINUATION_STATUS_COMPLETED
    continuation.completed_at = datetime.now(UTC)
    continuation.waiting_on = None
    session.flush()


def list_stale_waiting_continuations_v1(
    session: Session,
    *,
    stall_threshold_seconds: int = DEFAULT_STALL_THRESHOLD_SECONDS,
    limit: int = 100,
    tenant_id: uuid.UUID | None = None,
) -> list[CortexPipelineContinuationState]:
    """Read-only: continuations past heartbeat threshold (does not mutate status)."""
    cutoff = datetime.now(UTC) - timedelta(seconds=max(60, int(stall_threshold_seconds)))
    stmt = select(CortexPipelineContinuationState).where(
        CortexPipelineContinuationState.continuation_status.in_(
            (CONTINUATION_STATUS_WAITING, CONTINUATION_STATUS_STALLED)
        ),
        CortexPipelineContinuationState.waiting_on == WAITING_ON_TCRE_COMPLETION,
        CortexPipelineContinuationState.last_heartbeat_at < cutoff,
    )
    if tenant_id is not None:
        stmt = stmt.where(CortexPipelineContinuationState.tenant_id == tenant_id)
    return list(
        session.scalars(
            stmt.order_by(CortexPipelineContinuationState.last_heartbeat_at.asc()).limit(
                max(1, min(limit, 500))
            )
        ).all()
    )


def list_stalled_continuations_v1(
    session: Session,
    *,
    stall_threshold_seconds: int = DEFAULT_STALL_THRESHOLD_SECONDS,
    limit: int = 100,
) -> list[CortexPipelineContinuationState]:
    return list_stale_waiting_continuations_v1(
        session,
        stall_threshold_seconds=stall_threshold_seconds,
        limit=limit,
    )
