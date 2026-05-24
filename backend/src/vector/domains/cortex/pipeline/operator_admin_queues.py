"""Operator queues builder (R4 — paginated synthesis/TCRE/deferrals/ingestion failed)."""

from __future__ import annotations

import copy
import threading
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.cortex_canonical_materialization_deferral import (
    CortexCanonicalMaterializationDeferral,
)
from vector.infrastructure.db.models.ingestion_run import IngestionRun
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import CortexTcreReconstructionJob

OperatorQueueTab = Literal["synthesis_failed", "tcre_queued", "deferrals", "ingestion_failed"]

_QUEUE_CACHE_TTL_SECONDS = 30.0
_QUEUE_CACHE_LOCK = threading.Lock()
_QUEUE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def invalidate_operator_queues_cache_v1(tenant_id: uuid.UUID) -> None:
    prefix = f"{tenant_id}:"
    with _QUEUE_CACHE_LOCK:
        for key in list(_QUEUE_CACHE):
            if key.startswith(prefix):
                _QUEUE_CACHE.pop(key, None)


def build_operator_queues_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    tab: OperatorQueueTab = "synthesis_failed",
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    lim = max(1, min(int(limit), 200))
    off = max(0, int(offset))
    cache_key = f"{tenant_id}:{tab}:{off}:{lim}"
    now = time.monotonic()
    with _QUEUE_CACHE_LOCK:
        cached = _QUEUE_CACHE.get(cache_key)
        if cached is not None:
            ts, payload = cached
            if now - ts <= _QUEUE_CACHE_TTL_SECONDS:
                return copy.deepcopy(payload)

    counts = _queue_tab_counts_v1(session, tenant_id=tenant_id)
    items, total = _queue_tab_items_v1(
        session,
        tenant_id=tenant_id,
        tab=tab,
        limit=lim,
        offset=off,
    )
    payload = {
        "surface_kind": "operator_queues_v1",
        "tenant_id": str(tenant_id),
        "tab": tab,
        "items": items,
        "total": total,
        "limit": lim,
        "offset": off,
        "counts": counts,
        "generated_at_utc": datetime.now(UTC),
    }
    with _QUEUE_CACHE_LOCK:
        _QUEUE_CACHE[cache_key] = (time.monotonic(), copy.deepcopy(payload))
    return payload


def _queue_tab_counts_v1(session: Session, *, tenant_id: uuid.UUID) -> dict[str, int]:
    row = session.execute(
        text(
            """
            SELECT
              (
                SELECT COUNT(*)::bigint FROM cortex_synthesis_jobs
                WHERE tenant_id = :tenant_id AND status = 'failed'
              ) AS synthesis_failed,
              (
                SELECT COUNT(*)::bigint FROM cortex_tcre_reconstruction_jobs
                WHERE tenant_id = :tenant_id AND status = 'queued'
              ) AS tcre_queued,
              (
                SELECT COUNT(*)::bigint FROM cortex_canonical_materialization_deferrals
                WHERE tenant_id = :tenant_id
                  AND retry_ready_at <= NOW()
                  AND COALESCE(detail_json->>'permanent_orphan', '') != 'true'
              ) AS deferrals_retry_ready,
              (
                SELECT COUNT(*)::bigint FROM ingestion_runs
                WHERE tenant_id = :tenant_id AND status = 'FAILED'
              ) AS ingestion_failed
            """
        ),
        {"tenant_id": str(tenant_id)},
    ).mappings().first()
    if row is None:
        return {
            "synthesis_failed": 0,
            "tcre_queued": 0,
            "deferrals": 0,
            "ingestion_failed": 0,
        }
    return {
        "synthesis_failed": int(row["synthesis_failed"] or 0),
        "tcre_queued": int(row["tcre_queued"] or 0),
        "deferrals": int(row["deferrals_retry_ready"] or 0),
        "ingestion_failed": int(row["ingestion_failed"] or 0),
    }


def _queue_tab_items_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    tab: OperatorQueueTab,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    if tab == "synthesis_failed":
        return _synthesis_failed_items_v1(session, tenant_id=tenant_id, limit=limit, offset=offset)
    if tab == "tcre_queued":
        return _tcre_queued_items_v1(session, tenant_id=tenant_id, limit=limit, offset=offset)
    if tab == "deferrals":
        return _deferral_items_v1(session, tenant_id=tenant_id, limit=limit, offset=offset)
    if tab == "ingestion_failed":
        return _ingestion_failed_items_v1(session, tenant_id=tenant_id, limit=limit, offset=offset)
    raise ValueError(f"unsupported_tab:{tab}")


def _synthesis_failed_items_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    base = (
        CortexSynthesisJob.tenant_id == tenant_id,
        CortexSynthesisJob.status == "failed",
    )
    total = int(session.scalar(select(func.count()).select_from(CortexSynthesisJob).where(*base)) or 0)
    rows = list(
        session.scalars(
            select(CortexSynthesisJob)
            .where(*base)
            .order_by(CortexSynthesisJob.completed_at.desc().nullslast(), CortexSynthesisJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    items = [
        {
            "kind": "synthesis_job",
            "id": str(row.id),
            "status": row.status,
            "intent": row.synthesis_intent,
            "workload_class": row.synthesis_workload_class,
            "error_detail": (row.error_detail or "")[:500] or None,
            "created_at": row.created_at,
            "completed_at": row.completed_at,
        }
        for row in rows
    ]
    return items, total


def _tcre_queued_items_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    base = (
        CortexTcreReconstructionJob.tenant_id == tenant_id,
        CortexTcreReconstructionJob.status == "queued",
    )
    total = int(
        session.scalar(select(func.count()).select_from(CortexTcreReconstructionJob).where(*base)) or 0
    )
    rows = list(
        session.scalars(
            select(CortexTcreReconstructionJob)
            .where(*base)
            .order_by(CortexTcreReconstructionJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    items = [
        {
            "kind": "tcre_job",
            "id": str(row.id),
            "status": row.status,
            "job_kind": row.job_kind,
            "scope_summary": dict(row.scope_json or {}).get("scope_id") or dict(row.scope_json or {}),
            "error_detail": (row.error_detail or "")[:500] or None,
            "created_at": row.created_at,
            "started_at": row.started_at,
        }
        for row in rows
    ]
    return items, total


def _deferral_items_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    base_filter = (
        CortexCanonicalMaterializationDeferral.tenant_id == tenant_id,
        CortexCanonicalMaterializationDeferral.retry_ready_at <= datetime.now(UTC),
        CortexCanonicalMaterializationDeferral.detail_json["permanent_orphan"].astext.is_distinct_from(
            "true"
        ),
    )
    total = int(
        session.scalar(
            select(func.count()).select_from(CortexCanonicalMaterializationDeferral).where(*base_filter)
        )
        or 0
    )
    rows = list(
        session.scalars(
            select(CortexCanonicalMaterializationDeferral)
            .where(*base_filter)
            .order_by(CortexCanonicalMaterializationDeferral.retry_ready_at.asc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    items = [
        {
            "kind": "deferral",
            "raw_record_id": int(row.raw_record_id),
            "connector": row.connector,
            "resource_type": row.resource_type,
            "deferral_reason": row.deferral_reason,
            "retry_ready_at": row.retry_ready_at,
            "deferred_at": row.deferred_at,
            "missing_parent_ref": row.missing_parent_ref,
        }
        for row in rows
    ]
    return items, total


def _ingestion_failed_items_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    base = (
        IngestionRun.tenant_id == tenant_id,
        IngestionRun.status == "FAILED",
    )
    total = int(session.scalar(select(func.count()).select_from(IngestionRun).where(*base)) or 0)
    rows = list(
        session.scalars(
            select(IngestionRun)
            .where(*base)
            .order_by(IngestionRun.started_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    items = [
        {
            "kind": "ingestion_run",
            "id": str(row.id),
            "connector": row.connector,
            "status": row.status,
            "error_summary": row.error_summary,
            "started_at": row.started_at,
            "finished_at": row.finished_at,
        }
        for row in rows
    ]
    return items, total
