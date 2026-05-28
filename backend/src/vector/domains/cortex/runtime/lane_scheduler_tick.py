"""Shared helpers for canon/identity Beat tick audit rows."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy.orm import Session


class _LaneTickRow(Protocol):
    id: uuid.UUID
    completed_at: datetime | None
    outcome: str
    enqueued_count: int
    candidate_count: int
    skipped_count: int
    skip_reason: str | None
    enqueued_tenant_ids: list[str] | None


def complete_lane_scheduler_tick_v1(
    session: Session,
    tick: _LaneTickRow,
    *,
    outcome: str,
    enqueued_count: int,
    candidate_count: int,
    skipped_count: int = 0,
    skip_reason: str | None = None,
    enqueued_tenant_ids: list[str] | None = None,
) -> None:
    tick.completed_at = datetime.now(tz=UTC)
    tick.outcome = outcome
    tick.enqueued_count = enqueued_count
    tick.candidate_count = candidate_count
    tick.skipped_count = skipped_count
    tick.skip_reason = skip_reason
    tick.enqueued_tenant_ids = enqueued_tenant_ids


def latest_lane_scheduler_tick_v1(session: Session, model: type[Any]) -> Any | None:
    from sqlalchemy import select

    return session.scalar(select(model).order_by(model.started_at.desc()).limit(1))
