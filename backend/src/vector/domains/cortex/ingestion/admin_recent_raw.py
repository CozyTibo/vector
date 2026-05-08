"""Phase 01 admin — recent runs and raw row previews for operator visualization."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


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
    return out


def list_recent_ingestion_runs(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    limit: int = 30,
) -> list[dict[str, Any]]:
    stmt = (
        select(IngestionRun)
        .where(IngestionRun.tenant_id == tenant_id)
        .order_by(IngestionRun.started_at.desc())
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
    return out


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
