"""Operator history for Cortex ingestion-only Beat ticks (per tenant)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.ingestion_scheduler_tick import IngestionSchedulerTick
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

_SCHEDULED_TRIGGERS = frozenset({"scheduled", "scheduled_lane"})


def _resource_breakdown_for_run(session: Session, run_id: uuid.UUID) -> list[dict[str, Any]]:
    stmt = (
        select(RawIngestionRecord.resource_type, func.count().label("n"))
        .where(RawIngestionRecord.run_id == run_id)
        .group_by(RawIngestionRecord.resource_type)
        .order_by(func.count().desc())
    )
    return [
        {"resource_type": str(rt), "count": int(n)}
        for rt, n in session.execute(stmt).all()
    ]


def _runs_for_tenant_tick(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    tick_id: uuid.UUID,
) -> list[IngestionRun]:
    tick_key = str(tick_id)
    stmt = (
        select(IngestionRun)
        .where(
            IngestionRun.tenant_id == tenant_id,
            IngestionRun.source_trigger.in_(tuple(sorted(_SCHEDULED_TRIGGERS))),
        )
        .order_by(IngestionRun.connector.asc(), IngestionRun.started_at.asc())
    )
    return [
        r
        for r in session.scalars(stmt).all()
        if isinstance(r.stats, dict) and str(r.stats.get("scheduler_tick_id") or "") == tick_key
    ]


def _tenant_jobs_from_tick(tick: IngestionSchedulerTick, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    jobs = tick.enqueued_jobs if isinstance(tick.enqueued_jobs, list) else []
    tid = str(tenant_id)
    return [j for j in jobs if isinstance(j, dict) and str(j.get("tenant_id")) == tid]


def build_tenant_scheduler_beat_history_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int = 20,
) -> dict[str, Any]:
    """Recent ingestion Beat ticks that enqueued or ran work for this tenant."""
    limit = max(1, min(limit, 20))
    ticks = list(
        session.scalars(
            select(IngestionSchedulerTick)
            .order_by(IngestionSchedulerTick.started_at.desc())
            .limit(limit * 3)
        ).all()
    )

    items: list[dict[str, Any]] = []
    for tick in ticks:
        tenant_jobs = _tenant_jobs_from_tick(tick, tenant_id)
        runs = _runs_for_tenant_tick(session, tenant_id=tenant_id, tick_id=tick.id)
        if not tenant_jobs and not runs:
            continue

        run_by_connector: dict[str, IngestionRun] = {}
        for run in runs:
            run_by_connector[run.connector] = run

        connectors_seen: set[str] = set()
        connector_rows: list[dict[str, Any]] = []

        for job in tenant_jobs:
            connector = str(job.get("connector_id") or "")
            if not connector or connector in connectors_seen:
                continue
            connectors_seen.add(connector)
            connector_rows.append(
                _connector_debrief_row(
                    session,
                    connector=connector,
                    run=run_by_connector.get(connector),
                    enqueued=True,
                )
            )

        for connector, run in sorted(run_by_connector.items()):
            if connector in connectors_seen:
                continue
            connectors_seen.add(connector)
            connector_rows.append(
                _connector_debrief_row(session, connector=connector, run=run, enqueued=False)
            )

        items.append(
            {
                "tick_id": tick.id,
                "started_at": tick.started_at,
                "completed_at": tick.completed_at,
                "outcome": tick.outcome,
                "beat_interval_seconds": tick.beat_interval_seconds,
                "skip_reason": tick.skip_reason,
                "global_enqueued_count": tick.enqueued_count,
                "global_candidate_count": tick.candidate_count,
                "tenant_enqueued_count": len(tenant_jobs),
                "connectors": connector_rows,
            }
        )
        if len(items) >= limit:
            break

    return {
        "tenant_id": tenant_id,
        "items": items,
        "limit": limit,
    }


def _connector_debrief_row(
    session: Session,
    *,
    connector: str,
    run: IngestionRun | None,
    enqueued: bool,
) -> dict[str, Any]:
    if run is None:
        return {
            "connector": connector,
            "enqueued": enqueued,
            "run_id": None,
            "status": "pending",
            "records_written": None,
            "resource_breakdown": [],
            "error_summary": None,
            "started_at": None,
            "finished_at": None,
        }

    stats = run.stats if isinstance(run.stats, dict) else {}
    raw_n = stats.get("records_written")
    records_written = int(raw_n) if isinstance(raw_n, int) else None

    return {
        "connector": connector,
        "enqueued": enqueued,
        "run_id": run.id,
        "status": run.status,
        "records_written": records_written,
        "resource_breakdown": _resource_breakdown_for_run(session, run.id),
        "error_summary": run.error_summary,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }


def complete_scheduler_tick_v1(
    session: Session,
    tick_id: uuid.UUID,
    *,
    outcome: str,
    enqueued_count: int,
    candidate_count: int,
    skip_reason: str | None = None,
    enqueued_jobs: list[dict[str, Any]] | None = None,
) -> None:
    tick = session.get(IngestionSchedulerTick, tick_id)
    if tick is None:
        return
    tick.completed_at = datetime.now(tz=UTC)
    tick.outcome = outcome
    tick.enqueued_count = enqueued_count
    tick.candidate_count = candidate_count
    tick.skip_reason = skip_reason
    tick.enqueued_jobs = enqueued_jobs
