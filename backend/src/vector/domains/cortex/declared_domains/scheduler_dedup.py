"""Declared domain scheduled-pass enqueue deduplication."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.declared_domains.pass_run_ops import (
    RUN_RUNNING,
    abandon_stuck_running_declared_domain_passes,
)
from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.infrastructure.db.models.declared_domain_pass_run import DeclaredDomainPassRun


def should_skip_scheduled_declared_domain_pass(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    interval_seconds: int,
) -> bool:
    abandon_stuck_running_declared_domain_passes(
        session,
        tenant_id=tenant_id,
        interval_seconds=interval_seconds,
    )
    in_flight_window = max(120, int(interval_seconds) * 2)
    running = session.scalar(
        select(DeclaredDomainPassRun.id)
        .where(
            DeclaredDomainPassRun.tenant_id == tenant_id,
            DeclaredDomainPassRun.status == RUN_RUNNING,
            DeclaredDomainPassRun.started_at >= utc_now() - timedelta(seconds=in_flight_window),
        )
        .limit(1),
    )
    if running is not None:
        return True
    min_gap = max(60, int(interval_seconds * 0.85))
    recent = session.scalar(
        select(DeclaredDomainPassRun.id)
        .where(
            DeclaredDomainPassRun.tenant_id == tenant_id,
            DeclaredDomainPassRun.source_trigger == "scheduled",
            DeclaredDomainPassRun.started_at >= utc_now() - timedelta(seconds=min_gap),
        )
        .limit(1),
    )
    return recent is not None
