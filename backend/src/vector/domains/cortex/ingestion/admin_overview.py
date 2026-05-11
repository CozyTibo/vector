"""Phase 01 Step 6 — operator-facing ingestion summary for the internal admin UI."""

from __future__ import annotations

import copy
import logging
import threading
import time
import uuid
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.cortex_ingestion_policy import (
    SUPPORTED_CONNECTOR_IDS,
    should_route_ingestion_to_cortex,
)
from vector.domains.cortex.ingestion.checkpoint_contract import checkpoint_last_incremental_at
from vector.domains.cortex.ingestion.sync_context import SCOPE_DEFAULT
from vector.infrastructure.cortex_scheduler_pause import read_scheduler_paused_flag
from vector.infrastructure.db.models.connector_sync_state import ConnectorSyncState
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.settings import Settings

_LOGGER = logging.getLogger("app")
_OVERVIEW_CACHE_TTL_SECONDS = 8.0
_OVERVIEW_CACHE_LOCK = threading.Lock()
_OVERVIEW_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _operator_scheduler_label(
    *,
    env_enabled: bool,
    paused_redis: bool,
) -> Literal["Active", "Off (env)", "Paused (operator)", "Off (env) + paused (operator)"]:
    if not env_enabled and paused_redis:
        return "Off (env) + paused (operator)"
    if not env_enabled:
        return "Off (env)"
    if paused_redis:
        return "Paused (operator)"
    return "Active"


def _pick_connection_per_provider(conns: list[TenantConnection]) -> dict[str, TenantConnection]:
    by_p: dict[str, TenantConnection] = {}
    for tc in sorted(conns, key=lambda c: (c.provider, c.created_at), reverse=True):
        if tc.provider not in SUPPORTED_CONNECTOR_IDS:
            continue
        cur = by_p.get(tc.provider)
        if cur is None:
            by_p[tc.provider] = tc
            continue
        if tc.status == "active" and cur.status != "active":
            by_p[tc.provider] = tc
    return by_p


def _latest_runs_by_connection(
    session: Session,
    tenant_id: uuid.UUID,
) -> dict[tuple[uuid.UUID, str], IngestionRun]:
    stmt = (
        select(IngestionRun)
        .where(IngestionRun.tenant_id == tenant_id)
        .order_by(IngestionRun.started_at.desc())
        .limit(200)
    )
    runs = list(session.scalars(stmt).all())
    out: dict[tuple[uuid.UUID, str], IngestionRun] = {}
    for run in runs:
        key = (run.connection_id, run.connector)
        if key not in out:
            out[key] = run
    return out


def _checkpoint_row(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    connector: str,
) -> ConnectorSyncState | None:
    stmt = select(ConnectorSyncState).where(
        ConnectorSyncState.tenant_id == tenant_id,
        ConnectorSyncState.connection_id == connection_id,
        ConnectorSyncState.connector == connector,
        ConnectorSyncState.scope_key == SCOPE_DEFAULT,
    )
    return session.scalar(stmt)


def _run_summary_dict(run: IngestionRun) -> dict[str, Any]:
    stats = run.stats if isinstance(run.stats, dict) else None
    raw_n: int | None = None
    if stats is not None:
        raw = stats.get("records_written")
        if isinstance(raw, int):
            raw_n = raw
    return {
        "run_id": run.id,
        "status": run.status,
        "replay_mode": run.replay_mode,
        "sync_mode": run.sync_mode,
        "source_trigger": run.source_trigger,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "error_summary": run.error_summary,
        "raw_rows_written": raw_n,
    }


def _collect_worker_telemetry(settings: Settings) -> dict[str, Any]:
    if not settings.redis_url.strip():
        return {
            "status": "unavailable",
            "worker_count": 0,
            "live_queue_workers": 0,
            "replay_queue_workers": 0,
            "worker_names": [],
            "detail": "REDIS_URL not configured; Celery inspect unavailable.",
        }
    try:
        from app.celery_app import celery_app

        inspect = celery_app.control.inspect(timeout=1.5)
        if inspect is None:
            return {
                "status": "error",
                "worker_count": 0,
                "live_queue_workers": 0,
                "replay_queue_workers": 0,
                "worker_names": [],
                "detail": "Celery inspect handle unavailable.",
            }
        ping = inspect.ping() or {}
        active_queues = inspect.active_queues() or {}
        worker_names = sorted(ping.keys())
        if not worker_names:
            return {
                "status": "no_workers",
                "worker_count": 0,
                "live_queue_workers": 0,
                "replay_queue_workers": 0,
                "worker_names": [],
                "detail": "No workers responded to Celery ping.",
            }

        live_queue_workers = 0
        replay_queue_workers = 0
        for worker in worker_names:
            raw_queues = active_queues.get(worker)
            queues = raw_queues if isinstance(raw_queues, list) else []
            queue_names = {
                q.get("name")
                for q in queues
                if isinstance(q, dict) and isinstance(q.get("name"), str)
            }
            if "cortex_live" in queue_names:
                live_queue_workers += 1
            if "cortex_replay" in queue_names:
                replay_queue_workers += 1
        return {
            "status": "ok",
            "worker_count": len(worker_names),
            "live_queue_workers": live_queue_workers,
            "replay_queue_workers": replay_queue_workers,
            "worker_names": worker_names,
            "detail": None,
        }
    except Exception as exc:
        _LOGGER.warning("cortex worker telemetry inspect failed", exc_info=True)
        return {
            "status": "error",
            "worker_count": 0,
            "live_queue_workers": 0,
            "replay_queue_workers": 0,
            "worker_names": [],
            "detail": str(exc),
        }


def _collect_duplicate_prevention_metric(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    live_rows_examined = int(
        session.scalar(
            select(func.count())
            .select_from(RawIngestionRecord)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id.is_(None),
            )
        )
        or 0
    )
    if live_rows_examined == 0:
        return {
            "status": "unavailable",
            "ratio_percent": None,
            "live_rows_examined": 0,
            "duplicate_groups": 0,
            "duplicate_rows_excess": 0,
            "detail": "No live rows yet.",
        }

    dup_groups = list(
        session.execute(
            select(func.count().label("n"))
            .select_from(RawIngestionRecord)
            .where(
                RawIngestionRecord.tenant_id == tenant_id,
                RawIngestionRecord.replay_job_id.is_(None),
            )
            .group_by(
                RawIngestionRecord.connection_id,
                RawIngestionRecord.connector,
                RawIngestionRecord.resource_type,
                RawIngestionRecord.source_identity_key,
                RawIngestionRecord.source_revision_key,
            )
            .having(func.count() > 1)
        ).all()
    )
    duplicate_groups = len(dup_groups)
    duplicate_rows_excess = sum(max(0, int(n) - 1) for (n,) in dup_groups)
    unique_rows = max(0, live_rows_examined - duplicate_rows_excess)
    ratio_percent = round((unique_rows / live_rows_examined) * 100.0, 2)
    return {
        "status": "ok" if duplicate_rows_excess == 0 else "warn",
        "ratio_percent": ratio_percent,
        "live_rows_examined": live_rows_examined,
        "duplicate_groups": duplicate_groups,
        "duplicate_rows_excess": duplicate_rows_excess,
        "detail": (
            "No duplicate live logical revisions detected."
            if duplicate_rows_excess == 0
            else "Duplicate live logical revisions detected; investigate concurrent/legacy writes."
        ),
    }


def build_cortex_ingestion_admin_overview(
    session: Session,
    settings: Settings,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Assemble visibility payload for :class:`AdminCortexIngestionOverviewResponse`."""
    cache_key = str(tenant_id)
    now = time.monotonic()
    with _OVERVIEW_CACHE_LOCK:
        cached = _OVERVIEW_CACHE.get(cache_key)
        if cached is not None:
            ts, payload = cached
            if now - ts <= _OVERVIEW_CACHE_TTL_SECONDS:
                return copy.deepcopy(payload)

    tenant = session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("tenant not found")

    stmt = (
        select(TenantConnection)
        .where(TenantConnection.tenant_id == tenant_id)
        .order_by(TenantConnection.provider.asc(), TenantConnection.created_at.desc())
    )
    conns = list(session.scalars(stmt).all())
    by_provider = _pick_connection_per_provider(conns)
    latest_runs = _latest_runs_by_connection(session, tenant_id)

    paused_redis = read_scheduler_paused_flag(settings)
    redis_ok = bool(settings.redis_url.strip())
    env_on = settings.cortex_ingestion_scheduler_enabled

    connector_rows: list[dict[str, Any]] = []
    for connector in sorted(SUPPORTED_CONNECTOR_IDS):
        tc = by_provider.get(connector)
        routed = should_route_ingestion_to_cortex(settings, connector, tenant_id)
        latest = None
        ck_at: str | None = None
        if tc is not None:
            latest = latest_runs.get((tc.id, connector))
            ck = _checkpoint_row(
                session,
                tenant_id=tenant_id,
                connection_id=tc.id,
                connector=connector,
            )
            if ck is not None:
                raw_ts = checkpoint_last_incremental_at(dict(ck.state))
                if isinstance(raw_ts, str) and raw_ts.strip():
                    ck_at = raw_ts.strip()
        connector_rows.append(
            {
                "connector": connector,
                "connection_id": tc.id if tc else None,
                "connection_status": tc.status if tc else None,
                "cortex_routed": routed,
                "queue_lane_live": "cortex_live",
                "queue_lane_replay": "cortex_replay",
                "checkpoint_last_incremental_at": ck_at,
                "latest_run": _run_summary_dict(latest) if latest else None,
            },
        )

    routed_any = any(row["cortex_routed"] for row in connector_rows)
    has_active_conn = any(
        row["connection_id"] and row["connection_status"] == "active" for row in connector_rows
    )
    failed_recent = any(
        (row["latest_run"] or {}).get("status") == "FAILED"
        for row in connector_rows
        if row["latest_run"]
    )

    if not has_active_conn:
        bottleneck = "No active OAuth connections — connect integrations first."
    elif not routed_any:
        bottleneck = (
            "Connections exist but Cortex ingestion is turned off for every connector "
            "for this workspace (configuration or tenant allowlists)."
        )
    elif failed_recent:
        bottleneck = "A recent ingestion run failed — inspect error summaries and logs."
    elif env_on and not paused_redis:
        bottleneck = (
            "Scheduler is eligible to enqueue work when min-gap allows; "
            "watch run history for stalls."
        )
    else:
        bottleneck = (
            "Scheduled Beat enqueue is off or paused; manual sync remains available when routed."
        )

    digest = {
        "objective": (
            "Safely pull connector data into Cortex raw ingestion with checkpoints "
            "and replay isolation."
        ),
        "bottleneck_hint": bottleneck,
        "confidence_note": (
            "Use the verification checklist after changes; replay jobs use the "
            "cortex_replay lane only."
        ),
        "recommended_actions": [
            "Review declared organizational exhaust: GET …/cortex/ingestion/exhaust-coverage "
            "(also surfaced on the Cortex ingestion admin tab) — matrix-backed, not implied by checkpoints alone.",
            "Run the verification checklist after rollout or incident response.",
            "Use manual sync for one connector at a time; expect cortex_live queue load.",
            (
                "Use replay only with an explicit job id; expect cortex_replay lane "
                "and isolated checkpoints."
            ),
        ],
    }

    global_scheduler = {
        "env_scheduler_enabled": env_on,
        "beat_interval_seconds": settings.cortex_ingestion_scheduler_interval_seconds,
        "min_gap_seconds": settings.cortex_ingestion_min_gap_seconds,
        "verify_after_sync": settings.cortex_ingestion_verify_after_sync,
        "redis_url_configured": redis_ok,
        "paused_via_redis": paused_redis,
        "operator_mode_label": _operator_scheduler_label(
            env_enabled=env_on,
            paused_redis=paused_redis,
        ),
    }
    worker_telemetry = _collect_worker_telemetry(settings)
    duplicate_prevention = _collect_duplicate_prevention_metric(session, tenant_id)

    out = {
        "tenant_id": tenant_id,
        "company_name": tenant.company_name,
        "global_scheduler": global_scheduler,
        "worker_telemetry": worker_telemetry,
        "duplicate_prevention": duplicate_prevention,
        "digest": digest,
        "connectors": connector_rows,
    }
    with _OVERVIEW_CACHE_LOCK:
        _OVERVIEW_CACHE[cache_key] = (time.monotonic(), copy.deepcopy(out))
    return out
