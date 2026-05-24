"""Lean operator runtime builder (R2 — lease, dual-lane, paginated transitions; no island scan)."""

from __future__ import annotations

import copy
import threading
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.dual_lane_lease import build_dual_lane_inspect_v1
from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.execution.progression_status import build_substrate_progression_status_v1
from vector.domains.cortex.pipeline.operator_admin_overview import _operator_queue_counts_v1
from vector.infrastructure.db.models.cortex_execution_transition_log import CortexExecutionTransitionLog

_RUNTIME_CACHE_TTL_SECONDS = 15.0
_RUNTIME_CACHE_LOCK = threading.Lock()
_RUNTIME_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def invalidate_operator_runtime_cache_v1(tenant_id: uuid.UUID) -> None:
    prefix = f"{tenant_id}:"
    with _RUNTIME_CACHE_LOCK:
        for key in list(_RUNTIME_CACHE):
            if key.startswith(prefix):
                _RUNTIME_CACHE.pop(key, None)


def build_operator_runtime_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    transition_limit: int = 50,
    transition_offset: int = 0,
    pipeline_run_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Runtime inspect: lease truth, dual-lane, paginated transitions, queue hints."""
    lim = max(1, min(int(transition_limit), 200))
    offset = max(0, int(transition_offset))
    cache_key = f"{tenant_id}:{offset}:{lim}:{pipeline_run_id or ''}"
    now = time.monotonic()
    with _RUNTIME_CACHE_LOCK:
        cached = _RUNTIME_CACHE.get(cache_key)
        if cached is not None:
            ts, payload = cached
            if now - ts <= _RUNTIME_CACHE_TTL_SECONDS:
                return copy.deepcopy(payload)

    payload = _build_operator_runtime_uncached_v1(
        session,
        tenant_id=tenant_id,
        transition_limit=lim,
        transition_offset=offset,
        pipeline_run_id=pipeline_run_id,
    )
    with _RUNTIME_CACHE_LOCK:
        _RUNTIME_CACHE[cache_key] = (time.monotonic(), copy.deepcopy(payload))
    return payload


def _build_operator_runtime_uncached_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    transition_limit: int,
    transition_offset: int,
    pipeline_run_id: uuid.UUID | None,
) -> dict[str, Any]:
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    dual_lane = build_dual_lane_inspect_v1(session, tenant_id=tenant_id, lease=lease)
    progression = build_substrate_progression_status_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
    )
    queue_counts = _operator_queue_counts_v1(session, tenant_id=tenant_id)

    base_filter = CortexExecutionTransitionLog.tenant_id == tenant_id
    transition_total = int(
        session.scalar(select(func.count()).select_from(CortexExecutionTransitionLog).where(base_filter))
        or 0
    )
    transitions = list(
        session.scalars(
            select(CortexExecutionTransitionLog)
            .where(base_filter)
            .order_by(CortexExecutionTransitionLog.created_at.desc())
            .offset(transition_offset)
            .limit(transition_limit)
        ).all()
    )

    return {
        "surface_kind": "operator_runtime_v1",
        "tenant_id": str(tenant_id),
        "generated_at_utc": datetime.now(UTC),
        "lease": _lease_payload_v1(lease, dual_lane=dual_lane),
        "dual_lane": dual_lane,
        "progression": progression,
        "transitions": [_transition_payload_v1(row) for row in transitions],
        "transition_total": transition_total,
        "transition_limit": transition_limit,
        "transition_offset": transition_offset,
        "queue_counts": queue_counts,
    }


def _lease_payload_v1(lease: Any | None, *, dual_lane: dict[str, Any]) -> dict[str, Any] | None:
    if lease is None:
        return None
    canonical_lane = dual_lane.get("canonical_lane") if isinstance(dual_lane, dict) else None
    execution_lane = dual_lane.get("execution_lane") if isinstance(dual_lane, dict) else None
    return {
        "status": lease.status,
        "fsm_state": lease.fsm_state,
        "phase_cursor": lease.phase_cursor,
        "obligation_epoch": int(lease.obligation_epoch),
        "target_epoch": int(lease.target_epoch),
        "pipeline_run_id": str(lease.pipeline_run_id) if lease.pipeline_run_id else None,
        "block_reason_code": lease.block_reason_code,
        "block_detail": lease.block_detail,
        "last_error": (lease.last_error[:500] if lease.last_error else None),
        "canonical_lane_status": (
            canonical_lane.get("lane_status") if isinstance(canonical_lane, dict) else None
        ),
        "execution_lane_status": (
            execution_lane.get("lane_status") if isinstance(execution_lane, dict) else None
        ),
    }


def _transition_payload_v1(row: CortexExecutionTransitionLog) -> dict[str, Any]:
    return {
        "from_state": row.from_state,
        "to_state": row.to_state,
        "trigger": row.trigger,
        "gate_result": row.gate_result,
        "receipt_hash": row.receipt_hash,
        "pipeline_run_id": str(row.pipeline_run_id) if row.pipeline_run_id else None,
        "created_at": row.created_at,
        "detail_json": dict(row.detail_json or {}),
    }
