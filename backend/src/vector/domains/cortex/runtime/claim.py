"""Claim pending passes for worker execution."""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.domains.cortex.runtime.pass_types import STATUS_PENDING, STATUS_RUNNING
from vector.infrastructure.db.models.cortex_pass import CortexPass


def claim_next_pass_v1(
    session: Session,
    *,
    worker_id: str,
    lease_ttl_seconds: int,
) -> CortexPass | None:
    """Claim one eligible pass (``FOR UPDATE SKIP LOCKED``)."""
    now = utc_now()
    row = session.scalar(
        select(CortexPass)
        .where(
            CortexPass.status == STATUS_PENDING,
            CortexPass.scheduled_at <= now,
        )
        .order_by(CortexPass.priority.desc(), CortexPass.scheduled_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True),
    )
    if row is None:
        return None
    row.status = STATUS_RUNNING
    row.started_at = now
    row.attempt_count = int(row.attempt_count) + 1
    row.locked_by = worker_id
    row.locked_until = now + timedelta(seconds=max(60, lease_ttl_seconds))
    session.flush()
    return row


def extend_pass_lease_v1(
    session: Session,
    pass_row: CortexPass,
    *,
    lease_ttl_seconds: int,
) -> None:
    pass_row.locked_until = utc_now() + timedelta(seconds=max(60, lease_ttl_seconds))
    session.flush()
