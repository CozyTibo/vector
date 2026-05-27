"""Phase 01 admin — recent runs and raw row previews for operator visualization."""

from __future__ import annotations

import copy
import threading
import time
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord

_RAW_STATS_CACHE_TTL_SECONDS = 8.0
_RAW_STATS_CACHE_LOCK = threading.Lock()
_RAW_STATS_CACHE: dict[tuple[Any, ...], tuple[float, list[dict[str, Any]]]] = {}
_RECENT_RUNS_CACHE_TTL_SECONDS = 8.0
_RECENT_RUNS_CACHE_LOCK = threading.Lock()
_RecentRunsCacheKey = tuple[str, int, int, str | None]
_RECENT_RUNS_CACHE: dict[_RecentRunsCacheKey, tuple[float, tuple[list[dict[str, Any]], int]]] = {}


def invalidate_recent_ingestion_runs_cache_v1(tenant_id: uuid.UUID) -> None:
    """Clear cached recent-run lists for a tenant (any limit)."""
    prefix = str(tenant_id)
    with _RECENT_RUNS_CACHE_LOCK:
        stale = [k for k in _RECENT_RUNS_CACHE if k[0] == prefix]
        for k in stale:
            _RECENT_RUNS_CACHE.pop(k, None)


def _dt_key(v: datetime | None) -> str | None:
    return v.isoformat() if v is not None else None


def slack_user_email_presence_v1(session: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    """Admin read: % of ``slack.user`` rows with a non-empty email in stored payload."""
    stmt = (
        select(RawIngestionRecord.payload_body)
        .where(
            RawIngestionRecord.tenant_id == tenant_id,
            RawIngestionRecord.connector == "slack",
            RawIngestionRecord.resource_type == "slack.user",
        )
        .limit(5000)
    )
    rows = session.scalars(stmt).all()
    total = 0
    with_email = 0
    for body in rows:
        if not isinstance(body, dict):
            continue
        total += 1
        member = body.get("member")
        if not isinstance(member, dict):
            continue
        profile = member.get("profile")
        email = None
        if isinstance(profile, dict):
            email = profile.get("email")
        if email is None:
            email = member.get("email")
        if isinstance(email, str) and email.strip():
            with_email += 1
    rate = round(100.0 * with_email / total, 1) if total else None
    return {
        "sampled_rows": total,
        "with_email": with_email,
        "email_presence_pct": rate,
        "capped_sample": total >= 5000,
    }


def aggregate_raw_ingestion_stats(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    connector: str | None = None,
    resource_type: str | None = None,
    fetched_after: datetime | None = None,
    fetched_before: datetime | None = None,
    include_health_rows: bool = False,
) -> list[dict[str, Any]]:
    """Per (connector, resource_type) counts and fetched_at bounds (observed raw store)."""
    cache_key = (
        str(tenant_id),
        connector.strip() if connector else None,
        resource_type.strip() if resource_type else None,
        _dt_key(fetched_after),
        _dt_key(fetched_before),
        bool(include_health_rows),
    )
    now = time.monotonic()
    with _RAW_STATS_CACHE_LOCK:
        cached = _RAW_STATS_CACHE.get(cache_key)
        if cached is not None:
            ts, payload = cached
            if now - ts <= _RAW_STATS_CACHE_TTL_SECONDS:
                return copy.deepcopy(payload)

    filters = [RawIngestionRecord.tenant_id == tenant_id]
    if connector and connector.strip():
        filters.append(RawIngestionRecord.connector == connector.strip())
    if resource_type and resource_type.strip():
        filters.append(RawIngestionRecord.resource_type == resource_type.strip())
    if fetched_after is not None:
        filters.append(RawIngestionRecord.fetched_at >= fetched_after)
    if fetched_before is not None:
        filters.append(RawIngestionRecord.fetched_at <= fetched_before)
    if not include_health_rows:
        filters.extend(
            [
                RawIngestionRecord.resource_type.not_like("%.scope_ping"),
                RawIngestionRecord.resource_type != "scope_ping",
                RawIngestionRecord.resource_type != "linear.viewer_ping",
                RawIngestionRecord.resource_type != "viewer_ping",
            ],
        )

    stmt = (
        select(
            RawIngestionRecord.connector,
            RawIngestionRecord.resource_type,
            func.count().label("row_count"),
            func.min(RawIngestionRecord.fetched_at).label("oldest_fetched_at"),
            func.max(RawIngestionRecord.fetched_at).label("newest_fetched_at"),
        )
        .where(*filters)
        .group_by(RawIngestionRecord.connector, RawIngestionRecord.resource_type)
        .order_by(RawIngestionRecord.connector.asc(), RawIngestionRecord.resource_type.asc())
    )
    rows = session.execute(stmt).all()
    out: list[dict[str, Any]] = []
    for connector, resource_type, row_count, oldest, newest in rows:
        out.append(
            {
                "connector": connector,
                "resource_type": resource_type,
                "row_count": int(row_count),
                "oldest_fetched_at": oldest,
                "newest_fetched_at": newest,
            },
        )
    with _RAW_STATS_CACHE_LOCK:
        _RAW_STATS_CACHE[cache_key] = (time.monotonic(), copy.deepcopy(out))
    return out


def list_recent_ingestion_runs(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    limit: int = 30,
    offset: int = 0,
    connector: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    cache_key = (str(tenant_id), int(limit), int(offset), (connector or "").strip() or None)
    now = time.monotonic()
    with _RECENT_RUNS_CACHE_LOCK:
        cached = _RECENT_RUNS_CACHE.get(cache_key)
        if cached is not None:
            ts, payload = cached
            if now - ts <= _RECENT_RUNS_CACHE_TTL_SECONDS:
                items, total = payload
                return copy.deepcopy(items), int(total)

    filters = [IngestionRun.tenant_id == tenant_id]
    conn = (connector or "").strip()
    if conn:
        filters.append(IngestionRun.connector == conn)
    total_count = int(session.scalar(select(func.count()).select_from(IngestionRun).where(*filters)) or 0)
    stmt = (
        select(IngestionRun)
        .where(*filters)
        .order_by(IngestionRun.started_at.desc())
        .offset(max(0, int(offset)))
        .limit(limit)
    )
    runs = list(session.scalars(stmt).all())
    out: list[dict[str, Any]] = []
    for run in runs:
        stats = run.stats if isinstance(run.stats, dict) else None
        raw_n: int | None = None
        if stats is not None:
            w = stats.get("records_written")
            if isinstance(w, int):
                raw_n = w
        out.append(
            {
                "run_id": run.id,
                "connection_id": run.connection_id,
                "connector": run.connector,
                "status": run.status,
                "source_trigger": run.source_trigger,
                "sync_mode": run.sync_mode,
                "replay_mode": run.replay_mode,
                "replay_job_id": run.replay_job_id,
                "replay_version": run.replay_version,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "error_summary": run.error_summary,
                "raw_rows_written": raw_n,
            },
        )
    with _RECENT_RUNS_CACHE_LOCK:
        _RECENT_RUNS_CACHE[cache_key] = (time.monotonic(), (copy.deepcopy(out), total_count))
    return out, total_count


def build_connector_raw_rollups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fold per-resource stats into per-connector rollups (from ``aggregate_raw_ingestion_stats``)."""
    by: dict[str, dict[str, Any]] = {}
    for r in rows:
        c = str(r["connector"])
        if c not in by:
            by[c] = {
                "connector": c,
                "row_count": 0,
                "oldest_fetched_at": r.get("oldest_fetched_at"),
                "newest_fetched_at": r.get("newest_fetched_at"),
                "resource_types": [],
            }
        b = by[c]
        b["row_count"] += int(r["row_count"])
        o = r.get("oldest_fetched_at")
        n = r.get("newest_fetched_at")
        if o is not None and (b["oldest_fetched_at"] is None or o < b["oldest_fetched_at"]):
            b["oldest_fetched_at"] = o
        if n is not None and (b["newest_fetched_at"] is None or n > b["newest_fetched_at"]):
            b["newest_fetched_at"] = n
        b["resource_types"].append(
            {"resource_type": r["resource_type"], "row_count": int(r["row_count"])},
        )
    for b in by.values():
        b["resource_types"].sort(key=lambda x: -x["row_count"])
    return sorted(by.values(), key=lambda x: x["connector"])


def list_raw_records_for_connector(
    session: Session,
    tenant_id: uuid.UUID,
    connector: str,
    *,
    limit: int = 50,
    offset: int = 0,
    resource_type: str | None = None,
    fetched_after: datetime | None = None,
    fetched_before: datetime | None = None,
    search_query: str | None = None,
    include_health_rows: bool = False,
) -> tuple[list[dict[str, Any]], bool, int]:
    """All raw rows for a tenant + connector (newest ids first), paginated."""
    c = connector.strip()
    filters = [RawIngestionRecord.tenant_id == tenant_id, RawIngestionRecord.connector == c]
    if resource_type and resource_type.strip():
        filters.append(RawIngestionRecord.resource_type == resource_type.strip())
    if fetched_after is not None:
        filters.append(RawIngestionRecord.fetched_at >= fetched_after)
    if fetched_before is not None:
        filters.append(RawIngestionRecord.fetched_at <= fetched_before)
    if not include_health_rows:
        filters.extend(
            [
                RawIngestionRecord.resource_type.not_like("%.scope_ping"),
                RawIngestionRecord.resource_type != "scope_ping",
                RawIngestionRecord.resource_type != "linear.viewer_ping",
                RawIngestionRecord.resource_type != "viewer_ping",
            ],
        )
    if search_query and search_query.strip():
        q = f"%{search_query.strip()}%"
        filters.append(
            or_(
                RawIngestionRecord.external_id.ilike(q),
                RawIngestionRecord.api_endpoint.ilike(q),
                RawIngestionRecord.resource_type.ilike(q),
                cast(RawIngestionRecord.payload_body, String).ilike(q),
                cast(RawIngestionRecord.query_params, String).ilike(q),
                RawIngestionRecord.idempotency_key.ilike(q),
                RawIngestionRecord.source_identity_key.ilike(q),
                RawIngestionRecord.source_revision_key.ilike(q),
            ),
        )
    total = int(
        session.scalar(select(func.count()).select_from(RawIngestionRecord).where(*filters)) or 0,
    )
    stmt = (
        select(RawIngestionRecord)
        .where(*filters)
        .order_by(RawIngestionRecord.id.desc())
        .offset(offset)
        .limit(limit + 1)
    )
    rows = list(session.scalars(stmt).all())
    truncated = len(rows) > limit
    if truncated:
        rows = rows[:limit]
    items: list[dict[str, Any]] = []
    for r in rows:
        qp = dict(r.query_params) if isinstance(r.query_params, dict) else {}
        body = dict(r.payload_body) if isinstance(r.payload_body, dict) else {}
        items.append(
            {
                "id": r.id,
                "run_id": r.run_id,
                "resource_type": r.resource_type,
                "external_id": r.external_id,
                "api_endpoint": r.api_endpoint,
                "query_params": qp,
                "payload_body": body,
                "http_status": r.http_status,
                "fetched_at": r.fetched_at,
                "idempotency_key": r.idempotency_key,
                "source_identity_key": r.source_identity_key,
                "source_revision_key": r.source_revision_key,
                "replay_job_id": r.replay_job_id,
                "replay_version": r.replay_version,
            },
        )
    return items, truncated, total
