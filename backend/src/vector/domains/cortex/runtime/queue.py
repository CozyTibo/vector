"""Enqueue and inspect cortex_passes rows."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.domains.cortex.runtime.pass_types import (
    ACTIVE_STATUSES,
    STATUS_PENDING,
)
from vector.infrastructure.db.models.cortex_pass import CortexPass


def upsert_pending_pass_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pass_type: str,
    source_trigger: str,
    priority: int = 0,
    payload_json: dict[str, Any] | None = None,
    max_attempts: int = 5,
) -> uuid.UUID:
    """Insert or refresh a pending pass for (tenant, pass_type)."""
    existing = session.scalar(
        select(CortexPass)
        .where(
            CortexPass.tenant_id == tenant_id,
            CortexPass.pass_type == pass_type,
            CortexPass.status.in_(tuple(sorted(ACTIVE_STATUSES))),
        )
        .limit(1)
        .with_for_update(),
    )
    now = utc_now()
    if existing is not None:
        if existing.status == STATUS_PENDING:
            existing.source_trigger = source_trigger
            existing.priority = max(existing.priority, priority)
            existing.scheduled_at = now
            if payload_json is not None:
                existing.payload_json = payload_json
            session.flush()
            return existing.id
        return existing.id

    row = CortexPass(
        tenant_id=tenant_id,
        pass_type=pass_type,
        status=STATUS_PENDING,
        priority=priority,
        scheduled_at=now,
        source_trigger=source_trigger,
        payload_json=payload_json,
        max_attempts=max_attempts,
    )
    session.add(row)
    session.flush()
    return row.id


def count_passes_by_status_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID | None = None,
    pass_type: str | None = None,
) -> dict[str, int]:
    stmt = select(CortexPass.status, func.count()).group_by(CortexPass.status)
    if tenant_id is not None:
        stmt = stmt.where(CortexPass.tenant_id == tenant_id)
    if pass_type is not None:
        stmt = stmt.where(CortexPass.pass_type == pass_type)
    return {str(status): int(n) for status, n in session.execute(stmt).all()}


def list_passes_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID | None = None,
    status: str | None = None,
    pass_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    filters = []
    if tenant_id is not None:
        filters.append(CortexPass.tenant_id == tenant_id)
    if status is not None:
        filters.append(CortexPass.status == status)
    if pass_type is not None:
        filters.append(CortexPass.pass_type == pass_type)

    count_stmt = select(func.count()).select_from(CortexPass)
    list_stmt = select(CortexPass).order_by(CortexPass.scheduled_at.desc())
    for f in filters:
        count_stmt = count_stmt.where(f)
        list_stmt = list_stmt.where(f)
    total = int(session.scalar(count_stmt) or 0)
    rows = list(session.scalars(list_stmt.offset(offset).limit(limit)).all())
    items = [
        {
            "id": str(r.id),
            "tenant_id": str(r.tenant_id),
            "pass_type": r.pass_type,
            "status": r.status,
            "priority": r.priority,
            "scheduled_at": r.scheduled_at.isoformat(),
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "locked_by": r.locked_by,
            "locked_until": r.locked_until.isoformat() if r.locked_until else None,
            "attempt_count": r.attempt_count,
            "max_attempts": r.max_attempts,
            "source_trigger": r.source_trigger,
            "payload_json": r.payload_json,
            "error_summary": r.error_summary,
            "stats_json": r.stats_json,
        }
        for r in rows
    ]
    return items, total


def requeue_pass_v1(session: Session, pass_id: uuid.UUID) -> bool:
    row = session.get(CortexPass, pass_id)
    if row is None:
        return False
    row.status = STATUS_PENDING
    row.scheduled_at = utc_now()
    row.locked_by = None
    row.locked_until = None
    row.started_at = None
    row.finished_at = None
    row.error_summary = None
    session.flush()
    return True


def abandon_pass_v1(session: Session, pass_id: uuid.UUID) -> bool:
    from vector.domains.cortex.runtime.pass_types import STATUS_CANCELLED

    row = session.get(CortexPass, pass_id)
    if row is None:
        return False
    row.status = STATUS_CANCELLED
    row.finished_at = utc_now()
    row.locked_by = None
    row.locked_until = None
    row.error_summary = row.error_summary or "operator_abandoned"
    session.flush()
    return True


def recover_expired_leases_v1(session: Session, *, lease_ttl_seconds: int) -> int:
    from vector.domains.cortex.runtime.pass_types import STATUS_RUNNING

    _ = lease_ttl_seconds
    now = utc_now()
    expired = list(
        session.scalars(
            select(CortexPass).where(
                CortexPass.status == STATUS_RUNNING,
                CortexPass.locked_until.is_not(None),
                CortexPass.locked_until < now,
            ),
        ).all(),
    )
    if not expired:
        return 0
    for row in expired:
        row.status = STATUS_PENDING
        row.locked_by = None
        row.locked_until = None
        row.error_summary = "stale_lease_recovered"
        row.scheduled_at = now
    session.flush()
    return len(expired)
