"""Phase A step A3 — TCRE reconstruction job queue drain (stale ``queued`` cleanup)."""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.tcre_resume import on_tcre_job_terminal_for_execution_v1
from vector.domains.cortex.reasoning.runtime.reasoning_runtime_orchestrator import (
    execute_tcre_reconstruction_job_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import PHASE_07_RETRIEVAL
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)
from vector.settings import Settings, get_settings

PHASE_A_TCRE_JOB_LIFECYCLE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

P0_A3_STEP: Final[str] = "step_a3_tcre_queued_drain"

STALE_QUEUED_RECONCILE_CODE_V1: Final[str] = "tcre_job_stale_queued_drained"

ORPHAN_RUNNING_CODE_V1: Final[str] = "tcre_job_orphan_running"

TCRE_JOB_TERMINAL_STATUSES_V1: Final[frozenset[str]] = frozenset(
    {"completed", "failed", "cancelled"},
)


def tcre_job_queued_stale_seconds_v1(*, settings: Settings | None = None) -> int:
    cfg = settings or get_settings()
    return int(cfg.cortex_tcre_job_queued_stale_seconds)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def snapshot_tcre_job_status_histogram_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, int]:
    rows = session.execute(
        select(CortexTcreReconstructionJob.status, func.count())
        .where(CortexTcreReconstructionJob.tenant_id == tenant_id)
        .group_by(CortexTcreReconstructionJob.status),
    ).all()
    hist = {str(status): int(count) for status, count in rows}
    hist["total"] = sum(hist.values())
    hist["queued"] = int(hist.get("queued", 0))
    hist["running"] = int(hist.get("running", 0))
    hist["completed"] = int(hist.get("completed", 0))
    hist["failed"] = int(hist.get("failed", 0))
    return hist


def count_stale_queued_tcre_jobs_v1(
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
            .select_from(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status == "queued",
                CortexTcreReconstructionJob.created_at < cutoff,
            ),
        )
        or 0,
    )


def list_stale_queued_tcre_jobs_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stale_after_seconds: int,
    max_rows: int = 32,
    now: datetime | None = None,
) -> list[CortexTcreReconstructionJob]:
    cutoff = (now or _utc_now()) - timedelta(seconds=stale_after_seconds)
    return list(
        session.scalars(
            select(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status == "queued",
                CortexTcreReconstructionJob.created_at < cutoff,
            )
            .order_by(CortexTcreReconstructionJob.created_at.asc())
            .limit(max_rows),
        ).all(),
    )


def terminalize_tcre_job_failed_v1(
    job: CortexTcreReconstructionJob,
    *,
    error_code: str,
    completed_at: datetime | None = None,
) -> None:
    if job.status in TCRE_JOB_TERMINAL_STATUSES_V1:
        return
    job.status = "failed"
    job.error_detail = error_code
    job.completed_at = completed_at or _utc_now()
    if job.started_at is None:
        job.started_at = job.completed_at


def _pipeline_run_id_from_scope(scope: Mapping[str, Any]) -> uuid.UUID | None:
    raw = scope.get("substrate_pipeline_run_id")
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        return None


def drain_stale_queued_tcre_jobs_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stale_after_seconds: int | None = None,
    max_jobs: int = 32,
    resume_execution: bool = True,
    enqueue_convergence: bool = True,
    dry_run: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Execute stale ``queued`` TCRE jobs inline and resume execution at phase 07 when completed."""
    stale_sec = (
        stale_after_seconds
        if stale_after_seconds is not None
        else tcre_job_queued_stale_seconds_v1()
    )
    ref_now = now or _utc_now()
    before = snapshot_tcre_job_status_histogram_v1(session, tenant_id=tenant_id)
    stale_before = count_stale_queued_tcre_jobs_v1(
        session,
        tenant_id=tenant_id,
        stale_after_seconds=stale_sec,
        now=ref_now,
    )
    jobs = list_stale_queued_tcre_jobs_v1(
        session,
        tenant_id=tenant_id,
        stale_after_seconds=stale_sec,
        max_rows=max_jobs,
        now=ref_now,
    )

    drained: list[dict[str, Any]] = []
    if not dry_run:
        for job in jobs:
            pipeline_run_id = _pipeline_run_id_from_scope(job.scope_json or {})
            row: dict[str, Any] = {
                "job_id": str(job.id),
                "pipeline_run_id": str(pipeline_run_id) if pipeline_run_id else None,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            }
            try:
                summary = execute_tcre_reconstruction_job_v1(session, job)
                row["status"] = job.status
                row["summary_keys"] = list(summary.keys()) if isinstance(summary, Mapping) else []
            except Exception as exc:  # noqa: BLE001
                row["status"] = getattr(job, "status", "failed")
                row["error"] = str(exc)[:500]
                drained.append(row)
                continue

            resume_out = None
            if resume_execution and job.status == "completed" and pipeline_run_id is not None:
                resume_out = on_tcre_job_terminal_for_execution_v1(
                    session,
                    tenant_id=tenant_id,
                    pipeline_run_id=pipeline_run_id,
                    tcre_job_id=job.id,
                    tcre_job_status=str(job.status),
                    enqueue_convergence=enqueue_convergence,
                )
            row["resume"] = resume_out
            row["drain_code"] = STALE_QUEUED_RECONCILE_CODE_V1
            drained.append(row)
        if drained:
            session.flush()

    after = snapshot_tcre_job_status_histogram_v1(session, tenant_id=tenant_id)
    stale_after = count_stale_queued_tcre_jobs_v1(
        session,
        tenant_id=tenant_id,
        stale_after_seconds=stale_sec,
        now=ref_now,
    )
    return {
        "surface_kind": "tcre_job_drain",
        "phase_a_tcre_job_lifecycle_runtime_schema_version": (
            PHASE_A_TCRE_JOB_LIFECYCLE_RUNTIME_SCHEMA_VERSION
        ),
        "tenant_id": str(tenant_id),
        "dry_run": dry_run,
        "stale_after_seconds": stale_sec,
        "stale_queued_before": stale_before,
        "stale_queued_after": stale_after,
        "jobs_candidates": len(jobs),
        "jobs_drained": len(drained),
        "drained_jobs": drained,
        "histogram_before": before,
        "histogram_after": after,
        "resume_phase_cursor": PHASE_07_RETRIEVAL,
    }
