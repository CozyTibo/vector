"""Operator-facing estimate of when the next scheduled ingestion sync may run."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.cortex_ingestion_policy import (
    SUPPORTED_CONNECTOR_IDS,
    should_route_ingestion_to_cortex,
)
from vector.domains.cortex.ingestion.checkpoint_contract import checkpoint_last_incremental_at
from vector.domains.cortex.ingestion.scheduler import SCOPE_DEFAULT
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.settings import Settings

ForecastStatus = Literal[
    "disabled",
    "paused",
    "no_connectors",
    "running",
    "eligible_now",
    "waiting_cooldown",
]


_SCHEDULED_SOURCE_TRIGGERS = ("scheduled", "scheduled_lane")


def _parse_checkpoint_iso(raw: str | None) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        s = raw.strip().replace("Z", "+00:00") if raw.endswith("Z") else raw
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    except ValueError:
        return None


def _estimate_next_scheduler_tick_at_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    beat_seconds: int,
    now: datetime,
) -> datetime:
    """Best-effort next Celery Beat tick from the latest scheduled ingestion run."""
    beat = max(60, int(beat_seconds))
    last = session.scalar(
        select(func.max(IngestionRun.started_at)).where(
            IngestionRun.tenant_id == tenant_id,
            IngestionRun.source_trigger.in_(_SCHEDULED_SOURCE_TRIGGERS),
        )
    )
    if last is None:
        return now + timedelta(seconds=beat)
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    else:
        last = last.astimezone(UTC)
    next_tick = last + timedelta(seconds=beat)
    while next_tick <= now:
        next_tick += timedelta(seconds=beat)
    return next_tick


def _connector_rows_for_tenant(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
) -> list[dict[str, Any]]:
    from vector.infrastructure.db.models.tenant_connection import TenantConnection

    stmt = (
        select(TenantConnection)
        .where(TenantConnection.tenant_id == tenant_id)
        .order_by(TenantConnection.provider.asc())
    )
    conns = list(session.scalars(stmt).all())
    by_provider: dict[str, TenantConnection] = {}
    for tc in conns:
        cur = by_provider.get(tc.provider)
        if cur is None or (tc.status == "active" and cur.status != "active"):
            by_provider[tc.provider] = tc

    rows: list[dict[str, Any]] = []
    for connector in sorted(SUPPORTED_CONNECTOR_IDS):
        conn_row: TenantConnection | None = by_provider.get(connector)
        routed = should_route_ingestion_to_cortex(settings, connector, tenant_id)
        ck_at: str | None = None
        if conn_row is not None:
            ck = session.scalar(
                select(ConnectorSyncState).where(
                    ConnectorSyncState.tenant_id == tenant_id,
                    ConnectorSyncState.connection_id == conn_row.id,
                    ConnectorSyncState.connector == connector,
                    ConnectorSyncState.scope_key == SCOPE_DEFAULT,
                )
            )
            if ck is not None:
                raw_ts = checkpoint_last_incremental_at(dict(ck.state))
                if isinstance(raw_ts, str) and raw_ts.strip():
                    ck_at = raw_ts.strip()
        rows.append(
            {
                "connector": connector,
                "connection_id": conn_row.id if conn_row else None,
                "connection_status": conn_row.status if conn_row else None,
                "cortex_routed": routed,
                "checkpoint_last_incremental_at": ck_at,
            }
        )
    return rows


def estimate_tenant_next_scheduled_ingestion_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    scheduler: dict[str, Any] | None = None,
    connector_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Best-effort next scheduled sync time for one tenant (beat + per-connector min gap)."""
    sched = scheduler or {}
    beat = max(0, int(sched.get("beat_interval_seconds") or settings.cortex_ingestion_scheduler_interval_seconds))
    min_gap = max(0, int(sched.get("min_gap_seconds") or settings.cortex_ingestion_min_gap_seconds))
    env_on = bool(
        sched.get("env_scheduler_enabled")
        if "env_scheduler_enabled" in sched
        else settings.cortex_ingestion_scheduler_enabled
    )
    paused = bool(sched.get("paused_via_redis"))

    if not env_on:
        return {
            "status": "disabled",
            "next_at": None,
            "summary": "Scheduled ingestion is off in this environment — use manual sync or Run from ingestion.",
            "beat_interval_seconds": beat,
            "min_gap_seconds": min_gap,
        }
    if paused:
        return {
            "status": "paused",
            "next_at": None,
            "summary": "Scheduler is paused — resume in Settings before expecting automatic ingestion.",
            "beat_interval_seconds": beat,
            "min_gap_seconds": min_gap,
        }

    rows = connector_rows if connector_rows is not None else _connector_rows_for_tenant(
        session, settings, tenant_id=tenant_id
    )
    routed_active = [
        r
        for r in rows
        if r.get("cortex_routed") and r.get("connection_status") == "active" and r.get("connection_id")
    ]
    if not routed_active:
        return {
            "status": "no_connectors",
            "next_at": None,
            "summary": "No active Cortex-routed connectors — connect and route a source first.",
            "beat_interval_seconds": beat,
            "min_gap_seconds": min_gap,
        }

    running = session.scalar(
        select(IngestionRun.id)
        .where(
            IngestionRun.tenant_id == tenant_id,
            IngestionRun.status == "RUNNING",
        )
        .limit(1)
    )
    if running is not None:
        return {
            "status": "running",
            "next_at": None,
            "summary": "An ingestion run is in progress — the next scheduled tick will respect min-gap after it finishes.",
            "beat_interval_seconds": beat,
            "min_gap_seconds": min_gap,
        }

    now = datetime.now(tz=UTC)
    gap_td = timedelta(seconds=min_gap)
    eligible_now: list[str] = []
    next_by_connector: list[tuple[str, datetime]] = []

    for row in routed_active:
        connector = str(row["connector"])
        last = _parse_checkpoint_iso(row.get("checkpoint_last_incremental_at"))
        if last is None or now - last >= gap_td:
            eligible_now.append(connector)
            continue
        at = last + gap_td
        next_by_connector.append((connector, at))

    if eligible_now:
        next_tick = _estimate_next_scheduler_tick_at_v1(
            session,
            tenant_id=tenant_id,
            beat_seconds=beat,
            now=now,
        )
        summary = (
            f"Eligible now ({', '.join(eligible_now)}). "
            f"Beat enqueues scheduled syncs every {beat}s — next tick at the time shown."
        )
        return {
            "status": "eligible_now",
            "next_at": next_tick,
            "summary": summary,
            "beat_interval_seconds": beat,
            "min_gap_seconds": min_gap,
            "connectors_eligible_now": eligible_now,
        }

    assert next_by_connector
    next_by_connector.sort(key=lambda x: x[1])
    next_connector, eligibility_at = next_by_connector[0]
    next_tick = _estimate_next_scheduler_tick_at_v1(
        session,
        tenant_id=tenant_id,
        beat_seconds=beat,
        now=now,
    )
    next_at = max(eligibility_at, next_tick)
    summary = (
        f"{next_connector} becomes eligible at the time shown "
        f"(min gap {min_gap}s). Scheduled enqueue happens on the next Beat tick after that."
    )
    return {
        "status": "waiting_cooldown",
        "next_at": next_at,
        "summary": summary,
        "beat_interval_seconds": beat,
        "min_gap_seconds": min_gap,
        "next_connector": next_connector,
    }
