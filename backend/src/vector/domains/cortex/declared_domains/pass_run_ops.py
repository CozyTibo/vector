"""Declared domain pass run lifecycle helpers."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.infrastructure.db.models.declared_domain_pass_run import DeclaredDomainPassRun

RUN_RUNNING = "RUNNING"
RUN_COMPLETED = "COMPLETED"
RUN_FAILED = "FAILED"


def abandon_stuck_running_declared_domain_passes(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    interval_seconds: int,
) -> int:
    cutoff = utc_now() - timedelta(seconds=max(300, int(interval_seconds) * 4))
    result = session.execute(
        update(DeclaredDomainPassRun)
        .where(
            DeclaredDomainPassRun.tenant_id == tenant_id,
            DeclaredDomainPassRun.status == RUN_RUNNING,
            DeclaredDomainPassRun.started_at < cutoff,
        )
        .values(
            status=RUN_FAILED,
            finished_at=utc_now(),
            error_summary="abandoned_stuck_running",
        ),
    )
    return int(result.rowcount or 0)


def latest_declared_domain_pass_run(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> DeclaredDomainPassRun | None:
    return session.scalar(
        select(DeclaredDomainPassRun)
        .where(DeclaredDomainPassRun.tenant_id == tenant_id)
        .order_by(DeclaredDomainPassRun.started_at.desc())
        .limit(1),
    )
