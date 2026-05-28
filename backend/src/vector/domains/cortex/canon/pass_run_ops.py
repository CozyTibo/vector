"""Canon pass run housekeeping (stuck RUNNING recovery)."""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.infrastructure.db.models.canon_pass_run import CanonPassRun

_LOGGER = logging.getLogger(__name__)

RUN_RUNNING = "RUNNING"
RUN_FAILED = "FAILED"
_STUCK_RUNNING_MIN_SECONDS = 600


def abandon_stuck_running_canon_passes(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    interval_seconds: int,
) -> int:
    """Mark abandoned RUNNING passes so schedulers and workers are not wedged forever."""
    grace_seconds = max(_STUCK_RUNNING_MIN_SECONDS, int(interval_seconds) * 2)
    cutoff = utc_now() - timedelta(seconds=grace_seconds)
    stuck = list(
        session.scalars(
            select(CanonPassRun).where(
                CanonPassRun.tenant_id == tenant_id,
                CanonPassRun.status == RUN_RUNNING,
                CanonPassRun.started_at < cutoff,
            ),
        ).all(),
    )
    if not stuck:
        return 0
    now = utc_now()
    for row in stuck:
        row.status = RUN_FAILED
        row.finished_at = now
        row.error_summary = "stale_running_pass_abandoned"
    session.flush()
    _LOGGER.warning(
        "abandoned %s stale RUNNING canon pass(es) for tenant %s",
        len(stuck),
        tenant_id,
    )
    return len(stuck)
