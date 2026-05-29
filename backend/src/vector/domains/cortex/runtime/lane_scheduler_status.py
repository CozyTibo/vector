"""Operator-facing scheduler tick + lane staleness for canon/identity."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.identity.scheduler_dedup import should_skip_scheduled_identity_pass
from vector.domains.cortex.ingestion.sync_shared import utc_now
from vector.domains.cortex.runtime.lane_scheduler_tick import latest_lane_scheduler_tick_v1
from vector.domains.cortex.runtime.pass_types import (
    ACTIVE_STATUSES,
    CANON_PASS,
    DECLARED_DOMAIN_PASS,
    GRAPH_PROJECTION_PASS,
    IDENTITY_PASS,
)
from vector.domains.cortex.runtime.plan import _tenant_canon_has_backlog
from vector.infrastructure.db.models.canon_pass_run import CanonPassRun
from vector.infrastructure.db.models.canon_scheduler_tick import CanonSchedulerTick
from vector.infrastructure.db.models.cortex_pass import CortexPass
from vector.infrastructure.db.models.identity_pass_run import IdentityPassRun
from vector.infrastructure.db.models.graph_pass_run import GraphPassRun
from vector.infrastructure.db.models.graph_scheduler_tick import GraphSchedulerTick
from vector.infrastructure.db.models.declared_domain_dirty_queue import DeclaredDomainDirtyQueue
from vector.infrastructure.db.models.declared_domain_pass_run import DeclaredDomainPassRun
from vector.infrastructure.db.models.identity_scheduler_tick import IdentitySchedulerTick
from vector.infrastructure.db.models.orchestrator_run import OrchestratorRun


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


def _orchestrator_last_run_payload(session: Session) -> dict[str, Any] | None:
    last = session.scalar(
        select(OrchestratorRun).order_by(OrchestratorRun.started_at.desc()).limit(1),
    )
    if last is None:
        return None
    return {
        "id": str(last.id),
        "started_at": last.started_at.isoformat(),
        "completed_at": last.completed_at.isoformat() if last.completed_at else None,
        "outcome": last.outcome,
        "passes_planned": last.passes_planned,
        "passes_processed": last.passes_processed,
        "error_summary": last.error_summary,
    }


def _orchestrator_healthy(session: Session, *, interval_seconds: int, multiplier: float = 2.5) -> bool:
    last = session.scalar(
        select(OrchestratorRun).order_by(OrchestratorRun.started_at.desc()).limit(1),
    )
    if last is None:
        return False
    threshold = utc_now() - timedelta(seconds=max(60, int(interval_seconds * multiplier)))
    if last.outcome == "running":
        return last.started_at >= threshold
    if last.outcome != "ok":
        return False
    finished = last.completed_at or last.started_at
    return finished >= threshold


def _has_active_pass(session: Session, *, tenant_id: uuid.UUID, pass_type: str) -> bool:
    active = int(
        session.scalar(
            select(func.count())
            .select_from(CortexPass)
            .where(
                CortexPass.tenant_id == tenant_id,
                CortexPass.pass_type == pass_type,
                CortexPass.status.in_(tuple(sorted(ACTIVE_STATUSES))),
            ),
        )
        or 0,
    )
    return active > 0


def _recent_completed_pass(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pass_run_model: type[Any],
    interval_seconds: int,
    multiplier: float = 2.5,
) -> bool:
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
        return False
    threshold = utc_now() - timedelta(seconds=max(60, int(interval_seconds * multiplier)))
    finished = latest_completed.finished_at or latest_completed.started_at
    return finished >= threshold


def _compute_lane_stale(
    session: Session,
    *,
    enabled: bool,
    tenant_id: uuid.UUID,
    pass_run_model: type[Any],
    pass_type: str,
    lane_interval_seconds: int,
    orchestrator_interval_seconds: int,
    tenant_needs_work: bool,
) -> bool:
    if not enabled:
        return False
    if not tenant_needs_work:
        return False
    if _has_active_pass(session, tenant_id=tenant_id, pass_type=pass_type):
        return False
    if _recent_completed_pass(
        session,
        tenant_id=tenant_id,
        pass_run_model=pass_run_model,
        interval_seconds=lane_interval_seconds,
    ):
        return False
    return not _orchestrator_healthy(
        session,
        interval_seconds=orchestrator_interval_seconds,
    )


def build_canon_lane_scheduler_status(
    session: Session,
    *,
    tenant_id: Any,
    enabled: bool,
    interval_seconds: int,
    orchestrator_interval_seconds: int,
) -> dict[str, Any]:
    tid = tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    last_tick = latest_lane_scheduler_tick_v1(session, CanonSchedulerTick)
    needs_work = _tenant_canon_has_backlog(session, tid)
    stale = _compute_lane_stale(
        session,
        enabled=enabled,
        tenant_id=tid,
        pass_run_model=CanonPassRun,
        pass_type=CANON_PASS,
        lane_interval_seconds=interval_seconds,
        orchestrator_interval_seconds=orchestrator_interval_seconds,
        tenant_needs_work=needs_work,
    )
    return {
        "runtime_model": "orchestrator",
        "enabled": enabled,
        "interval_seconds": interval_seconds,
        "orchestrator_interval_seconds": orchestrator_interval_seconds,
        "tenant_needs_work": needs_work,
        "last_tick": _tick_payload(last_tick),
        "last_orchestrator_run": _orchestrator_last_run_payload(session),
        "lane_stale": stale,
    }


def _tenant_graph_has_backlog(session: Session, tenant_id: uuid.UUID) -> bool:
    from vector.domains.cortex.graph.materialize import tenant_has_canon_backlog
    from vector.infrastructure.db.models.graph_dirty_queue import GraphDirtyQueue

    pending = session.scalar(
        select(GraphDirtyQueue.id)
        .where(
            GraphDirtyQueue.tenant_id == tenant_id,
            GraphDirtyQueue.processed_at.is_(None),
        )
        .limit(1),
    )
    if pending is None:
        return False
    return not tenant_has_canon_backlog(session, tenant_id)


def build_graph_lane_scheduler_status(
    session: Session,
    *,
    tenant_id: Any,
    enabled: bool,
    interval_seconds: int,
    orchestrator_interval_seconds: int,
) -> dict[str, Any]:
    from vector.domains.cortex.graph.scheduler_dedup import should_skip_scheduled_graph_pass

    tid = tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    last_tick = latest_lane_scheduler_tick_v1(session, GraphSchedulerTick)
    needs_work = _tenant_graph_has_backlog(session, tid)
    stale = _compute_lane_stale(
        session,
        enabled=enabled,
        tenant_id=tid,
        pass_run_model=GraphPassRun,
        pass_type=GRAPH_PROJECTION_PASS,
        lane_interval_seconds=interval_seconds,
        orchestrator_interval_seconds=orchestrator_interval_seconds,
        tenant_needs_work=needs_work,
    )
    return {
        "runtime_model": "orchestrator",
        "enabled": enabled,
        "interval_seconds": interval_seconds,
        "orchestrator_interval_seconds": orchestrator_interval_seconds,
        "tenant_needs_work": needs_work,
        "last_tick": _tick_payload(last_tick),
        "last_orchestrator_run": _orchestrator_last_run_payload(session),
        "lane_stale": stale,
        "scheduled_skip": should_skip_scheduled_graph_pass(
            session,
            tenant_id=tid,
            interval_seconds=interval_seconds,
        ),
    }


def build_identity_lane_scheduler_status(
    session: Session,
    *,
    tenant_id: Any,
    enabled: bool,
    interval_seconds: int,
    orchestrator_interval_seconds: int,
) -> dict[str, Any]:
    tid = tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    last_tick = latest_lane_scheduler_tick_v1(session, IdentitySchedulerTick)
    needs_work = not should_skip_scheduled_identity_pass(
        session,
        tenant_id=tid,
        interval_seconds=interval_seconds,
    )
    stale = _compute_lane_stale(
        session,
        enabled=enabled,
        tenant_id=tid,
        pass_run_model=IdentityPassRun,
        pass_type=IDENTITY_PASS,
        lane_interval_seconds=interval_seconds,
        orchestrator_interval_seconds=orchestrator_interval_seconds,
        tenant_needs_work=needs_work,
    )
    return {
        "runtime_model": "orchestrator",
        "enabled": enabled,
        "interval_seconds": interval_seconds,
        "orchestrator_interval_seconds": orchestrator_interval_seconds,
        "tenant_needs_work": needs_work,
        "last_tick": _tick_payload(last_tick),
        "last_orchestrator_run": _orchestrator_last_run_payload(session),
        "lane_stale": stale,
    }


def _tenant_declared_domain_has_backlog(session: Session, tenant_id: uuid.UUID) -> bool:
    dirty = int(
        session.scalar(
            select(func.count())
            .select_from(DeclaredDomainDirtyQueue)
            .where(
                DeclaredDomainDirtyQueue.tenant_id == tenant_id,
                DeclaredDomainDirtyQueue.processed_at.is_(None),
            ),
        )
        or 0,
    )
    return dirty > 0


def build_declared_domain_lane_scheduler_status(
    session: Session,
    *,
    tenant_id: Any,
    enabled: bool,
    interval_seconds: int,
    orchestrator_interval_seconds: int,
) -> dict[str, Any]:
    from vector.domains.cortex.declared_domains.scheduler_dedup import (
        should_skip_scheduled_declared_domain_pass,
    )

    tid = tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))
    needs_work = _tenant_declared_domain_has_backlog(session, tid)
    stale = _compute_lane_stale(
        session,
        enabled=enabled,
        tenant_id=tid,
        pass_run_model=DeclaredDomainPassRun,
        pass_type=DECLARED_DOMAIN_PASS,
        lane_interval_seconds=interval_seconds,
        orchestrator_interval_seconds=orchestrator_interval_seconds,
        tenant_needs_work=needs_work,
    )
    return {
        "runtime_model": "orchestrator",
        "enabled": enabled,
        "interval_seconds": interval_seconds,
        "orchestrator_interval_seconds": orchestrator_interval_seconds,
        "tenant_needs_work": needs_work,
        "last_tick": None,
        "last_orchestrator_run": _orchestrator_last_run_payload(session),
        "lane_stale": stale,
        "scheduled_skip": should_skip_scheduled_declared_domain_pass(
            session,
            tenant_id=tid,
            interval_seconds=interval_seconds,
        ),
    }
