"""Phase A step A1 — synthesis job lifecycle reconciliation (stale ``running`` cleanup)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.synthesis.synthesis_repository import (
    SynthesisRepositoryError,
    assert_synthesis_idempotency_key_v1,
    create_synthesis_job_row_v1,
    envelope_json_for_persistence_v1,
    find_idempotent_synthesis_job_v1,
)
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.settings import Settings, get_settings

PHASE_A_SYNTHESIS_JOB_LIFECYCLE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

P0_A1_STEP: Final[str] = "step_a1_synthesis_job_reconcile"

SYNTHESIS_JOB_TERMINAL_STATUSES_V1: Final[frozenset[str]] = frozenset(
    {"completed", "failed", "cancelled"},
)

SYNTHESIS_JOB_INFLIGHT_STATUSES_V1: Final[frozenset[str]] = frozenset({"queued", "running"})

STALE_RUNNING_RECONCILE_CODE_V1: Final[str] = "synthesis_job_stale_running_reconciled"

STALE_RUNNING_SUPERSEDED_CODE_V1: Final[str] = "synthesis_job_stale_running_superseded"

STALE_QUEUED_SUPERSEDED_CODE_V1: Final[str] = "synthesis_job_stale_queued_superseded"

DUPLICATE_INFLIGHT_SUPERSEDED_CODE_V1: Final[str] = "synthesis_job_duplicate_inflight_superseded"

ORPHAN_RUNNING_CODE_V1: Final[str] = "synthesis_job_orphan_running"

P0_A6_STEP: Final[str] = "step_a6_synthesis_terminal_transitions"

PHASE_A_SYNTHESIS_TERMINAL_RUNTIME_SCHEMA_VERSION: Final[int] = 1


def synthesis_job_running_stale_seconds_v1(*, settings: Settings | None = None) -> int:
    cfg = settings or get_settings()
    return int(cfg.cortex_synthesis_job_running_stale_seconds)


def synthesis_job_running_alert_threshold_v1(*, settings: Settings | None = None) -> int:
    cfg = settings or get_settings()
    return int(cfg.cortex_synthesis_job_running_alert_threshold)


def is_synthesis_job_reconcile_on_materialize_enabled_v1(*, settings: Settings | None = None) -> bool:
    cfg = settings or get_settings()
    return bool(cfg.cortex_synthesis_job_reconcile_on_materialize)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _job_started_or_created_at(job: CortexSynthesisJob) -> datetime:
    if job.started_at is not None:
        return job.started_at
    return job.created_at


def is_synthesis_job_running_stale_v1(
    job: CortexSynthesisJob,
    *,
    stale_after_seconds: int,
    now: datetime | None = None,
) -> bool:
    if job.status != "running":
        return False
    ref = _job_started_or_created_at(job)
    cutoff = (now or _utc_now()) - timedelta(seconds=stale_after_seconds)
    return ref < cutoff


def snapshot_synthesis_job_status_histogram_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, int]:
    rows = session.execute(
        select(CortexSynthesisJob.status, func.count())
        .where(CortexSynthesisJob.tenant_id == tenant_id)
        .group_by(CortexSynthesisJob.status),
    ).all()
    hist = {str(status): int(count) for status, count in rows}
    hist["total"] = sum(hist.values())
    hist["running"] = int(hist.get("running", 0))
    hist["queued"] = int(hist.get("queued", 0))
    hist["completed"] = int(hist.get("completed", 0))
    hist["failed"] = int(hist.get("failed", 0))
    return hist


def count_stale_running_synthesis_jobs_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stale_after_seconds: int,
    now: datetime | None = None,
) -> int:
    cutoff = (now or _utc_now()) - timedelta(seconds=stale_after_seconds)
    return int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.status == "running",
                func.coalesce(CortexSynthesisJob.started_at, CortexSynthesisJob.created_at) < cutoff,
            ),
        )
        or 0,
    )


def find_inflight_synthesis_job_by_idempotency_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    idempotency_key: str,
    envelope_digest: str,
) -> CortexSynthesisJob | None:
    """Latest queued/running job for tenant + idempotency key + digest."""
    return session.scalar(
        select(CortexSynthesisJob)
        .where(
            CortexSynthesisJob.tenant_id == tenant_id,
            CortexSynthesisJob.idempotency_key == idempotency_key,
            CortexSynthesisJob.envelope_digest == envelope_digest,
            CortexSynthesisJob.status.in_(tuple(SYNTHESIS_JOB_INFLIGHT_STATUSES_V1)),
        )
        .order_by(CortexSynthesisJob.created_at.desc())
        .limit(1),
    )


def terminalize_synthesis_job_failed_v1(
    job: CortexSynthesisJob,
    *,
    error_code: str,
    execution_trace: Sequence[Mapping[str, Any]] | None = None,
    completed_at: datetime | None = None,
) -> None:
    """Mark a non-terminal job failed (idempotent when already terminal)."""
    if job.status in SYNTHESIS_JOB_TERMINAL_STATUSES_V1:
        return
    job.status = "failed"
    job.error_detail = error_code
    job.completed_at = completed_at or _utc_now()
    if execution_trace is not None:
        job.execution_trace_json = list(execution_trace)


def terminalize_synthesis_job_completed_v1(
    job: CortexSynthesisJob,
    *,
    execution_trace: Sequence[Mapping[str, Any]] | None = None,
    completed_at: datetime | None = None,
) -> None:
    """Mark a non-terminal job completed (idempotent when already terminal)."""
    if job.status in SYNTHESIS_JOB_TERMINAL_STATUSES_V1:
        return
    job.status = "completed"
    job.error_detail = None
    job.completed_at = completed_at or _utc_now()
    if execution_trace is not None:
        job.execution_trace_json = list(execution_trace)


def list_inflight_synthesis_jobs_by_idempotency_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    idempotency_key: str,
    envelope_digest: str,
) -> list[CortexSynthesisJob]:
    return list(
        session.scalars(
            select(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.idempotency_key == idempotency_key,
                CortexSynthesisJob.envelope_digest == envelope_digest,
                CortexSynthesisJob.status.in_(tuple(SYNTHESIS_JOB_INFLIGHT_STATUSES_V1)),
            )
            .order_by(CortexSynthesisJob.created_at.desc())
        ).all()
    )


def supersede_duplicate_inflight_synthesis_jobs_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    idempotency_key: str,
    envelope_digest: str,
    keep_job_id: uuid.UUID,
    completed_at: datetime | None = None,
) -> int:
    """Fail duplicate queued/running rows for the same idempotency (single enqueue path)."""
    ref_now = completed_at or _utc_now()
    superseded = 0
    for row in list_inflight_synthesis_jobs_by_idempotency_v1(
        session,
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        envelope_digest=envelope_digest,
    ):
        if row.id == keep_job_id:
            continue
        terminalize_synthesis_job_failed_v1(
            row,
            error_code=DUPLICATE_INFLIGHT_SUPERSEDED_CODE_V1,
            completed_at=ref_now,
        )
        superseded += 1
    if superseded:
        session.flush()
    return superseded


def is_synthesis_job_queued_stale_v1(
    job: CortexSynthesisJob,
    *,
    stale_after_seconds: int,
    now: datetime | None = None,
) -> bool:
    if job.status != "queued":
        return False
    cutoff = (now or _utc_now()) - timedelta(seconds=stale_after_seconds)
    return job.created_at < cutoff


def reconcile_stale_queued_synthesis_jobs_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stale_after_seconds: int,
    dry_run: bool = False,
    max_rows: int = 10_000,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Fail ``queued`` jobs older than ``stale_after_seconds`` (prevents orphan queued rows)."""
    ref_now = now or _utc_now()
    cutoff = ref_now - timedelta(seconds=max(stale_after_seconds, 0))
    stmt = (
        select(CortexSynthesisJob)
        .where(
            CortexSynthesisJob.tenant_id == tenant_id,
            CortexSynthesisJob.status == "queued",
            CortexSynthesisJob.created_at < cutoff,
        )
        .order_by(CortexSynthesisJob.created_at.asc())
        .limit(max_rows)
    )
    stale_jobs = list(session.scalars(stmt).all())
    if not dry_run:
        for job in stale_jobs:
            terminalize_synthesis_job_failed_v1(
                job,
                error_code=STALE_QUEUED_SUPERSEDED_CODE_V1,
                completed_at=ref_now,
            )
        if stale_jobs:
            session.flush()
    return {
        "stale_queued_count": len(stale_jobs),
        "error_code": STALE_QUEUED_SUPERSEDED_CODE_V1,
        "dry_run": dry_run,
    }


@dataclass(frozen=True)
class SynthesisJobExecutePrepareV1:
    """Result of ``prepare_synthesis_job_row_for_execute_v1`` (single enqueue path)."""

    job: CortexSynthesisJob
    idempotent_completed_job: CortexSynthesisJob | None = None
    superseded_inflight_count: int = 0


def prepare_synthesis_job_row_for_execute_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    envelope: Mapping[str, Any],
    envelope_digest: str,
    job_id: uuid.UUID | None = None,
    stale_after_seconds: int | None = None,
) -> SynthesisJobExecutePrepareV1:
    """Resolve idempotency, dedupe inflight rows, and return a runnable job row.

    Raises ``SynthesisRepositoryError`` when ``job_id`` is invalid for the tenant.
    """
    idem_key = envelope.get("idempotency_key")
    idem_str = str(idem_key) if idem_key else None
    if idem_str:
        completed = find_idempotent_synthesis_job_v1(
            session,
            tenant_id=tenant_id,
            idempotency_key=idem_str,
            envelope_digest=envelope_digest,
        )
        if completed is not None and completed.receipt_digest:
            return SynthesisJobExecutePrepareV1(
                job=completed,
                idempotent_completed_job=completed,
            )

    resolved_job_id = job_id
    if resolved_job_id is None and idem_str:
        resolved_job_id = resolve_synthesis_job_before_execute_v1(
            session,
            tenant_id=tenant_id,
            idempotency_key=idem_str,
            envelope_digest=envelope_digest,
            stale_after_seconds=stale_after_seconds,
        )

    if resolved_job_id is not None:
        job = session.get(CortexSynthesisJob, resolved_job_id)
        if job is None or job.tenant_id != tenant_id:
            raise SynthesisRepositoryError(
                "synthesis_job_not_found",
                http_status=404,
            )
        if job.status not in SYNTHESIS_JOB_INFLIGHT_STATUSES_V1:
            raise SynthesisRepositoryError(
                "synthesis_job_not_runnable",
                http_status=409,
                detail={"status": job.status},
            )
        job.envelope_json = envelope_json_for_persistence_v1(envelope)
        job.envelope_digest = envelope_digest
    else:
        assert_synthesis_idempotency_key_v1(
            session,
            tenant_id=tenant_id,
            idempotency_key=idem_str,
            envelope_digest=envelope_digest,
        )
        job = create_synthesis_job_row_v1(
            session,
            tenant_id=tenant_id,
            envelope=envelope,
            envelope_digest=envelope_digest,
        )

    superseded = 0
    if idem_str:
        superseded = supersede_duplicate_inflight_synthesis_jobs_v1(
            session,
            tenant_id=tenant_id,
            idempotency_key=idem_str,
            envelope_digest=envelope_digest,
            keep_job_id=job.id,
        )

    job.status = "running"
    job.started_at = _utc_now()
    session.flush()
    return SynthesisJobExecutePrepareV1(
        job=job,
        superseded_inflight_count=superseded,
    )


def ensure_synthesis_job_terminal_after_execute_v1(
    job: CortexSynthesisJob,
    *,
    execution_trace: Sequence[Mapping[str, Any]] | None = None,
) -> str | None:
    """Guarantee no orphan ``running`` after execute (``finally`` safety net)."""
    if job.status == "running":
        terminalize_synthesis_job_failed_v1(
            job,
            error_code=ORPHAN_RUNNING_CODE_V1,
            execution_trace=execution_trace,
        )
        return ORPHAN_RUNNING_CODE_V1
    return None


def reconcile_stale_synthesis_jobs_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stale_after_seconds: int | None = None,
    dry_run: bool = False,
    max_rows: int = 10_000,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Fail ``running`` jobs older than ``stale_after_seconds`` (default from settings)."""
    stale_sec = stale_after_seconds if stale_after_seconds is not None else synthesis_job_running_stale_seconds_v1()
    ref_now = now or _utc_now()
    cutoff = ref_now - timedelta(seconds=max(stale_sec, 0))
    before = snapshot_synthesis_job_status_histogram_v1(session, tenant_id=tenant_id)

    stmt = select(CortexSynthesisJob).where(
        CortexSynthesisJob.tenant_id == tenant_id,
        CortexSynthesisJob.status == "running",
    )
    if stale_sec > 0:
        stmt = stmt.where(
            func.coalesce(CortexSynthesisJob.started_at, CortexSynthesisJob.created_at) < cutoff,
        )
    stmt = stmt.order_by(CortexSynthesisJob.created_at.asc()).limit(max_rows)
    stale_jobs = list(session.scalars(stmt).all())
    reconciled_ids: list[str] = []
    if not dry_run:
        for job in stale_jobs:
            terminalize_synthesis_job_failed_v1(
                job,
                error_code=STALE_RUNNING_RECONCILE_CODE_V1,
                completed_at=ref_now,
            )
            reconciled_ids.append(str(job.id))
        if reconciled_ids:
            session.flush()

    after = snapshot_synthesis_job_status_histogram_v1(session, tenant_id=tenant_id)
    stale_running_after = count_stale_running_synthesis_jobs_v1(
        session,
        tenant_id=tenant_id,
        stale_after_seconds=stale_sec if stale_sec > 0 else synthesis_job_running_stale_seconds_v1(),
    )
    return {
        "surface_kind": "synthesis_job_reconcile",
        "phase_a_synthesis_job_lifecycle_runtime_schema_version": (
            PHASE_A_SYNTHESIS_JOB_LIFECYCLE_RUNTIME_SCHEMA_VERSION
        ),
        "tenant_id": str(tenant_id),
        "dry_run": dry_run,
        "stale_after_seconds": stale_sec,
        "stale_cutoff": None if stale_sec <= 0 else cutoff.isoformat(),
        "reconcile_all_running": stale_sec <= 0,
        "reconciled_count": len(stale_jobs),
        "reconciled_job_ids_sample": reconciled_ids[:20],
        "histogram_before": before,
        "histogram_after": after,
        "stale_running_after": stale_running_after,
        "error_code": STALE_RUNNING_RECONCILE_CODE_V1,
    }


def resolve_synthesis_job_before_execute_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    idempotency_key: str | None,
    envelope_digest: str,
    stale_after_seconds: int | None = None,
) -> uuid.UUID | None:
    """Return existing inflight job id to resume, or None to create a new row.

    Stale ``running`` rows with the same idempotency key are failed before returning None.
    """
    if not idempotency_key:
        return None
    stale_sec = stale_after_seconds if stale_after_seconds is not None else synthesis_job_running_stale_seconds_v1()
    inflight = find_inflight_synthesis_job_by_idempotency_v1(
        session,
        tenant_id=tenant_id,
        idempotency_key=idempotency_key,
        envelope_digest=envelope_digest,
    )
    if inflight is None:
        return None
    if inflight.status == "running" and is_synthesis_job_running_stale_v1(
        inflight,
        stale_after_seconds=stale_sec,
    ):
        terminalize_synthesis_job_failed_v1(
            inflight,
            error_code=STALE_RUNNING_SUPERSEDED_CODE_V1,
        )
        session.flush()
        return None
    return inflight.id


def maybe_reconcile_synthesis_jobs_on_materialize_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
) -> dict[str, Any] | None:
    """Optional pre-flight reconcile before phase 08 materialization."""
    cfg = settings or get_settings()
    if not is_synthesis_job_reconcile_on_materialize_enabled_v1(settings=cfg):
        return None
    running = reconcile_stale_synthesis_jobs_v1(
        session,
        tenant_id=tenant_id,
        stale_after_seconds=synthesis_job_running_stale_seconds_v1(settings=cfg),
        dry_run=False,
    )
    queued = reconcile_stale_queued_synthesis_jobs_v1(
        session,
        tenant_id=tenant_id,
        stale_after_seconds=synthesis_job_queued_stale_seconds_v1(settings=cfg),
        dry_run=False,
    )
    return {
        "running_reconcile": running,
        "queued_reconcile": queued,
    }


def synthesis_job_queued_stale_seconds_v1(*, settings: Settings | None = None) -> int:
    cfg = settings or get_settings()
    return int(cfg.cortex_synthesis_job_queued_stale_seconds)


def snapshot_synthesis_job_terminal_health_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Histogram + stale inflight counts for continuity proofs."""
    stale_run_sec = synthesis_job_running_stale_seconds_v1()
    stale_q_sec = synthesis_job_queued_stale_seconds_v1()
    hist = snapshot_synthesis_job_status_histogram_v1(session, tenant_id=tenant_id)
    return {
        "histogram": hist,
        "running_count": int(hist.get("running", 0)),
        "queued_count": int(hist.get("queued", 0)),
        "stale_running_count": count_stale_running_synthesis_jobs_v1(
            session,
            tenant_id=tenant_id,
            stale_after_seconds=stale_run_sec,
        ),
        "stale_queued_count": int(
            reconcile_stale_queued_synthesis_jobs_v1(
                session,
                tenant_id=tenant_id,
                stale_after_seconds=stale_q_sec,
                dry_run=True,
            ).get("stale_queued_count")
            or 0
        ),
        "running_alert_threshold": synthesis_job_running_alert_threshold_v1(),
        "running_stale_seconds": stale_run_sec,
        "queued_stale_seconds": stale_q_sec,
    }
