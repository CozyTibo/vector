"""Operator-facing scheduler tick + lane staleness for canon/identity."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.domains.cortex.runtime.lane_scheduler_tick import latest_lane_scheduler_tick_v1
from vector.infrastructure.db.models.canon_pass_run import CanonPassRun
from vector.infrastructure.db.models.canon_scheduler_tick import CanonSchedulerTick
from vector.infrastructure.db.models.identity_pass_run import IdentityPassRun
from vector.infrastructure.db.models.identity_scheduler_tick import IdentitySchedulerTick


def _tick_payload(tick: Any | None) -> dict[str, Any] | None:
    if tick is None:
        return None
    return {
        "tick_id": str(tick.id),
        "started_at": tick.started_at.isoformat(),
        "completed_at": tick.completed_at.isoformat() if tick.completed_at else None,
        "outcome": tick.outcome,
        "enqueued_count": tick.enqueued_count,
        "candidate_count": tick.candidate_count,
        "skipped_count": tick.skipped_count,
        "beat_interval_seconds": tick.beat_interval_seconds,
        "skip_reason": tick.skip_reason,
    }


def _lane_stale(
    session: Session,
    *,
    tenant_id: Any,
    pass_run_model: type[Any],
    interval_seconds: int,
    multiplier: float = 2.5,
) -> bool:
    from sqlalchemy import select

    latest_completed = session.scalar(
        select(pass_run_model)
        .where(
            pass_run_model.tenant_id == tenant_id,
            pass_run_model.status.in_(("COMPLETED", "completed")),
        )
        .order_by(pass_run_model.started_at.desc())
        .limit(1),
    )
    if latest_completed is None:
        return True
    threshold = utc_now() - timedelta(seconds=max(60, int(interval_seconds * multiplier)))
    finished = latest_completed.finished_at or latest_completed.started_at
    return finished < threshold


def build_canon_lane_scheduler_status(
    session: Session,
    *,
    tenant_id: Any,
    enabled: bool,
    interval_seconds: int,
) -> dict[str, Any]:
    last_tick = latest_lane_scheduler_tick_v1(session, CanonSchedulerTick)
    stale = enabled and _lane_stale(
        session,
        tenant_id=tenant_id,
        pass_run_model=CanonPassRun,
        interval_seconds=interval_seconds,
    )
    return {
        "enabled": enabled,
        "interval_seconds": interval_seconds,
        "last_tick": _tick_payload(last_tick),
        "lane_stale": stale,
    }


def build_identity_lane_scheduler_status(
    session: Session,
    *,
    tenant_id: Any,
    enabled: bool,
    interval_seconds: int,
) -> dict[str, Any]:
    last_tick = latest_lane_scheduler_tick_v1(session, IdentitySchedulerTick)
    stale = enabled and _lane_stale(
        session,
        tenant_id=tenant_id,
        pass_run_model=IdentityPassRun,
        interval_seconds=interval_seconds,
    )
    return {
        "enabled": enabled,
        "interval_seconds": interval_seconds,
        "last_tick": _tick_payload(last_tick),
        "lane_stale": stale,
    }
