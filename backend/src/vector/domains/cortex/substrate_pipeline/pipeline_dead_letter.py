"""Durable recoverable dead-letter queue for substrate pipeline async failures."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
    hash_reasoning_canonical_json_sha256_v1,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_dead_letter import (
    CortexSubstratePipelineDeadLetter,
)
from vector.settings import Settings, get_settings

_LOGGER = logging.getLogger(__name__)

DLQ_STATUS_OPEN: Final[str] = "open"
DLQ_STATUS_RECOVERED: Final[str] = "recovered"
DLQ_STATUS_CLOSED: Final[str] = "closed"

FAILURE_CLASS_TCRE_FAILED: Final[str] = "tcre_failed"
FAILURE_CLASS_TCRE_MISSING_SCOPE: Final[str] = "tcre_missing_scope"
FAILURE_CLASS_CELERY_LOST: Final[str] = "celery_lost"
FAILURE_CLASS_CONTINUATION_MISSING: Final[str] = "continuation_missing"
FAILURE_CLASS_PHASE_ENQUEUE_FAILED: Final[str] = "phase_enqueue_failed"
FAILURE_CLASS_WALK_POISON: Final[str] = "walk_poison"

FAILURE_CLASS_IDS_V1: Final[tuple[str, ...]] = (
    FAILURE_CLASS_TCRE_FAILED,
    FAILURE_CLASS_TCRE_MISSING_SCOPE,
    FAILURE_CLASS_CELERY_LOST,
    FAILURE_CLASS_CONTINUATION_MISSING,
    FAILURE_CLASS_PHASE_ENQUEUE_FAILED,
    FAILURE_CLASS_WALK_POISON,
)

RECOVERY_ACTION_RETRY_CONTINUATION: Final[str] = "retry_continuation"
RECOVERY_ACTION_REBIND_TCRE: Final[str] = "rebind_tcre"
RECOVERY_ACTION_RESUME_PHASE_07: Final[str] = "resume_phase_07"
RECOVERY_ACTION_REPLAY_CALLBACK: Final[str] = "replay_callback"
RECOVERY_ACTION_MARK_UNRECOVERABLE: Final[str] = "mark_unrecoverable"
RECOVERY_ACTION_REPLAY_PHASE_06: Final[str] = "replay_phase_06"

RECOVERY_ACTION_IDS_V1: Final[tuple[str, ...]] = (
    RECOVERY_ACTION_RETRY_CONTINUATION,
    RECOVERY_ACTION_REBIND_TCRE,
    RECOVERY_ACTION_RESUME_PHASE_07,
    RECOVERY_ACTION_REPLAY_CALLBACK,
    RECOVERY_ACTION_REPLAY_PHASE_06,
    RECOVERY_ACTION_MARK_UNRECOVERABLE,
)

_DEFAULT_RECOVERY_ACTIONS_BY_FAILURE_V1: Final[dict[str, tuple[str, ...]]] = {
    FAILURE_CLASS_TCRE_FAILED: (
        RECOVERY_ACTION_REBIND_TCRE,
        RECOVERY_ACTION_REPLAY_PHASE_06,
        RECOVERY_ACTION_MARK_UNRECOVERABLE,
    ),
    FAILURE_CLASS_TCRE_MISSING_SCOPE: (
        RECOVERY_ACTION_REPLAY_PHASE_06,
        RECOVERY_ACTION_MARK_UNRECOVERABLE,
    ),
    FAILURE_CLASS_CELERY_LOST: (
        RECOVERY_ACTION_REBIND_TCRE,
        RECOVERY_ACTION_RETRY_CONTINUATION,
        RECOVERY_ACTION_MARK_UNRECOVERABLE,
    ),
    FAILURE_CLASS_CONTINUATION_MISSING: (
        RECOVERY_ACTION_RETRY_CONTINUATION,
        RECOVERY_ACTION_REPLAY_CALLBACK,
        RECOVERY_ACTION_RESUME_PHASE_07,
    ),
    FAILURE_CLASS_PHASE_ENQUEUE_FAILED: (
        RECOVERY_ACTION_RETRY_CONTINUATION,
        RECOVERY_ACTION_RESUME_PHASE_07,
        RECOVERY_ACTION_MARK_UNRECOVERABLE,
    ),
    FAILURE_CLASS_WALK_POISON: (RECOVERY_ACTION_MARK_UNRECOVERABLE,),
}

_REPLAY_SAFE_BY_FAILURE_V1: Final[dict[str, bool]] = {
    FAILURE_CLASS_TCRE_FAILED: False,
    FAILURE_CLASS_TCRE_MISSING_SCOPE: False,
    FAILURE_CLASS_CELERY_LOST: True,
    FAILURE_CLASS_CONTINUATION_MISSING: True,
    FAILURE_CLASS_PHASE_ENQUEUE_FAILED: True,
    FAILURE_CLASS_WALK_POISON: False,
}


class PipelineDeadLetterError(ValueError):
    def __init__(self, code: str, *, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.detail = dict(detail or {})
        super().__init__(code)


def get_dlq_max_auto_retries_per_receipt_v1(*, settings: Settings | None = None) -> int:
    cfg = settings or get_settings()
    return max(0, int(cfg.cortex_substrate_dlq_max_auto_retries_per_receipt))


def default_recovery_actions_for_failure_class_v1(failure_class: str) -> list[str]:
    if failure_class not in FAILURE_CLASS_IDS_V1:
        msg = f"unknown_failure_class:{failure_class}"
        raise PipelineDeadLetterError(msg)
    return list(_DEFAULT_RECOVERY_ACTIONS_BY_FAILURE_V1[failure_class])


def assert_failure_class_closed_v1(failure_class: str) -> None:
    if failure_class not in FAILURE_CLASS_IDS_V1:
        raise PipelineDeadLetterError(
            "failure_class_not_closed",
            detail={"failure_class": failure_class, "allowed": list(FAILURE_CLASS_IDS_V1)},
        )


def dead_letter_public_dict_v1(row: CortexSubstratePipelineDeadLetter) -> dict[str, Any]:
    return {
        "dead_letter_id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "pipeline_run_id": str(row.pipeline_run_id),
        "phase_id": row.phase_id,
        "async_job_id": str(row.async_job_id) if row.async_job_id else None,
        "failure_class": row.failure_class,
        "replay_safe": bool(row.replay_safe),
        "recovery_actions": list(row.recovery_actions or []),
        "resume_receipt_hash": row.resume_receipt_hash,
        "auto_retry_count": int(row.auto_retry_count or 0),
        "dlq_status": row.dlq_status,
        "failure_detail": row.failure_detail,
        "detail_json": dict(row.detail_json or {}),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
    }


def count_dlq_auto_retries_for_receipt_v1(
    session: Session,
    *,
    resume_receipt_hash: str,
) -> int:
    """Sum auto-retry attempts recorded on open DLQ rows for one receipt (**G-P085-DLQ-01**)."""
    if not resume_receipt_hash.strip():
        return 0
    total = session.scalar(
        select(func.coalesce(func.sum(CortexSubstratePipelineDeadLetter.auto_retry_count), 0)).where(
            CortexSubstratePipelineDeadLetter.resume_receipt_hash == resume_receipt_hash,
            CortexSubstratePipelineDeadLetter.dlq_status == DLQ_STATUS_OPEN,
        )
    )
    return int(total or 0)


def assert_dlq_auto_retry_budget_v1(
    session: Session,
    *,
    resume_receipt_hash: str | None,
    settings: Settings | None = None,
) -> None:
    """Block auto-retry when ``N_max`` attempts per ``resume_receipt_hash`` exhausted."""
    if not resume_receipt_hash:
        return
    n_max = get_dlq_max_auto_retries_per_receipt_v1(settings=settings)
    if n_max <= 0:
        return
    used = count_dlq_auto_retries_for_receipt_v1(session, resume_receipt_hash=resume_receipt_hash)
    if used >= n_max:
        raise PipelineDeadLetterError(
            "dlq_auto_retry_budget_exhausted",
            detail={
                "resume_receipt_hash": resume_receipt_hash,
                "auto_retry_count": used,
                "n_max": n_max,
            },
        )


def record_pipeline_dead_letter_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    phase_id: str,
    failure_class: str,
    async_job_id: uuid.UUID | None = None,
    resume_receipt_hash: str | None = None,
    failure_detail: str | None = None,
    recovery_actions: Sequence[str] | None = None,
    replay_safe: bool | None = None,
    detail: Mapping[str, Any] | None = None,
    auto_retry_increment: int = 0,
) -> CortexSubstratePipelineDeadLetter:
    """Persist recoverable DLQ row for operator / watchdog recovery."""
    assert_failure_class_closed_v1(failure_class)
    actions = (
        list(recovery_actions)
        if recovery_actions is not None
        else default_recovery_actions_for_failure_class_v1(failure_class)
    )
    safe = (
        bool(replay_safe)
        if replay_safe is not None
        else _REPLAY_SAFE_BY_FAILURE_V1.get(failure_class, True)
    )
    existing = session.scalar(
        select(CortexSubstratePipelineDeadLetter)
        .where(
            CortexSubstratePipelineDeadLetter.pipeline_run_id == pipeline_run_id,
            CortexSubstratePipelineDeadLetter.failure_class == failure_class,
            CortexSubstratePipelineDeadLetter.dlq_status == DLQ_STATUS_OPEN,
        )
        .order_by(CortexSubstratePipelineDeadLetter.created_at.desc())
        .limit(1)
    )
    if existing is not None:
        existing.phase_id = phase_id
        existing.async_job_id = async_job_id
        existing.replay_safe = safe
        existing.recovery_actions = actions
        if resume_receipt_hash:
            existing.resume_receipt_hash = resume_receipt_hash
        if failure_detail:
            existing.failure_detail = failure_detail[:2000]
        merged = dict(existing.detail_json or {})
        merged.update(dict(detail or {}))
        existing.detail_json = merged
        if auto_retry_increment > 0:
            existing.auto_retry_count = int(existing.auto_retry_count or 0) + auto_retry_increment
        session.flush()
        _LOGGER.warning(
            "pipeline_dlq_updated tenant_id=%s pipeline_run_id=%s failure_class=%s",
            tenant_id,
            pipeline_run_id,
            failure_class,
        )
        return existing

    row = CortexSubstratePipelineDeadLetter(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        phase_id=phase_id,
        async_job_id=async_job_id,
        failure_class=failure_class,
        replay_safe=safe,
        recovery_actions=actions,
        resume_receipt_hash=resume_receipt_hash,
        auto_retry_count=max(0, int(auto_retry_increment)),
        dlq_status=DLQ_STATUS_OPEN,
        failure_detail=(failure_detail or "")[:2000] or None,
        detail_json=dict(detail or {}),
    )
    session.add(row)
    session.flush()
    from vector.domains.cortex.operational_runtime.recovery_continuity import (
        increment_dlq_metric_v1,
    )

    increment_dlq_metric_v1("substrate_dlq_open_total")
    _LOGGER.warning(
        "pipeline_dlq_created tenant_id=%s pipeline_run_id=%s failure_class=%s dead_letter_id=%s",
        tenant_id,
        pipeline_run_id,
        failure_class,
        row.id,
    )
    return row


def list_open_dead_letters_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    lim = max(1, min(limit, 500))
    stmt = select(CortexSubstratePipelineDeadLetter).where(
        CortexSubstratePipelineDeadLetter.dlq_status == DLQ_STATUS_OPEN,
    )
    if tenant_id is not None:
        stmt = stmt.where(CortexSubstratePipelineDeadLetter.tenant_id == tenant_id)
    rows = list(
        session.scalars(
            stmt.order_by(CortexSubstratePipelineDeadLetter.created_at.desc()).limit(lim)
        ).all()
    )
    return [dead_letter_public_dict_v1(r) for r in rows]


def resolve_open_dlq_for_pipeline_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    outcome: str = DLQ_STATUS_RECOVERED,
    detail: Mapping[str, Any] | None = None,
) -> int:
    """Resolve all open DLQ rows for one pipeline run."""
    rows = list(
        session.scalars(
            select(CortexSubstratePipelineDeadLetter).where(
                CortexSubstratePipelineDeadLetter.pipeline_run_id == pipeline_run_id,
                CortexSubstratePipelineDeadLetter.dlq_status == DLQ_STATUS_OPEN,
            )
        ).all()
    )
    count = 0
    for row in rows:
        resolve_dead_letter_v1(
            session,
            dead_letter_id=row.id,
            outcome=outcome,
            detail=detail,
        )
        count += 1
    return count


def resolve_dead_letter_v1(
    session: Session,
    *,
    dead_letter_id: uuid.UUID,
    outcome: str = DLQ_STATUS_RECOVERED,
    detail: Mapping[str, Any] | None = None,
) -> CortexSubstratePipelineDeadLetter | None:
    row = session.get(CortexSubstratePipelineDeadLetter, dead_letter_id)
    if row is None:
        return None
    if outcome not in (DLQ_STATUS_RECOVERED, DLQ_STATUS_CLOSED):
        raise PipelineDeadLetterError("invalid_dlq_resolve_outcome", detail={"outcome": outcome})
    row.dlq_status = outcome
    row.resolved_at = datetime.now(UTC)
    merged = dict(row.detail_json or {})
    merged.update(dict(detail or {}))
    row.detail_json = merged
    session.flush()
    from vector.domains.cortex.operational_runtime.recovery_continuity import (
        increment_dlq_metric_v1,
    )

    increment_dlq_metric_v1("substrate_dlq_resolved_total")
    return row


def compute_dlq_failure_digest_v1(
    *,
    pipeline_run_id: uuid.UUID,
    failure_class: str,
    phase_id: str,
    async_job_id: uuid.UUID | None = None,
) -> str:
    return hash_reasoning_canonical_json_sha256_v1(
        {
            "pipeline_run_id": str(pipeline_run_id),
            "failure_class": failure_class,
            "phase_id": phase_id,
            "async_job_id": str(async_job_id) if async_job_id else None,
            "purpose": "pipeline_dlq_failure_digest_v1",
        }
    )[:64]
