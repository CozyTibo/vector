"""Build ``GET …/cortex/pipeline/overview`` from execution lease + completeness projections."""

from __future__ import annotations

import copy
import logging
import threading
import time
import uuid
from typing import Any, Literal

_LOGGER = logging.getLogger("app")
_OVERVIEW_CACHE_TTL_SECONDS = 30.0
_OVERVIEW_STALE_SERVE_SECONDS = 120.0
_OVERVIEW_CACHE_LOCK = threading.Lock()
_OVERVIEW_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def invalidate_pipeline_overview_cache_v1(tenant_id: uuid.UUID) -> None:
    """Drop cached pipeline overview so operator actions refresh immediately."""
    key = str(tenant_id)
    with _OVERVIEW_CACHE_LOCK:
        _OVERVIEW_CACHE.pop(key, None)

from sqlalchemy.orm import Session

from vector.domains.cortex.completeness.canonical_completeness_projection import (
    project_canonical_completeness_v1,
)
from vector.domains.cortex.completeness.graph_completeness_projection import (
    project_graph_completeness_v1,
)
from vector.domains.cortex.completeness.identity_completeness_projection import (
    project_identity_completeness_v1,
)
from vector.domains.cortex.completeness.ingestion_completeness_projection import (
    project_ingestion_completeness_v1,
)
from vector.domains.cortex.completeness.tcre_completeness_projection import (
    project_tcre_completeness_v1,
)
from vector.domains.cortex.completeness.traversal_completeness_projection import (
    project_traversal_completeness_v1,
)
from vector.domains.cortex.execution.admin_commands import build_execution_inspect_v1
from vector.domains.cortex.execution.tenant_constants import FSM_BLOCKED, LEASE_STATUS_RUNNING
from vector.domains.cortex.ingestion.admin_overview import build_cortex_ingestion_admin_overview
from vector.domains.cortex.ingestion.admin_recent_raw import list_recent_ingestion_runs
from vector.domains.cortex.ingestion.ingestion_schedule_forecast import (
    estimate_tenant_next_scheduled_ingestion_v1,
)
from vector.domains.cortex.pipeline.pipeline_phase_operator_copy import (
    build_attention_lines,
    humanize_phase_issues,
    object_count_label,
    phase_status_label,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
)
from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
    project_retrieval_completeness_v1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    project_synthesis_completeness_v1,
)
from vector.settings import Settings

PhaseStatus = Literal["healthy", "running", "waiting", "blocked", "degraded"]
OperatorPhase = Literal[
    "ingestion",
    "canonical",
    "identity",
    "graph",
    "reconstruction",
    "retrieval",
    "synthesis",
]

_OPERATOR_PHASES: tuple[OperatorPhase, ...] = (
    "ingestion",
    "canonical",
    "identity",
    "graph",
    "reconstruction",
    "retrieval",
    "synthesis",
)

_PHASE_ID_TO_OPERATOR: dict[str, OperatorPhase] = {
    PHASE_02_CANONICAL: "canonical",
    PHASE_03_IDENTITY: "identity",
    PHASE_04_GRAPH: "graph",
    PHASE_05_TRAVERSAL: "graph",
    PHASE_06_TCRE: "reconstruction",
    PHASE_07_RETRIEVAL: "retrieval",
    PHASE_08_SYNTHESIS: "synthesis",
}

_FSM_TO_OPERATOR: dict[str, OperatorPhase] = {
    "CANONICAL": "canonical",
    "CANONICAL_DRAINING": "canonical",
    "IDENTITY": "identity",
    "GRAPH": "graph",
    "TRAVERSAL": "graph",
    "TCRE": "reconstruction",
    "AWAITING_TCRE": "reconstruction",
    "RETRIEVAL": "retrieval",
    "SYNTHESIS": "synthesis",
    "BLOCKED": "canonical",
    "IDLE": "synthesis",
}


def _mirror_to_status(raw: str | None) -> PhaseStatus:
    st = (raw or "").strip().lower()
    if st == "failed":
        return "blocked"
    if st == "running":
        return "running"
    if st == "waiting":
        return "waiting"
    if st in ("completed", "skipped"):
        return "healthy"
    if st == "queued":
        return "waiting"
    if st == "missing":
        return "waiting"
    return "waiting"


def _substrate_to_status(substrate_state: str | None) -> PhaseStatus:
    st = (substrate_state or "").strip().lower()
    if st == "critical":
        return "blocked"
    if st == "degraded":
        return "degraded"
    return "healthy"


def _ingestion_trigger_kind(*, source_trigger: str, replay_mode: bool) -> Literal["scheduled", "manual", "replay"]:
    if replay_mode:
        return "replay"
    key = (source_trigger or "").strip().lower()
    if key in ("scheduled", "scheduled_lane"):
        return "scheduled"
    if key in ("replay", "manual_admin_replay"):
        return "replay"
    return "manual"


def _merge_status(a: PhaseStatus, b: PhaseStatus) -> PhaseStatus:
    rank = {"blocked": 4, "running": 3, "degraded": 2, "waiting": 1, "healthy": 0}
    return a if rank[a] >= rank[b] else b


def _canonical_operator_backlog_count(envelope: dict[str, Any]) -> int | None:
    """Prefer drainable routable backlog over raw−mat admin gap (Fix 7)."""
    metrics = envelope.get("metrics")
    if isinstance(metrics, dict) and "drainable_routable_estimate" in metrics:
        return int(metrics.get("drainable_routable_estimate") or 0)
    backlog = envelope.get("unresolved_count")
    return int(backlog) if backlog is not None else None


def _envelope_blockers(envelope: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for w in envelope.get("drift_warnings") or []:
        if isinstance(w, str) and w.strip():
            out.append(w.strip())
    omissions = envelope.get("omission_classes") or {}
    if isinstance(omissions, dict):
        for key, count in sorted(omissions.items()):
            n = int(count) if isinstance(count, (int, float)) else 0
            if n > 0:
                out.append(f"{key}: {n}")
    label = str(envelope.get("label") or envelope.get("stage_id") or "phase")
    st = str(envelope.get("substrate_state") or "")
    if st == "critical":
        out.append(f"{label} substrate is critical")
    elif st == "degraded" and not out:
        out.append(f"{label} has known gaps")
    return out


def _phase_from_completeness(
    *,
    operator_phase: OperatorPhase,
    envelope: dict[str, Any],
    mirror_status: dict[str, str],
    lease: dict[str, Any] | None,
    phase_ids: tuple[str, ...],
) -> dict[str, Any]:
    status = _substrate_to_status(str(envelope.get("substrate_state")))
    for pid in phase_ids:
        status = _merge_status(status, _mirror_to_status(mirror_status.get(pid)))

    active_op: OperatorPhase | None = None
    if lease is not None:
        fsm = str(lease.get("fsm_state") or "").strip().upper()
        active_op = _FSM_TO_OPERATOR.get(fsm)
        if lease.get("status") == LEASE_STATUS_RUNNING and active_op == operator_phase:
            status = _merge_status(status, "running")
        if fsm == FSM_BLOCKED and active_op == operator_phase:
            status = _merge_status(status, "blocked")

    blockers = _phase_from_completeness_blockers(envelope, lease, active_op, operator_phase)
    processed = envelope.get("processed_count")
    if operator_phase == "canonical":
        backlog = _canonical_operator_backlog_count(envelope)
    else:
        backlog = envelope.get("unresolved_count")
        if backlog is None:
            backlog = envelope.get("omitted_count")
    processed_n = int(processed) if processed is not None else None
    backlog_n = int(backlog) if backlog is not None else None
    issues = humanize_phase_issues(
        operator_phase=operator_phase,
        status=status,
        blockers=blockers,
        backlog_count=backlog_n,
    )
    return {
        "phase": operator_phase,
        "status": status,
        "status_label": phase_status_label(status),
        "processed_count": processed_n,
        "object_count_label": object_count_label(processed_n),
        "backlog_count": backlog_n,
        "last_success_at": envelope.get("last_successful_at"),
        "blockers": blockers,
        "issues": issues,
    }


def _phase_from_completeness_blockers(
    envelope: dict[str, Any],
    lease: dict[str, Any] | None,
    active_op: OperatorPhase | None,
    operator_phase: OperatorPhase,
) -> list[str]:
    blockers = _envelope_blockers(envelope)
    if lease is not None and active_op == operator_phase:
        code = lease.get("block_reason_code")
        if isinstance(code, str) and code.strip():
            blockers.insert(0, str(code).strip())
        detail = lease.get("block_detail")
        if isinstance(detail, str) and detail.strip():
            blockers.append(detail.strip())
    return blockers[:8]


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


def _build_pipeline_overview_v1_uncached(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    inspect = build_execution_inspect_v1(session, tenant_id=tenant_id, transition_limit=5)
    lease = inspect.get("lease")
    progression = inspect.get("progression") or {}
    mirror_status: dict[str, str] = dict(progression.get("phase_status") or {})

    ingestion_admin = build_cortex_ingestion_admin_overview(
        session, settings, tenant_id, lite=True
    )
    ing_env = project_ingestion_completeness_v1(session, tenant_id=tenant_id)
    can_env = project_canonical_completeness_v1(session, tenant_id=tenant_id, admin_fast=True)
    id_env = project_identity_completeness_v1(session, tenant_id=tenant_id)
    graph_env = project_graph_completeness_v1(session, tenant_id=tenant_id)
    trav_env = project_traversal_completeness_v1(session, tenant_id=tenant_id)
    tcre_env = project_tcre_completeness_v1(session, tenant_id=tenant_id)
    ret_env = project_retrieval_completeness_v1(session, tenant_id=tenant_id)
    syn_env = project_synthesis_completeness_v1(session, tenant_id=tenant_id)

    def _worse_substrate(a: str | None, b: str | None) -> str:
        rank = {"healthy": 0, "degraded": 1, "critical": 2}
        sa = (a or "healthy").strip().lower()
        sb = (b or "healthy").strip().lower()
        return sa if rank.get(sa, 1) >= rank.get(sb, 1) else sb

    graph_merged = dict(graph_env)
    graph_merged["unresolved_count"] = int(graph_env.get("unresolved_count") or 0) + int(
        trav_env.get("unresolved_count") or 0
    )
    graph_merged["degraded_count"] = int(graph_env.get("degraded_count") or 0) + int(
        trav_env.get("degraded_count") or 0
    )
    graph_merged["substrate_state"] = _worse_substrate(
        str(graph_env.get("substrate_state")),
        str(trav_env.get("substrate_state")),
    )
    graph_merged["drift_warnings"] = list(graph_env.get("drift_warnings") or []) + list(
        trav_env.get("drift_warnings") or []
    )

    phases: list[dict[str, Any]] = []
    for op in _OPERATOR_PHASES:
        if op == "ingestion":
            st = _substrate_to_status(str(ing_env.get("substrate_state")))
            blockers = _envelope_blockers(ing_env)
            processed_n = int(ing_env.get("processed_count") or ing_env.get("total_objects") or 0)
            backlog_raw = int(ing_env.get("unresolved_count") or 0)
            backlog_n = backlog_raw if backlog_raw > 0 else None
            issues = humanize_phase_issues(
                operator_phase="ingestion",
                status=st,
                blockers=blockers,
                backlog_count=backlog_n,
            )
            phases.append(
                {
                    "phase": "ingestion",
                    "status": st,
                    "status_label": phase_status_label(st),
                    "processed_count": processed_n,
                    "object_count_label": object_count_label(processed_n),
                    "backlog_count": backlog_n,
                    "last_success_at": ing_env.get("last_successful_at"),
                    "blockers": blockers,
                    "issues": issues,
                }
            )
            continue
        env_map: dict[OperatorPhase, tuple[dict[str, Any], tuple[str, ...]]] = {
            "canonical": (can_env, (PHASE_02_CANONICAL,)),
            "identity": (id_env, (PHASE_03_IDENTITY,)),
            "graph": (graph_merged, (PHASE_04_GRAPH, PHASE_05_TRAVERSAL)),
            "reconstruction": (tcre_env, (PHASE_06_TCRE,)),
            "retrieval": (ret_env, (PHASE_07_RETRIEVAL,)),
            "synthesis": (syn_env, (PHASE_08_SYNTHESIS,)),
        }
        env, pids = env_map[op]
        phases.append(
            _phase_from_completeness(
                operator_phase=op,
                envelope=env,
                mirror_status=mirror_status,
                lease=lease if isinstance(lease, dict) else None,
                phase_ids=pids,
            )
        )

    exec_block: str | None = None
    if lease and isinstance(lease, dict):
        code = lease.get("block_reason_code")
        if isinstance(code, str) and code.strip():
            exec_block = code.strip()
    attention = build_attention_lines(phases, execution_block_reason=exec_block)

    execution = {
        "fsm_state": lease.get("fsm_state") if isinstance(lease, dict) else None,
        "phase_cursor": lease.get("phase_cursor") if isinstance(lease, dict) else None,
        "lease_status": lease.get("status") if isinstance(lease, dict) else None,
        "block_reason_code": lease.get("block_reason_code") if isinstance(lease, dict) else None,
    }

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
        connector_rows=ingestion_admin.get("connectors") if isinstance(ingestion_admin.get("connectors"), list) else None,
    )

    return {
        "surface_kind": "pipeline_overview",
        "tenant_id": str(tenant_id),
        "execution": execution,
        "phases": phases,
        "attention": attention,
        "scheduler": global_scheduler,
        "runnable_connectors": runnable,
        "recent_ingestion_runs": recent_ingestion_runs,
        "next_scheduled_ingestion": next_scheduled,
    }
