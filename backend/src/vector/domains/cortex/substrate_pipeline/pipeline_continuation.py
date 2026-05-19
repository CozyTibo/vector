"""Durable substrate pipeline continuation across async TCRE gaps."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from collections.abc import Mapping
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_05_TRAVERSAL,
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
WAITING_ON_TRAVERSAL_COMPLETION: Final[str] = "TRAVERSAL_COMPLETION"
ASYNC_JOB_TYPE_TCRE: Final[str] = "TCRE_RECONSTRUCTION"
ASYNC_JOB_TYPE_TRAVERSAL_WALK_BATCH: Final[str] = "TRAVERSAL_WALK_BATCH"

DEFAULT_STALL_THRESHOLD_SECONDS: Final[int] = 1800


def transition_continuation_status_v1(
    session: Session,
    *,
    continuation: CortexPipelineContinuationState,
    to_status: str,
) -> None:
    """Apply **G-P085-CONT-01** state transition with validation."""
    from vector.domains.cortex.operational_runtime.substrate_continuity import (
        validate_continuation_status_transition_v1,
    )

    if continuation.continuation_status == to_status:
        return
    validate_continuation_status_transition_v1(
        from_status=continuation.continuation_status,
        to_status=to_status,
    )
    continuation.continuation_status = to_status
    session.flush()


def mark_continuation_failed_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    failure_reason: str,
) -> CortexPipelineContinuationState | None:
    continuation = get_continuation_for_pipeline_v1(session, pipeline_run_id=pipeline_run_id)
    if continuation is None:
        return None
    transition_continuation_status_v1(
        session,
        continuation=continuation,
        to_status=CONTINUATION_STATUS_FAILED,
    )
    continuation.failure_reason = failure_reason[:2000]
    continuation.recovery_required = True
    session.flush()
    return continuation


def append_recovery_receipt_v1(
    continuation: CortexPipelineContinuationState,
    *,
    receipt: Mapping[str, Any],
) -> None:
    detail = dict(continuation.detail_json or {})
    receipts = list(detail.get("recovery_receipts") or [])
    receipts.append(dict(receipt))
    from vector.domains.cortex.operational_runtime.recovery_receipts import (
        MAX_RECOVERY_RECEIPTS_PER_CONTINUATION_V1,
    )

    detail["recovery_receipts"] = receipts[-MAX_RECOVERY_RECEIPTS_PER_CONTINUATION_V1:]
    continuation.detail_json = detail


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
        transition_continuation_status_v1(
            session,
            continuation=existing,
            to_status=CONTINUATION_STATUS_WAITING,
        )
        existing.waiting_on = waiting_on
        existing.async_job_id = tcre_job_id
        existing.async_job_type = ASYNC_JOB_TYPE_TCRE
        existing.current_phase = PHASE_06_TCRE
        existing.last_heartbeat_at = now
        existing.recovery_required = False
        existing.failure_reason = None
        detail = dict(existing.detail_json or {})
        if celery_task_id:
            detail["celery_task_id"] = celery_task_id
        existing.detail_json = detail
        session.flush()
        from vector.domains.cortex.operational_runtime.substrate_continuity import (
            increment_continuation_metric_v1,
        )

        increment_continuation_metric_v1("substrate_continuation_waiting_gauge")
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
    from vector.domains.cortex.operational_runtime.substrate_continuity import (
        increment_continuation_metric_v1,
    )

    increment_continuation_metric_v1("substrate_continuation_waiting_gauge")
    return row


def mark_pipeline_waiting_on_traversal_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    walk_batch_id: uuid.UUID,
    scheduled_start_count: int = 0,
    celery_task_id: str | None = None,
) -> CortexPipelineContinuationState:
    """Persist WAITING continuation after traversal walk batch is scheduled (**G-P085-WALK-01**)."""
    now = datetime.now(UTC)
    waiting_on = WAITING_ON_TRAVERSAL_COMPLETION
    nonce = compute_continuation_nonce_v1(
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        waiting_on=waiting_on,
    )
    existing = get_continuation_for_pipeline_v1(session, pipeline_run_id=pipeline_run_id)
    detail_base = {
        "scheduled_start_count": int(scheduled_start_count),
        "walk_batch_id": str(walk_batch_id),
    }
    if celery_task_id:
        detail_base["celery_task_id"] = celery_task_id

    if existing is not None:
        transition_continuation_status_v1(
            session,
            continuation=existing,
            to_status=CONTINUATION_STATUS_WAITING,
        )
        existing.waiting_on = waiting_on
        existing.async_job_id = walk_batch_id
        existing.async_job_type = ASYNC_JOB_TYPE_TRAVERSAL_WALK_BATCH
        existing.current_phase = PHASE_05_TRAVERSAL
        existing.last_heartbeat_at = now
        existing.recovery_required = False
        existing.failure_reason = None
        detail = dict(existing.detail_json or {})
        detail.update(detail_base)
        existing.detail_json = detail
        session.flush()
        from vector.domains.cortex.operational_runtime.substrate_continuity import (
            increment_continuation_metric_v1,
        )

        increment_continuation_metric_v1("substrate_continuation_waiting_gauge")
        return existing

    row = CortexPipelineContinuationState(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        substrate_pipeline_run_id=pipeline_run_id,
        current_phase=PHASE_05_TRAVERSAL,
        waiting_on=waiting_on,
        async_job_id=walk_batch_id,
        async_job_type=ASYNC_JOB_TYPE_TRAVERSAL_WALK_BATCH,
        continuation_status=CONTINUATION_STATUS_WAITING,
        continuation_nonce=nonce,
        last_heartbeat_at=now,
        retry_count=0,
        recovery_required=False,
        detail_json=detail_base,
    )
    session.add(row)
    session.flush()
    from vector.domains.cortex.operational_runtime.substrate_continuity import (
        increment_continuation_metric_v1,
    )

    increment_continuation_metric_v1("substrate_continuation_waiting_gauge")
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
    enqueue_phase: bool = True,
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
        from vector.domains.cortex.substrate_pipeline.pipeline_dead_letter import (
            FAILURE_CLASS_CONTINUATION_MISSING,
            record_pipeline_dead_letter_v1,
        )

        record_pipeline_dead_letter_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_06_TCRE,
            failure_class=FAILURE_CLASS_CONTINUATION_MISSING,
            async_job_id=tcre_job_id,
            failure_detail="continuation_state_missing_on_tcre_complete",
            detail={"recovered_inline": True},
        )

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
        transition_continuation_status_v1(
            session,
            continuation=continuation,
            to_status=CONTINUATION_STATUS_COMPLETED,
        )
        continuation.completed_at = datetime.now(UTC)
        continuation.resume_identity_digest = resume_digest
        continuation.resume_receipt_hash = receipt_hash
        session.flush()
        from vector.domains.cortex.operational_runtime.recovery_receipts import (
            RECOVERY_RECEIPT_ACTION_RESUME_PHASE_07,
            RECOVERY_RECEIPT_OUTCOME_SKIPPED,
            persist_recovery_receipt_v1,
        )

        recovery_receipt = persist_recovery_receipt_v1(
            session,
            continuation=continuation,
            action=RECOVERY_RECEIPT_ACTION_RESUME_PHASE_07,
            outcome=RECOVERY_RECEIPT_OUTCOME_SKIPPED,
            prior_resume_receipt_hash=receipt_hash,
            extra={"reason": "phase_07_already_completed"},
        )
        return {
            "resumed": False,
            "reason": "phase_07_already_completed",
            "resume_receipt_hash": receipt_hash,
            "recovery_receipt": recovery_receipt,
        }

    if (
        continuation.resume_receipt_hash == receipt_hash
        and continuation.continuation_status in (CONTINUATION_STATUS_RESUMED, CONTINUATION_STATUS_COMPLETED)
    ):
        touch_continuation_heartbeat_v1(session, continuation=continuation)
        from vector.domains.cortex.operational_runtime.recovery_receipts import (
            RECOVERY_RECEIPT_ACTION_REPLAY_CALLBACK,
            RECOVERY_RECEIPT_OUTCOME_SKIPPED,
            persist_recovery_receipt_v1,
        )
        from vector.domains.cortex.operational_runtime.substrate_continuity import (
            increment_continuation_metric_v1,
        )

        increment_continuation_metric_v1("substrate_resume_duplicate_total")
        recovery_receipt = persist_recovery_receipt_v1(
            session,
            continuation=continuation,
            action=RECOVERY_RECEIPT_ACTION_REPLAY_CALLBACK,
            outcome=RECOVERY_RECEIPT_OUTCOME_SKIPPED,
            prior_resume_receipt_hash=receipt_hash,
            extra={"reason": "duplicate_resume_receipt"},
        )
        return {
            "resumed": False,
            "reason": "duplicate_resume_receipt",
            "resume_receipt_hash": receipt_hash,
            "recovery_receipt": recovery_receipt,
        }

    now = datetime.now(UTC)
    continuation.resume_identity_digest = resume_digest
    continuation.resume_receipt_hash = receipt_hash
    transition_continuation_status_v1(
        session,
        continuation=continuation,
        to_status=CONTINUATION_STATUS_RESUMED,
    )
    continuation.resumed_at = now
    continuation.current_phase = PHASE_07_RETRIEVAL
    continuation.last_heartbeat_at = now
    touch_continuation_heartbeat_v1(session, continuation=continuation)

    chain: dict[str, Any] | None = None
    if enqueue_phase:
        chain = enqueue_next_pipeline_phase_v1(
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            phase_id=PHASE_07_RETRIEVAL,
        )
        from vector.domains.cortex.operational_runtime.substrate_continuity import (
            increment_continuation_metric_v1,
        )

        increment_continuation_metric_v1("substrate_phase_07_enqueue_total")
    from vector.domains.cortex.operational_runtime.recovery_receipts import (
        RECOVERY_RECEIPT_ACTION_REPLAY_CALLBACK,
        RECOVERY_RECEIPT_OUTCOME_RECOVERED,
        persist_recovery_receipt_v1,
    )

    recovery_receipt = persist_recovery_receipt_v1(
        session,
        continuation=continuation,
        action=RECOVERY_RECEIPT_ACTION_REPLAY_CALLBACK,
        outcome=RECOVERY_RECEIPT_OUTCOME_RECOVERED,
        prior_resume_receipt_hash=receipt_hash,
        extra={"reason": "tcre_completion_resume"},
    )
    return {
        "resumed": True,
        "resume_receipt_hash": receipt_hash,
        "resume_identity_digest": resume_digest,
        "continuation_nonce": continuation.continuation_nonce,
        "next_phase": chain,
        "recovery_receipt": recovery_receipt,
    }


def mark_continuation_completed_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
) -> None:
    continuation = get_continuation_for_pipeline_v1(session, pipeline_run_id=pipeline_run_id)
    if continuation is None:
        return
    transition_continuation_status_v1(
        session,
        continuation=continuation,
        to_status=CONTINUATION_STATUS_COMPLETED,
    )
    continuation.completed_at = datetime.now(UTC)
    continuation.waiting_on = None
    session.flush()


def list_stale_waiting_continuations_v1(
    session: Session,
    *,
    stall_threshold_seconds: int | None = None,
    limit: int = 100,
    tenant_id: uuid.UUID | None = None,
) -> list[CortexPipelineContinuationState]:
    """Read-only: continuations past heartbeat threshold (does not mutate status)."""
    if stall_threshold_seconds is None:
        from vector.domains.cortex.operational_runtime.substrate_continuity import (
            get_continuation_stall_threshold_seconds_v1,
        )

        stall_threshold_seconds = get_continuation_stall_threshold_seconds_v1()
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
