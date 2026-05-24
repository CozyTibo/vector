"""Lean operator overview builder (R0 dark launch — 8-query cap, no legacy context forest)."""

from __future__ import annotations

import copy
import logging
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.ingestion.admin_overview import build_cortex_ingestion_admin_overview
from vector.domains.cortex.ingestion.admin_recent_raw import list_recent_ingestion_runs
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
    PHASE_STATUS_COMPLETED,
    PHASE_STATUS_FAILED,
)
from vector.domains.cortex.pipeline.admin_continuity_snapshot import read_admin_continuity_snapshot_v1
from vector.domains.cortex.substrate_pipeline.pipeline_receipts import build_phase_execution_receipt_v1
from vector.infrastructure.cortex_scheduler_pause import read_scheduler_paused_flag
from vector.infrastructure.db.models.cortex_execution_transition_log import CortexExecutionTransitionLog
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
    CortexSubstratePhaseRun,
    CortexSubstratePipelineRun,
)
from vector.settings import Settings

_LOGGER = logging.getLogger("app")
_OVERVIEW_CACHE_TTL_SECONDS = 30.0
_OVERVIEW_CACHE_LOCK = threading.Lock()
_OVERVIEW_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def invalidate_operator_overview_cache_v1(tenant_id: uuid.UUID) -> None:
    with _OVERVIEW_CACHE_LOCK:
        _OVERVIEW_CACHE.pop(str(tenant_id), None)


def build_operator_overview_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Assemble operator overview from bounded query groups (no semantic/continuity bundle)."""
    cache_key = str(tenant_id)
    now = time.monotonic()
    with _OVERVIEW_CACHE_LOCK:
        cached = _OVERVIEW_CACHE.get(cache_key)
        if cached is not None:
            ts, payload = cached
            if now - ts <= _OVERVIEW_CACHE_TTL_SECONDS:
                return copy.deepcopy(payload)

    payload = _build_operator_overview_uncached_v1(session, settings, tenant_id=tenant_id)
    with _OVERVIEW_CACHE_LOCK:
        _OVERVIEW_CACHE[cache_key] = (time.monotonic(), copy.deepcopy(payload))
    return payload


def _build_operator_overview_uncached_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    query_groups = 0

    # 1 — lease row
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    query_groups += 1

    # 2 — recent execution transitions (status banner + recent events)
    transitions = list(
        session.scalars(
            select(CortexExecutionTransitionLog)
            .where(CortexExecutionTransitionLog.tenant_id == tenant_id)
            .order_by(CortexExecutionTransitionLog.created_at.desc())
            .limit(5)
        ).all()
    )
    query_groups += 1
    last_transition = transitions[0] if transitions else None

    # 3 — ingestion connectors (lite path; cached internally)
    ingestion_overview = build_cortex_ingestion_admin_overview(
        session,
        settings,
        tenant_id,
        lite=True,
    )
    query_groups += 1

    # 4 — recent ingestion runs
    recent_runs, _total = list_recent_ingestion_runs(session, tenant_id, limit=3)
    query_groups += 1

    # 5 — last terminal receipts for phases 07 and 08
    phase_receipts = _latest_terminal_phase_receipts_v1(session, tenant_id=tenant_id)
    query_groups += 1

    # 6 — queue counts (single round trip)
    queue_counts = _operator_queue_counts_v1(session, tenant_id=tenant_id)
    query_groups += 1

    # 7 — materialized continuity snapshot (R1 table)
    continuity_snapshot = read_admin_continuity_snapshot_v1(session, tenant_id=tenant_id)
    query_groups += 1

    # 8 — scheduler pause (Redis; not a DB query)
    global_scheduler = ingestion_overview.get("global_scheduler")
    scheduler = _operator_scheduler_state_v1(
        settings,
        global_scheduler=global_scheduler if isinstance(global_scheduler, dict) else None,
    )
    query_groups += 1

    runnable_connectors = _runnable_connectors_from_ingestion_v1(ingestion_overview)

    status_banner = _build_status_banner_v1(lease=lease, last_transition=last_transition)
    continuity_facts = _build_continuity_facts_v1(
        ingestion_overview=ingestion_overview,
        lease=lease,
        last_transition=last_transition,
        phase_receipts=phase_receipts,
        queue_counts=queue_counts,
        continuity_snapshot=continuity_snapshot,
    )
    recent_events = _merge_recent_events_v1(recent_runs=recent_runs, transitions=transitions)
    connectors = _connector_rows_from_ingestion_v1(ingestion_overview)

    return {
        "surface_kind": "operator_overview_v1",
        "tenant_id": str(tenant_id),
        "generated_at_utc": datetime.now(UTC),
        "status_banner": status_banner,
        "continuity_facts": continuity_facts,
        "recent_events": recent_events,
        "connectors": connectors,
        "phase_receipts": phase_receipts,
        "queue_counts": queue_counts,
        "continuity_snapshot": continuity_snapshot,
        "scheduler": scheduler,
        "runnable_connectors": runnable_connectors,
        "query_groups_used": query_groups,
    }


def _build_status_banner_v1(
    *,
    lease: Any | None,
    last_transition: CortexExecutionTransitionLog | None,
) -> dict[str, Any]:
    return {
        "lease_status": lease.status if lease is not None else None,
        "fsm_state": lease.fsm_state if lease is not None else None,
        "phase_cursor": lease.phase_cursor if lease is not None else None,
        "block_reason_code": lease.block_reason_code if lease is not None else None,
        "block_detail": lease.block_detail if lease is not None else None,
        "obligation_epoch": int(lease.obligation_epoch) if lease is not None else None,
        "target_epoch": int(lease.target_epoch) if lease is not None else None,
        "pipeline_run_id": str(lease.pipeline_run_id) if lease and lease.pipeline_run_id else None,
        "last_transition_at": last_transition.created_at if last_transition else None,
        "last_transition_trigger": last_transition.trigger if last_transition else None,
        "last_transition_from_state": last_transition.from_state if last_transition else None,
        "last_transition_to_state": last_transition.to_state if last_transition else None,
    }


def _latest_terminal_phase_receipts_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, dict[str, Any]]:
    terminal_statuses = (PHASE_STATUS_COMPLETED, PHASE_STATUS_FAILED)
    out: dict[str, dict[str, Any]] = {}
    for phase_id in (PHASE_07_RETRIEVAL, PHASE_08_SYNTHESIS):
        phase_row = session.scalar(
            select(CortexSubstratePhaseRun)
            .join(
                CortexSubstratePipelineRun,
                CortexSubstratePipelineRun.id == CortexSubstratePhaseRun.pipeline_run_id,
            )
            .where(
                CortexSubstratePipelineRun.tenant_id == tenant_id,
                CortexSubstratePhaseRun.phase_id == phase_id,
                CortexSubstratePhaseRun.status.in_(terminal_statuses),
            )
            .order_by(
                CortexSubstratePhaseRun.completed_at.desc().nullslast(),
                CortexSubstratePhaseRun.started_at.desc().nullslast(),
            )
            .limit(1)
        )
        out[phase_id] = _phase_receipt_summary_v1(phase_row, phase_id=phase_id)
    return out


def _phase_receipt_summary_v1(
    phase_row: CortexSubstratePhaseRun | None,
    *,
    phase_id: str,
) -> dict[str, Any]:
    if phase_row is None:
        return {
            "phase_id": phase_id,
            "status": None,
            "started_at": None,
            "completed_at": None,
            "error_detail": None,
            "receipt_digest": None,
            "output_summary": {},
        }
    output = dict(phase_row.output_json or {})
    receipt = build_phase_execution_receipt_v1(
        phase_id=phase_row.phase_id,
        status=phase_row.status,
        output=output,
    )
    return {
        "phase_id": phase_row.phase_id,
        "status": phase_row.status,
        "started_at": phase_row.started_at,
        "completed_at": phase_row.completed_at,
        "error_detail": phase_row.error_detail,
        "receipt_digest": receipt.get("phase_execution_receipt_digest"),
        "output_summary": (receipt.get("body") or {}).get("output_summary") or {},
    }


def _operator_queue_counts_v1(session: Session, *, tenant_id: uuid.UUID) -> dict[str, int]:
    row = session.execute(
        text(
            """
            SELECT
              (
                SELECT COUNT(*)::bigint
                FROM cortex_canonical_materialization_deferrals
                WHERE tenant_id = :tenant_id
                  AND retry_ready_at <= NOW()
                  AND COALESCE(detail_json->>'permanent_orphan', '') != 'true'
              ) AS deferral_retry_ready,
              (
                SELECT COUNT(*)::bigint
                FROM cortex_synthesis_jobs
                WHERE tenant_id = :tenant_id AND status = 'failed'
              ) AS synthesis_failed,
              (
                SELECT COUNT(*)::bigint
                FROM cortex_tcre_reconstruction_jobs
                WHERE tenant_id = :tenant_id AND status = 'queued'
              ) AS tcre_queued
            """
        ),
        {"tenant_id": str(tenant_id)},
    ).mappings().first()
    if row is None:
        return {"deferral_retry_ready": 0, "synthesis_failed": 0, "tcre_queued": 0}
    return {
        "deferral_retry_ready": int(row["deferral_retry_ready"] or 0),
        "synthesis_failed": int(row["synthesis_failed"] or 0),
        "tcre_queued": int(row["tcre_queued"] or 0),
    }


def _runnable_connectors_from_ingestion_v1(ingestion_overview: dict[str, Any]) -> list[str]:
    return [
        str(row["connector"])
        for row in ingestion_overview.get("connectors") or []
        if isinstance(row, dict)
        and row.get("cortex_routed")
        and row.get("connection_status") == "active"
    ]


def _operator_scheduler_state_v1(
    settings: Settings,
    *,
    global_scheduler: dict[str, Any] | None = None,
) -> dict[str, Any]:
    paused = read_scheduler_paused_flag(settings)
    env_on = settings.cortex_ingestion_scheduler_enabled
    gs = global_scheduler or {}
    label = str(gs.get("operator_mode_label") or "")
    if not label:
        if not env_on and paused:
            label = "Off (env) + paused (operator)"
        elif not env_on:
            label = "Off (env)"
        elif paused:
            label = "Paused (operator)"
        else:
            label = "Active"
    return {
        "env_scheduler_enabled": bool(gs.get("env_scheduler_enabled", env_on)),
        "paused_via_redis": bool(gs.get("paused_via_redis", paused)),
        "operator_mode_label": label,
        "beat_interval_seconds": int(
            gs.get("beat_interval_seconds") or settings.cortex_ingestion_scheduler_interval_seconds
        ),
        "min_gap_seconds": int(
            gs.get("min_gap_seconds") or settings.cortex_ingestion_min_gap_seconds
        ),
    }


def _connector_rows_from_ingestion_v1(ingestion_overview: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in ingestion_overview.get("connectors") or []:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "connector": item.get("connector") or "",
                "connection_id": str(item["connection_id"]) if item.get("connection_id") else None,
                "connection_status": item.get("connection_status"),
                "cortex_routed": bool(item.get("cortex_routed")),
                "checkpoint_last_incremental_at": item.get("checkpoint_last_incremental_at"),
                "latest_run": item.get("latest_run"),
            }
        )
    return rows


def _humanize_age(dt: datetime | None) -> str:
    if dt is None:
        return "never"
    now = datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    delta = now - dt
    if delta < timedelta(hours=1):
        mins = max(1, int(delta.total_seconds() // 60))
        return f"{mins}m ago"
    if delta < timedelta(days=1):
        hours = max(1, int(delta.total_seconds() // 3600))
        return f"{hours}h ago"
    days = max(1, delta.days)
    return f"{days}d ago"


def _build_continuity_facts_v1(
    *,
    ingestion_overview: dict[str, Any],
    lease: Any | None,
    last_transition: CortexExecutionTransitionLog | None,
    phase_receipts: dict[str, dict[str, Any]],
    queue_counts: dict[str, int],
    continuity_snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    connector_bits: list[str] = []
    for row in ingestion_overview.get("connectors") or []:
        if not isinstance(row, dict):
            continue
        connector = str(row.get("connector") or "unknown")
        latest = row.get("latest_run") or {}
        finished = latest.get("finished_at") or latest.get("started_at")
        if isinstance(finished, str):
            try:
                finished_dt = datetime.fromisoformat(finished.replace("Z", "+00:00"))
            except ValueError:
                finished_dt = None
        else:
            finished_dt = finished if isinstance(finished, datetime) else None
        status = str(latest.get("status") or "no runs").lower()
        connector_bits.append(f"{connector} {status} ({_humanize_age(finished_dt)})")
    ingestion_text = (
        "; ".join(connector_bits[:4])
        if connector_bits
        else "No connector sync history yet."
    )

    if lease is None:
        execution_text = "No execution lease row — worker has not started for this tenant."
    elif lease.block_reason_code:
        execution_text = (
            f"Worker {lease.status} at {lease.phase_cursor or 'unknown phase'}; "
            f"blocked: {lease.block_reason_code}."
        )
    elif last_transition is not None:
        execution_text = (
            f"Worker {lease.status}; last transition "
            f"{last_transition.from_state} → {last_transition.to_state} "
            f"({_humanize_age(last_transition.created_at)})."
        )
    else:
        execution_text = f"Worker {lease.status}; no transitions recorded yet."

    graph_summary = continuity_snapshot.get("graph_summary") if continuity_snapshot.get("available") else None
    if isinstance(graph_summary, dict) and graph_summary.get("summary_text"):
        graph_text = str(graph_summary["summary_text"])
    elif continuity_snapshot.get("available"):
        entities = graph_summary.get("entities_in_graph") if isinstance(graph_summary, dict) else None
        graph_text = f"{entities} entities in auth graph." if entities is not None else "Graph snapshot captured."
    else:
        graph_text = "Graph continuity snapshot pending (materialized row not yet populated)."

    phase07 = phase_receipts.get(PHASE_07_RETRIEVAL) or {}
    if phase07.get("status") == PHASE_STATUS_FAILED:
        retrieval_text = (
            f"Retrieval phase failed: {(phase07.get('error_detail') or 'unknown error')[:120]}."
        )
    elif phase07.get("status") == PHASE_STATUS_COMPLETED:
        summary = phase07.get("output_summary") or {}
        epoch = summary.get("published_index_epoch") or summary.get("index_epoch")
        retrieval_text = f"Last retrieval publish succeeded (epoch {epoch or 'unknown'})."
    else:
        retrieval_text = "No terminal retrieval phase receipt yet."

    failed = int(queue_counts.get("synthesis_failed") or 0)
    phase08 = phase_receipts.get(PHASE_08_SYNTHESIS) or {}
    if failed > 0:
        synthesis_text = f"{failed} failed synthesis jobs in backlog."
    elif phase08.get("status") == PHASE_STATUS_COMPLETED:
        synthesis_text = "Latest synthesis phase completed."
    else:
        synthesis_text = "No published synthesis backlog signal yet."

    return [
        {"key": "ingestion", "text": ingestion_text, "inspect_lens": "ingestion"},
        {"key": "execution", "text": execution_text, "inspect_lens": "runtime"},
        {"key": "graph", "text": graph_text, "inspect_lens": "graph"},
        {"key": "retrieval", "text": retrieval_text, "inspect_lens": "retrieval"},
        {"key": "synthesis", "text": synthesis_text, "inspect_lens": "queues"},
    ]


def _merge_recent_events_v1(
    *,
    recent_runs: list[dict[str, Any]],
    transitions: list[CortexExecutionTransitionLog],
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for run in recent_runs:
        if not isinstance(run, dict):
            continue
        at_raw = run.get("finished_at") or run.get("started_at") or run.get("created_at")
        if isinstance(at_raw, str):
            try:
                at = datetime.fromisoformat(at_raw.replace("Z", "+00:00"))
            except ValueError:
                continue
        elif isinstance(at_raw, datetime):
            at = at_raw
        else:
            continue
        connector = run.get("connector") or "unknown"
        status = run.get("status") or "unknown"
        events.append(
            {
                "kind": "ingestion_run",
                "at": at,
                "summary": f"Ingestion {connector} {status}",
                "detail": {"run_id": run.get("id"), "connector": connector, "status": status},
            }
        )
    for tr in transitions:
        events.append(
            {
                "kind": "execution_transition",
                "at": tr.created_at,
                "summary": f"Transition {tr.from_state} → {tr.to_state} ({tr.trigger})",
                "detail": {
                    "from_state": tr.from_state,
                    "to_state": tr.to_state,
                    "trigger": tr.trigger,
                    "gate_result": tr.gate_result,
                },
            }
        )
    events.sort(key=lambda e: e["at"], reverse=True)
    return events[:10]
