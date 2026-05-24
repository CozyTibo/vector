"""Build ``GET …/cortex/pipeline/overview`` from execution lease + completeness projections.

Operator primary KPI (D1 / Fix 7): ``operator_primary_kpi`` exposes
``drainable_routable_estimate`` via ``_canonical_operator_backlog_count`` — not raw−mat hero.
"""

from __future__ import annotations

import copy
import logging
import threading
import time
import uuid
from typing import Any, Literal

_LOGGER = logging.getLogger("app")
_OVERVIEW_CACHE_TTL_SECONDS = 60.0
_OVERVIEW_STALE_SERVE_SECONDS = 300.0
_OVERVIEW_CACHE_LOCK = threading.Lock()
_OVERVIEW_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_SLICE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def invalidate_pipeline_overview_cache_v1(tenant_id: uuid.UUID) -> None:
    """Drop cached pipeline overview so operator actions refresh immediately."""
    from vector.domains.cortex.pipeline.continuity_overview_v1 import (
        invalidate_continuity_overview_context_cache_v1,
    )
    from vector.domains.cortex.pipeline.pipeline_admin_semantic_readiness import (
        invalidate_semantic_readiness_cache_v1,
    )

    key = str(tenant_id)
    invalidate_semantic_readiness_cache_v1(tenant_id)
    invalidate_continuity_overview_context_cache_v1(tenant_id)
    from vector.domains.cortex.pipeline.pipeline_admin_graph_truth_inspector import (
        invalidate_graph_truth_inspector_cache_v1,
    )

    invalidate_graph_truth_inspector_cache_v1(tenant_id)
    with _OVERVIEW_CACHE_LOCK:
        _OVERVIEW_CACHE.pop(key, None)
        for suffix in ("execution", "phases", "ingestion", "continuity_bundle", "bootstrap"):
            _SLICE_CACHE.pop(f"{key}:{suffix}", None)

from sqlalchemy.orm import Session

from vector.domains.cortex.ingestion.admin_overview import build_cortex_ingestion_admin_overview
from vector.domains.cortex.ingestion.admin_recent_raw import list_recent_ingestion_runs
from vector.domains.cortex.ingestion.ingestion_schedule_forecast import (
    estimate_tenant_next_scheduled_ingestion_v1,
)
from vector.domains.cortex.execution.admin_commands import build_execution_inspect_v1
from vector.domains.cortex.pipeline.continuity_overview_v1 import (
    build_continuity_overview_bundle_v1,
    build_continuity_status_from_context_v1,
    get_cached_continuity_overview_context_v1,
)
from vector.domains.cortex.pipeline.canonical_operator_metrics import (
    _canonical_operator_backlog_count,
    snapshot_canonical_operator_metrics_v1,
)
from vector.domains.cortex.pipeline.pipeline_admin_operator_kpi import (
    build_operator_primary_kpi_v1,
)
from vector.domains.cortex.pipeline.pipeline_admin_semantic_readiness import (
    build_semantic_readiness_admin_v1,
)
from vector.settings import Settings

# Fix 7 / D1 static wiring probes read drainable helpers from this module.
__all__ = [
    "_canonical_operator_backlog_count",
    "build_operator_primary_kpi_v1",
    "snapshot_canonical_operator_metrics_v1",
]


def _cached_continuity_bundle_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    cache_key = f"{tenant_id}:continuity_bundle"

    def _build() -> dict[str, Any]:
        status, phases, items, lines = build_continuity_overview_bundle_v1(
            session, settings, tenant_id=tenant_id
        )
        return {
            "continuity_status": status,
            "phases": phases,
            "attention_items": items,
            "attention": lines,
        }

    payload = _cached_slice_v1(cache_key=cache_key, build=_build)
    return (
        dict(payload["continuity_status"]),
        list(payload["phases"]),
        list(payload["attention_items"]),
        list(payload["attention"]),
    )


def _ingestion_trigger_kind(*, source_trigger: str, replay_mode: bool) -> Literal["scheduled", "manual", "replay"]:
    if replay_mode:
        return "replay"
    key = (source_trigger or "").strip().lower()
    if key in ("scheduled", "scheduled_lane"):
        return "scheduled"
    if key in ("replay", "manual_admin_replay"):
        return "replay"
    return "manual"


def _cached_slice_v1(
    *,
    cache_key: str,
    build: Any,
) -> dict[str, Any]:
    now = time.monotonic()
    stale_payload: dict[str, Any] | None = None
    with _OVERVIEW_CACHE_LOCK:
        cached = _SLICE_CACHE.get(cache_key)
        if cached is not None:
            ts, payload = cached
            if now - ts <= _OVERVIEW_CACHE_TTL_SECONDS:
                return copy.deepcopy(payload)
            if now - ts <= _OVERVIEW_STALE_SERVE_SECONDS:
                stale_payload = copy.deepcopy(payload)
    try:
        out = build()
    except Exception:
        if stale_payload is not None:
            _LOGGER.warning(
                "serving stale cortex pipeline overview slice key=%s",
                cache_key,
                exc_info=True,
            )
            return stale_payload
        raise
    with _OVERVIEW_CACHE_LOCK:
        _SLICE_CACHE[cache_key] = (time.monotonic(), copy.deepcopy(out))
    return out


def build_pipeline_overview_execution_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Fast execution lease + continuity status for progressive admin load."""
    cache_key = f"{tenant_id}:execution"

    def _build() -> dict[str, Any]:
        ctx = get_cached_continuity_overview_context_v1(
            session, settings, tenant_id=tenant_id, overview_lite=True
        )
        continuity_status = build_continuity_status_from_context_v1(
            session, settings, ctx, tenant_id=tenant_id
        )
        return {
            "surface_kind": "pipeline_overview_execution",
            "tenant_id": str(tenant_id),
            "execution": _build_execution_snapshot_v1(session, tenant_id=tenant_id),
            "continuity_status": continuity_status,
            "operator_primary_kpi": build_operator_primary_kpi_v1(
                session,
                tenant_id=tenant_id,
                settings=settings,
                overview_slice=True,
                precomputed_metrics=ctx.operator_metrics,
            ),
        }

    return _cached_slice_v1(cache_key=cache_key, build=_build)


def build_pipeline_overview_phases_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Operational phase strip + structured attention (continuity projection)."""
    cache_key = f"{tenant_id}:phases"

    def _build() -> dict[str, Any]:
        continuity_status, phases, attention_items, attention = _cached_continuity_bundle_v1(
            session, settings, tenant_id=tenant_id
        )
        return {
            "surface_kind": "pipeline_overview_phases",
            "tenant_id": str(tenant_id),
            "continuity_status": continuity_status,
            "phases": phases,
            "attention": attention,
            "attention_items": attention_items,
        }

    return _cached_slice_v1(cache_key=cache_key, build=_build)


def build_pipeline_overview_ingestion_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Ingestion panel: scheduler, connectors, recent runs, next beat."""
    cache_key = f"{tenant_id}:ingestion"

    def _build() -> dict[str, Any]:
        return {
            "surface_kind": "pipeline_overview_ingestion",
            "tenant_id": str(tenant_id),
            **_build_ingestion_panel_v1(session, settings, tenant_id=tenant_id),
        }

    return _cached_slice_v1(cache_key=cache_key, build=_build)


def build_pipeline_overview_bootstrap_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Single-pass overview payload for admin UI (no semantic readiness)."""
    cache_key = f"{tenant_id}:bootstrap"

    def _build() -> dict[str, Any]:
        ctx = get_cached_continuity_overview_context_v1(
            session, settings, tenant_id=tenant_id, overview_lite=True
        )
        ingestion_admin = build_cortex_ingestion_admin_overview(
            session, settings, tenant_id, lite=True
        )
        continuity_status, phases, attention_items, attention = build_continuity_overview_bundle_v1(
            session,
            settings,
            tenant_id=tenant_id,
            ctx=ctx,
            ingestion_admin=ingestion_admin,
        )
        return {
            "surface_kind": "pipeline_overview_bootstrap",
            "tenant_id": str(tenant_id),
            "execution": _build_execution_snapshot_v1(session, tenant_id=tenant_id),
            "continuity_status": continuity_status,
            "operator_primary_kpi": build_operator_primary_kpi_v1(
                session,
                tenant_id=tenant_id,
                settings=settings,
                overview_slice=True,
                precomputed_metrics=ctx.operator_metrics,
            ),
            "phases": phases,
            "attention": attention,
            "attention_items": attention_items,
            **_build_ingestion_panel_v1(
                session,
                settings,
                tenant_id=tenant_id,
                ingestion_admin=ingestion_admin,
            ),
        }

    return _cached_slice_v1(cache_key=cache_key, build=_build)


def build_pipeline_overview_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Cached operator pipeline overview (fast path for admin UI)."""
    cache_key = str(tenant_id)
    now = time.monotonic()
    stale_payload: dict[str, Any] | None = None
    with _OVERVIEW_CACHE_LOCK:
        cached = _OVERVIEW_CACHE.get(cache_key)
        if cached is not None:
            ts, payload = cached
            if now - ts <= _OVERVIEW_CACHE_TTL_SECONDS:
                return copy.deepcopy(payload)
            if now - ts <= _OVERVIEW_STALE_SERVE_SECONDS:
                stale_payload = copy.deepcopy(payload)

    try:
        out = _build_pipeline_overview_v1_uncached(session, settings, tenant_id=tenant_id)
    except Exception:
        if stale_payload is not None:
            _LOGGER.warning(
                "serving stale cortex pipeline overview tenant_id=%s",
                tenant_id,
                exc_info=True,
            )
            return stale_payload
        raise

    with _OVERVIEW_CACHE_LOCK:
        _OVERVIEW_CACHE[cache_key] = (time.monotonic(), copy.deepcopy(out))
    return out


def _build_execution_snapshot_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    from vector.domains.cortex.execution.lease import (
        get_tenant_execution_lease_v1,
        lease_overview_public_dict_v1,
    )

    snap = lease_overview_public_dict_v1(get_tenant_execution_lease_v1(session, tenant_id=tenant_id))
    if snap is None:
        return {
            "fsm_state": None,
            "phase_cursor": None,
            "lease_status": None,
            "block_reason_code": None,
        }
    return {
        "fsm_state": snap.get("fsm_state"),
        "phase_cursor": snap.get("phase_cursor"),
        "lease_status": snap.get("status"),
        "block_reason_code": snap.get("block_reason_code"),
    }


def _build_ingestion_panel_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    ingestion_admin: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if ingestion_admin is None:
        ingestion_admin = build_cortex_ingestion_admin_overview(
            session, settings, tenant_id, lite=True
        )
    runnable = [
        row["connector"]
        for row in ingestion_admin.get("connectors") or []
        if row.get("cortex_routed") and row.get("connection_status") == "active"
    ]

    recent_ingestion_runs: list[dict[str, Any]] = []
    recent_rows, _recent_total = list_recent_ingestion_runs(session, tenant_id, limit=10)
    for row in recent_rows:
        recent_ingestion_runs.append(
            {
                "run_id": row["run_id"],
                "connector": row["connector"],
                "status": row["status"],
                "started_at": row["started_at"],
                "finished_at": row.get("finished_at"),
                "raw_rows_written": row.get("raw_rows_written"),
                "trigger_kind": _ingestion_trigger_kind(
                    source_trigger=str(row.get("source_trigger") or ""),
                    replay_mode=bool(row.get("replay_mode")),
                ),
            }
        )

    global_scheduler = ingestion_admin.get("global_scheduler")
    next_scheduled = estimate_tenant_next_scheduled_ingestion_v1(
        session,
        settings,
        tenant_id=tenant_id,
        scheduler=global_scheduler if isinstance(global_scheduler, dict) else None,
        connector_rows=ingestion_admin.get("connectors")
        if isinstance(ingestion_admin.get("connectors"), list)
        else None,
    )

    return {
        "scheduler": global_scheduler,
        "runnable_connectors": runnable,
        "recent_ingestion_runs": recent_ingestion_runs,
        "next_scheduled_ingestion": next_scheduled,
    }


def _build_pipeline_overview_v1_uncached(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    continuity_status, phases, attention_items, attention = _cached_continuity_bundle_v1(
        session, settings, tenant_id=tenant_id
    )
    execution = _build_execution_snapshot_v1(session, tenant_id=tenant_id)
    ingestion_panel = _build_ingestion_panel_v1(session, settings, tenant_id=tenant_id)

    return {
        "surface_kind": "pipeline_overview",
        "tenant_id": str(tenant_id),
        "execution": execution,
        "continuity_status": continuity_status,
        "operator_primary_kpi": build_operator_primary_kpi_v1(
            session, tenant_id=tenant_id, settings=settings
        ),
        "semantic_readiness": build_semantic_readiness_admin_v1(
            session, settings, tenant_id=tenant_id
        ),
        "phases": phases,
        "attention": attention,
        "attention_items": attention_items,
        **ingestion_panel,
    }
