"""Canon readiness inventory — raw exhaust vs materialization progress."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canon.mapper_version import CANON_MAPPER_VERSION
from vector.infrastructure.db.models.canon_materialization_cursor import CanonMaterializationCursor
from vector.infrastructure.db.models.canon_pass_run import CanonPassRun
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord
from vector.infrastructure.db.models.raw_memory_lineage_index import RawMemoryLineageIndex
from vector.infrastructure.db.models.tenant import Tenant

_HEALTH_RESOURCE_SUFFIXES = (".scope_ping",)
_HEALTH_RESOURCE_EXACT = frozenset({"scope_ping", "viewer_ping", "linear.viewer_ping"})


def _is_health_resource_type(resource_type: str) -> bool:
    if resource_type in _HEALTH_RESOURCE_EXACT:
        return True
    return any(resource_type.endswith(s) for s in _HEALTH_RESOURCE_SUFFIXES)


def scan_tenant_raw_inventory(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    include_health_rows: bool = False,
) -> dict[str, Any]:
    """Per-tenant raw row counts and max raw id (live lane only)."""
    base = select(
        RawIngestionRecord.resource_type,
        func.count().label("row_count"),
    ).where(
        RawIngestionRecord.tenant_id == tenant_id,
        RawIngestionRecord.replay_job_id.is_(None),
    )
    if not include_health_rows:
        base = base.where(
            RawIngestionRecord.resource_type.not_like("%.scope_ping"),
            RawIngestionRecord.resource_type.notin_(tuple(sorted(_HEALTH_RESOURCE_EXACT))),
        )
    by_type = {
        str(rt): int(n)
        for rt, n in session.execute(base.group_by(RawIngestionRecord.resource_type)).all()
    }
    max_raw_id = session.scalar(
        select(func.max(RawIngestionRecord.id)).where(
            RawIngestionRecord.tenant_id == tenant_id,
            RawIngestionRecord.replay_job_id.is_(None),
        ),
    )
    lineage_count = session.scalar(
        select(func.count())
        .select_from(RawMemoryLineageIndex)
        .where(RawMemoryLineageIndex.tenant_id == tenant_id),
    )
    return {
        "resource_type_counts": by_type,
        "total_live_rows": sum(by_type.values()),
        "max_live_raw_id": int(max_raw_id or 0),
        "lineage_identity_count": int(lineage_count or 0),
    }


def scan_materialization_lag(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    scope_key: str = "live",
) -> dict[str, Any]:
    """Compare canon cursor position to latest live raw id."""
    inv = scan_tenant_raw_inventory(session, tenant_id)
    max_raw = inv["max_live_raw_id"]
    cur = session.get(
        CanonMaterializationCursor,
        {"tenant_id": tenant_id, "scope_key": scope_key},
    )
    last_raw_id = int(cur.last_raw_id) if cur is not None else 0
    mapper_version = int(cur.mapper_version) if cur is not None else CANON_MAPPER_VERSION
    pending_raw_rows = max(0, max_raw - last_raw_id) if max_raw else 0
    return {
        "scope_key": scope_key,
        "last_raw_id": last_raw_id,
        "max_live_raw_id": max_raw,
        "pending_raw_rows_estimate": pending_raw_rows,
        "mapper_version": mapper_version,
        "expected_mapper_version": CANON_MAPPER_VERSION,
        "mapper_version_current": mapper_version == CANON_MAPPER_VERSION,
    }


def classify_resource_types_for_canon(
    resource_types: list[str],
    *,
    registry_disposition: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Map / skip / defer / unknown per resource type (registry supplied when available)."""
    reg = registry_disposition or {}
    mapped: list[str] = []
    skipped: list[str] = []
    deferred: list[str] = []
    unknown: list[str] = []
    for rt in sorted(set(resource_types)):
        disp = reg.get(rt, "unknown")
        if disp == "map":
            mapped.append(rt)
        elif disp == "skip":
            skipped.append(rt)
        elif disp == "defer":
            deferred.append(rt)
        else:
            unknown.append(rt)
    return {
        "mapped": mapped,
        "skipped": skipped,
        "deferred": deferred,
        "unknown": unknown,
    }


def build_tenant_canon_readiness(
    session: Session,
    tenant_id: uuid.UUID,
    *,
    registry_disposition: dict[str, str] | None = None,
    dirty_queue_depth: int = 0,
) -> dict[str, Any]:
    """Full readiness payload for admin overview."""
    tenant = session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("tenant_not_found")
    inv = scan_tenant_raw_inventory(session, tenant_id)
    lag = scan_materialization_lag(session, tenant_id)
    classification = classify_resource_types_for_canon(
        list(inv["resource_type_counts"].keys()),
        registry_disposition=registry_disposition,
    )
    latest_pass = session.scalar(
        select(CanonPassRun)
        .where(CanonPassRun.tenant_id == tenant_id)
        .order_by(CanonPassRun.started_at.desc())
        .limit(1),
    )
    latest_pass_payload: dict[str, Any] | None = None
    if latest_pass is not None:
        latest_pass_payload = {
            "id": str(latest_pass.id),
            "status": latest_pass.status,
            "source_trigger": latest_pass.source_trigger,
            "started_at": latest_pass.started_at.isoformat(),
            "finished_at": latest_pass.finished_at.isoformat() if latest_pass.finished_at else None,
            "stats": latest_pass.stats,
        }
    return {
        "tenant_id": str(tenant_id),
        "company_name": tenant.company_name,
        "mapper_version": CANON_MAPPER_VERSION,
        "raw_inventory": inv,
        "materialization_lag": lag,
        "resource_type_classification": classification,
        "dirty_queue_depth": dirty_queue_depth,
        "latest_pass_run": latest_pass_payload,
    }


def global_canon_inventory_snapshot(session: Session) -> dict[str, Any]:
    """Cross-tenant counts for operator dashboards."""
    tenant_count = session.scalar(select(func.count()).select_from(Tenant)) or 0
    pass_running = session.scalar(
        select(func.count()).where(CanonPassRun.status.in_(("RUNNING", "running"))),
    ) or 0
    max_raw_global = session.scalar(
        select(func.max(RawIngestionRecord.id)).where(RawIngestionRecord.replay_job_id.is_(None)),
    )
    return {
        "tenant_count": int(tenant_count),
        "pass_runs_running": int(pass_running),
        "global_max_live_raw_id": int(max_raw_global or 0),
    }
