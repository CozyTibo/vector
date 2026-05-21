"""Build ``GET …/cortex/pipeline/overview`` from execution lease + completeness projections."""

from __future__ import annotations

import uuid
from typing import Any, Literal

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


def _merge_status(a: PhaseStatus, b: PhaseStatus) -> PhaseStatus:
    rank = {"blocked": 4, "running": 3, "degraded": 2, "waiting": 1, "healthy": 0}
    return a if rank[a] >= rank[b] else b


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
    backlog = envelope.get("unresolved_count")
    if backlog is None:
        backlog = envelope.get("omitted_count")
    return {
        "phase": operator_phase,
        "status": status,
        "processed_count": int(processed) if processed is not None else None,
        "backlog_count": int(backlog) if backlog is not None else None,
        "last_success_at": envelope.get("last_successful_at"),
        "blockers": blockers,
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
    inspect = build_execution_inspect_v1(session, tenant_id=tenant_id, transition_limit=20)
    lease = inspect.get("lease")
    progression = inspect.get("progression") or {}
    mirror_status: dict[str, str] = dict(progression.get("phase_status") or {})

    ingestion_admin = build_cortex_ingestion_admin_overview(session, settings, tenant_id)
    ing_env = project_ingestion_completeness_v1(session, tenant_id=tenant_id)
    can_env = project_canonical_completeness_v1(session, tenant_id=tenant_id)
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
            phases.append(
                {
                    "phase": "ingestion",
                    "status": st,
                    "processed_count": int(ing_env.get("processed_count") or ing_env.get("total_objects") or 0),
                    "backlog_count": int(ing_env.get("unresolved_count") or 0) or None,
                    "last_success_at": ing_env.get("last_successful_at"),
                    "blockers": _envelope_blockers(ing_env),
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

    attention: list[str] = []
    for p in phases:
        label = p["phase"].replace("_", " ").title()
        if p["status"] == "blocked":
            for b in p.get("blockers") or []:
                attention.append(f"{label} blocked: {b}")
            if not p.get("blockers"):
                attention.append(f"{label} is blocked")
        elif p["status"] == "degraded":
            attention.append(f"{label} degraded")
    if lease and isinstance(lease, dict):
        code = lease.get("block_reason_code")
        if code and str(code) not in " ".join(attention):
            attention.insert(0, f"Execution blocked: {code}")
    attention = attention[:5]

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

    return {
        "surface_kind": "pipeline_overview",
        "tenant_id": str(tenant_id),
        "execution": execution,
        "phases": phases,
        "attention": attention,
        "scheduler": ingestion_admin.get("global_scheduler"),
        "runnable_connectors": runnable,
    }
