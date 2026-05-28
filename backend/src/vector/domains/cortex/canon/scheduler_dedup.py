"""Canon scheduled-pass enqueue deduplication."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.pass_run_ops import RUN_RUNNING, abandon_stuck_running_canon_passes
from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.infrastructure.db.models.canon_pass_run import CanonPassRun


def should_skip_scheduled_canon_pass(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    interval_seconds: int,
) -> bool:
    """Avoid duplicate scheduled passes (multiple Beat containers or slow workers)."""
    abandon_stuck_running_canon_passes(
        session,
        tenant_id=tenant_id,
        interval_seconds=interval_seconds,
    )
    in_flight_window = max(120, int(interval_seconds) * 2)
    running = session.scalar(
        select(CanonPassRun.id)
        .where(
            CanonPassRun.tenant_id == tenant_id,
            CanonPassRun.status == RUN_RUNNING,
            CanonPassRun.started_at >= utc_now() - timedelta(seconds=in_flight_window),
        )
        .limit(1),
    )
    if running is not None:
        return True
    min_gap = max(60, int(interval_seconds * 0.85))
    recent = session.scalar(
        select(CanonPassRun.id)
        .where(
            CanonPassRun.tenant_id == tenant_id,
            CanonPassRun.source_trigger == "scheduled",
            CanonPassRun.started_at >= utc_now() - timedelta(seconds=min_gap),
        )
        .limit(1),
    )
    return recent is not None
