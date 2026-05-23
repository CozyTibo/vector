"""R1 — sweeper support for tenants WAITING on async TCRE (resume execution lane)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.enqueue import enqueue_tenant_convergence_v1
from vector.domains.cortex.execution.lease import resume_convergence_from_waiting_v1
from vector.domains.cortex.execution.tcre_job_lifecycle import (
    drain_stale_queued_tcre_jobs_v1,
    list_stale_queued_tcre_jobs_v1,
    snapshot_tcre_job_status_histogram_v1,
    tcre_job_queued_stale_seconds_v1,
)
from vector.domains.cortex.execution.tenant_constants import LEASE_STATUS_WAITING
from vector.domains.cortex.substrate_pipeline.constants import PHASE_07_RETRIEVAL
from vector.infrastructure.db.models.cortex_tenant_convergence_lease import CortexTenantConvergenceLease
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob
from vector.settings import Settings, get_settings

_LOGGER = logging.getLogger(__name__)


def list_tenants_waiting_on_tcre_for_sweep_v1(
    session: Session,
    *,
    limit: int,
    settings: Settings | None = None,
) -> list[uuid.UUID]:
    """Tenants in WAITING/tcre_async that may need drain or resume."""
    cfg = settings or get_settings()
    if not bool(getattr(cfg, "cortex_convergence_sweep_tcre_waiting_enabled", True)):
        return []
    stale_sec = tcre_job_queued_stale_seconds_v1(settings=cfg)
    rows = list(
        session.scalars(
            select(CortexTenantConvergenceLease.tenant_id)
            .where(CortexTenantConvergenceLease.status == LEASE_STATUS_WAITING)
            .order_by(CortexTenantConvergenceLease.updated_at.asc().nullsfirst())
            .limit(max(1, min(int(limit), 500)))
        ).all()
    )
    out: list[uuid.UUID] = []
    for tid in rows:
        lease = session.get(CortexTenantConvergenceLease, tid)
        if lease is None:
            continue
        detail = dict(lease.detail_json or {})
        if detail.get("waiting_reason") != "tcre_async":
            continue
        hist = snapshot_tcre_job_status_histogram_v1(session, tenant_id=tid)
        queued = int(hist.get("queued") or 0)
        completed = int(hist.get("completed") or 0)
        stale_queued = list_stale_queued_tcre_jobs_v1(
            session,
            tenant_id=tid,
            stale_after_seconds=stale_sec,
            max_rows=1,
        )
        if stale_queued or (queued == 0 and completed > 0):
            out.append(tid)
    return out


def sweep_tcre_waiting_tenant_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Drain stale queued TCRE jobs and/or resume lease at phase 07."""
    cfg = settings or get_settings()
    stale_sec = tcre_job_queued_stale_seconds_v1(settings=cfg)
    hist_before = snapshot_tcre_job_status_histogram_v1(session, tenant_id=tenant_id)
    drain = drain_stale_queued_tcre_jobs_v1(
        session,
        tenant_id=tenant_id,
        stale_after_seconds=stale_sec,
        dry_run=False,
        enqueue_convergence=False,
    )
    hist_after = snapshot_tcre_job_status_histogram_v1(session, tenant_id=tenant_id)
    queued = int(hist_after.get("queued") or 0)
    completed = int(hist_after.get("completed") or 0)
    resumed = False
    enqueue_hint: dict[str, Any] | None = None
    if queued == 0 and completed > 0:
        lease_row = session.get(CortexTenantConvergenceLease, tenant_id)
        pipeline_run_id = lease_row.pipeline_run_id if lease_row else None
        resume_convergence_from_waiting_v1(
            session,
            tenant_id=tenant_id,
            phase_cursor=PHASE_07_RETRIEVAL,
            pipeline_run_id=pipeline_run_id,
        )
        resumed = True
        try:
            enqueue_hint = enqueue_tenant_convergence_v1(tenant_id, reason="sweep_tcre_waiting_resume")
        except Exception as exc:  # noqa: BLE001
            enqueue_hint = {"enqueued": False, "error": str(exc)[:500]}
            _LOGGER.warning(
                "sweep_tcre_waiting_enqueue_failed tenant_id=%s",
                tenant_id,
                exc_info=True,
            )
    elif queued > 0:
        running = int(
            session.scalar(
                select(func.count())
                .select_from(CortexTcreReconstructionJob)
                .where(
                    CortexTcreReconstructionJob.tenant_id == tenant_id,
                    CortexTcreReconstructionJob.status == "running",
                )
            )
            or 0
        )
        if running == 0 and list_stale_queued_tcre_jobs_v1(
            session,
            tenant_id=tenant_id,
            stale_after_seconds=stale_sec,
            max_rows=1,
        ):
            drain = drain_stale_queued_tcre_jobs_v1(
                session,
                tenant_id=tenant_id,
                stale_after_seconds=stale_sec,
                dry_run=False,
                enqueue_convergence=True,
            )
    return {
        "tenant_id": str(tenant_id),
        "histogram_before": hist_before,
        "histogram_after": hist_after,
        "drain": drain,
        "resumed_from_waiting": resumed,
        "enqueue": enqueue_hint,
    }
