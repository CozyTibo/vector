"""Fast operational continuity overview — projections, not substrate vanity scans."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.canonical_phase_admin_lite import (
    build_canonical_phase_summary_metrics_v1,
)
from vector.domains.cortex.canonical.forward_progress.deferral_store import count_deferrals
from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform
from vector.domains.cortex.canonical.permanent_orphan_omission_doctrine import (
    evaluate_permanent_orphan_omission_posture_v1,
)
from vector.domains.cortex.pipeline.canonical_operator_metrics import (
    snapshot_canonical_operator_metrics_v1,
)
from vector.domains.cortex.execution.admin_commands import build_execution_inspect_v1
from vector.domains.cortex.execution.lease import get_tenant_execution_lease_v1
from vector.domains.cortex.execution.progression_status import build_substrate_progression_status_v1
from vector.domains.cortex.execution.tenant_constants import (
    FSM_BLOCKED,
    LEASE_STATUS_RUNNING,
    LEASE_STATUS_WAITING,
)
from vector.domains.cortex.ingestion.admin_overview import build_cortex_ingestion_admin_overview
from vector.domains.cortex.operational_runtime.graph_density import (
    count_active_org_entities_v1,
    count_entities_with_promoted_edges_v1,
    count_graph_candidate_count_v1,
    count_graph_promoted_edge_count_v1,
)
from vector.domains.cortex.operational_runtime.graph_orphan_continuity import (
    list_graph_connected_components_v1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    evaluate_traversal_propagation_v1,
    list_eligible_traversal_components_v1,
)
from vector.domains.cortex.pipeline.pipeline_phase_operator_copy import phase_status_label
from vector.domains.cortex.retrieval.retrieval_completeness_projection import (
    count_retrieval_indexed_in_published_epoch_v1,
)
from vector.domains.cortex.retrieval.retrieval_index_materialization import get_published_index_epoch_v1
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
    PHASE_STATUS_COMPLETED,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_STALLED,
    CONTINUATION_STATUS_WAITING,
    get_continuation_for_pipeline_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    count_synthesis_eligible_scopes_v1,
)
from vector.domains.cortex.unlock.step12_track_b_p3 import (
    TRACK_B_SOAK_HOURS_REQUIRED_V1,
    evaluate_p2_autonomous_soak_v1,
)
from vector.infrastructure.db.models.cortex_octs_durable_walk_record import CortexOctsDurableWalkRecord
from vector.infrastructure.db.models.cortex_org_ambiguity_record import CortexOrgAmbiguityRecord
from vector.infrastructure.db.models.cortex_retrieval_index_epoch import CortexRetrievalIndexEpoch
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
    CortexSubstratePhaseRun,
    CortexSubstratePipelineRun,
)
from vector.infrastructure.db.models.cortex_synthesis_artifact import CortexSynthesisArtifact
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob
from vector.settings import Settings

ContinuityState = Literal[
    "AUTONOMOUS",
    "DEGRADED",
    "WEDGE_DEPENDENT",
    "STALLED",
    "BROKEN",
]
LaneStatus = Literal["HEALTHY", "DEGRADED", "BLOCKED", "WAITING", "UNKNOWN"]
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
AttentionPriority = Literal["P0", "P1", "P2"]

_OPERATOR_PHASES: tuple[OperatorPhase, ...] = (
    "ingestion",
    "canonical",
    "identity",
    "graph",
    "reconstruction",
    "retrieval",
    "synthesis",
)

def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()


def _ago_label(iso_at: str | None) -> str | None:
    if not iso_at:
        return None
    try:
        ts = datetime.fromisoformat(iso_at.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        delta = datetime.now(UTC) - ts.astimezone(UTC)
        mins = int(delta.total_seconds() // 60)
        if mins < 1:
            return "just now"
        if mins < 60:
            return f"{mins}m ago"
        hours = mins // 60
        if hours < 48:
            return f"{hours}h ago"
        days = hours // 24
        return f"{days}d ago"
    except ValueError:
        return None


def _signal(
    key: str,
    label: str,
    value: str | int | float | bool | None,
    *,
    severity: Literal["ok", "warn", "bad"] | None = None,
) -> dict[str, Any]:
    if value is None:
        text = "—"
    elif isinstance(value, bool):
        text = "yes" if value else "no"
    else:
        text = str(value)
    return {"key": key, "label": label, "value": text, "severity": severity}


def _last_phase_completed_at(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    phase_id: str,
) -> datetime | None:
    return session.scalar(
        select(CortexSubstratePhaseRun.completed_at)
        .join(
            CortexSubstratePipelineRun,
            CortexSubstratePipelineRun.id == CortexSubstratePhaseRun.pipeline_run_id,
        )
        .where(
            CortexSubstratePipelineRun.tenant_id == tenant_id,
            CortexSubstratePhaseRun.phase_id == phase_id,
            CortexSubstratePhaseRun.status == PHASE_STATUS_COMPLETED,
            CortexSubstratePhaseRun.completed_at.is_not(None),
        )
        .order_by(CortexSubstratePhaseRun.completed_at.desc())
        .limit(1)
    )


def _published_epoch_published_at(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    index_epoch: str | None,
) -> datetime | None:
    if not index_epoch:
        return None
    return session.scalar(
        select(CortexRetrievalIndexEpoch.published_at)
        .where(
            CortexRetrievalIndexEpoch.tenant_id == tenant_id,
            CortexRetrievalIndexEpoch.index_epoch == index_epoch,
            CortexRetrievalIndexEpoch.build_state == "PUBLISHED",
        )
        .limit(1)
    )


def _walk_operational_counts(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    since: datetime,
) -> dict[str, int]:
    base = select(func.count()).select_from(CortexOctsDurableWalkRecord).where(
        CortexOctsDurableWalkRecord.tenant_id == tenant_id,
        CortexOctsDurableWalkRecord.created_at >= since,
    )
    recent = int(session.scalar(base) or 0)
    completed = int(
        session.scalar(
            base.where(CortexOctsDurableWalkRecord.status.in_(("completed", "succeeded")))
        )
        or 0
    )
    failed = int(
        session.scalar(base.where(CortexOctsDurableWalkRecord.status.in_(("failed", "error"))))
        or 0
    )
    return {"recent_walks_24h": recent, "completed_walks_24h": completed, "failed_walks_24h": failed}


def build_continuity_status_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    settings: Settings,
    lease: dict[str, Any] | None,
    progression: dict[str, Any],
    propagation: dict[str, Any],
    canonical_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Top-level Cortex continuity status card."""
    lease_status = str((lease or {}).get("status") or "").strip().lower()
    fsm = str((lease or {}).get("fsm_state") or "").strip().upper()
    block_code = (lease or {}).get("block_reason_code")
    phase_cursor = str((lease or {}).get("phase_cursor") or progression.get("active_phase") or "")

    last_t05 = _last_phase_completed_at(session, tenant_id=tenant_id, phase_id=PHASE_05_TRAVERSAL)
    last_t06 = _last_phase_completed_at(session, tenant_id=tenant_id, phase_id=PHASE_06_TCRE)
    last_t07 = _last_phase_completed_at(session, tenant_id=tenant_id, phase_id=PHASE_07_RETRIEVAL)
    last_t08 = _last_phase_completed_at(session, tenant_id=tenant_id, phase_id=PHASE_08_SYNTHESIS)
    chain_times = [t for t in (last_t05, last_t06, last_t07, last_t08) if t is not None]
    last_full_chain_at = max(chain_times) if len(chain_times) == 4 else None

    published = get_published_index_epoch_v1(session, tenant_id=tenant_id)
    retrieval_published_at = _published_epoch_published_at(
        session, tenant_id=tenant_id, index_epoch=published
    )
    last_synth = session.scalar(
        select(CortexSynthesisArtifact.created_at)
        .where(CortexSynthesisArtifact.tenant_id == tenant_id)
        .order_by(CortexSynthesisArtifact.created_at.desc())
        .limit(1)
    )

    execution_lane: LaneStatus = "UNKNOWN"
    if fsm == FSM_BLOCKED or block_code:
        execution_lane = "BLOCKED"
    elif lease_status == LEASE_STATUS_RUNNING:
        execution_lane = "HEALTHY"
    elif lease_status == LEASE_STATUS_WAITING:
        execution_lane = "WAITING"
    elif progression.get("progression_class") in ("progressing", "operationally_alive"):
        execution_lane = "HEALTHY"
    else:
        execution_lane = "DEGRADED"

    operator_metrics = snapshot_canonical_operator_metrics_v1(session, tenant_id=tenant_id)
    untreated = int(
        (canonical_metrics.get("forward_progress") or {}).get("untreated_estimate")
        or operator_metrics.get("untreated_routable_estimate")
        or 0
    )
    drainable = int(operator_metrics.get("drainable_routable_estimate") or 0)
    bundle_id = resolve_default_bundle_id_for_stub_transform(session, tenant_id)
    deferral: dict[str, int] = {}
    topology_wait = False
    if bundle_id:
        deferral = count_deferrals(session, tenant_id=tenant_id, bundle_id=bundle_id)
        topology_wait = int(deferral.get("deferred_waiting_cooldown") or 0) > 0
    retry_ready = int(deferral.get("deferred_retry_ready") or 0)
    permanent = int(deferral.get("deferred_permanent_orphan") or 0)
    defer_total = int(deferral.get("deferred_total") or 0)
    permanent_pct = int(round(100 * permanent / defer_total)) if defer_total else 0

    canonical_lane: LaneStatus = "HEALTHY"
    if fsm in ("CANONICAL", "CANONICAL_DRAINING") and lease_status == LEASE_STATUS_RUNNING:
        canonical_lane = "HEALTHY"
    elif topology_wait or retry_ready > 500 or untreated > 5000:
        canonical_lane = "DEGRADED"
    elif permanent_pct > 50 and defer_total > 20 and not permanent_omission_ok:
        canonical_lane = "DEGRADED"
    elif untreated > 0 and execution_lane == "BLOCKED":
        canonical_lane = "WAITING"

    lease_row = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    detail = dict(lease_row.detail_json or {}) if lease_row is not None else {}
    last_canonical_outcome = str(
        detail.get("last_canonical_outcome") or detail.get("last_phase_outcome") or ""
    )
    soak = evaluate_p2_autonomous_soak_v1(
        phase_cursor=phase_cursor,
        last_canonical_outcome=last_canonical_outcome,
        drainable_routable_estimate=drainable,
        untreated_routable_estimate=untreated,
    )
    soak_active = bool(soak.get("p2_soak_t0_captured"))
    soak_started = soak.get("track_b_soak_started_at")
    soak_hours_elapsed: float | None = None
    if soak_active and soak_started:
        try:
            t0 = datetime.fromisoformat(str(soak_started).replace("Z", "+00:00"))
            if t0.tzinfo is None:
                t0 = t0.replace(tzinfo=UTC)
            soak_hours_elapsed = (datetime.now(UTC) - t0.astimezone(UTC)).total_seconds() / 3600.0
        except ValueError:
            soak_hours_elapsed = None

    propagation_blocked = bool(propagation.get("blocked"))
    progression_class = str(progression.get("progression_class") or "")
    run = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    continuation_stalled = False
    if run is not None:
        cont = get_continuation_for_pipeline_v1(session, pipeline_run_id=run.id)
        if cont is not None:
            continuation_stalled = cont.continuation_status in (
                CONTINUATION_STATUS_WAITING,
                CONTINUATION_STATUS_STALLED,
            )

    state: ContinuityState = "AUTONOMOUS"
    if propagation_blocked and int(propagation.get("entity_count") or 0) > 0:
        state = "BROKEN"
    elif fsm == FSM_BLOCKED or (block_code and str(block_code).strip()):
        state = "BROKEN"
    elif continuation_stalled:
        state = "STALLED"
    elif lease_status != LEASE_STATUS_RUNNING and progression_class == "idle" and last_synth:
        recent_manual = session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.status == "completed",
                CortexSynthesisJob.created_at >= datetime.now(UTC) - timedelta(hours=48),
            )
        )
        if int(recent_manual or 0) > 0:
            state = "WEDGE_DEPENDENT"
    elif execution_lane in ("BLOCKED", "WAITING") or canonical_lane == "DEGRADED" or propagation_blocked:
        state = "DEGRADED"
    elif lease_status == LEASE_STATUS_RUNNING and not propagation_blocked:
        state = "AUTONOMOUS"
    else:
        state = "DEGRADED"

    if lease_status != LEASE_STATUS_RUNNING and continuation_stalled:
        state = "STALLED"

    return {
        "state": state,
        "state_label": state.replace("_", " ").title(),
        "execution_lane": execution_lane,
        "canonical_lane": canonical_lane,
        "last_full_chain_at": _iso(last_full_chain_at),
        "last_full_chain_ago": _ago_label(_iso(last_full_chain_at)),
        "last_retrieval_epoch": published,
        "last_retrieval_epoch_at": _iso(retrieval_published_at),
        "last_retrieval_epoch_ago": _ago_label(_iso(retrieval_published_at)),
        "last_synthesis_at": _iso(last_synth),
        "last_synthesis_ago": _ago_label(_iso(last_synth)),
        "topology_wait": topology_wait,
        "aa_continuity_soak": {
            "active": soak_active,
            "hours_elapsed": round(soak_hours_elapsed, 1) if soak_hours_elapsed is not None else None,
            "hours_required": TRACK_B_SOAK_HOURS_REQUIRED_V1,
            "detail": soak.get("p2_soak_detail"),
        },
        "progression_class": progression_class,
    }


def _phase_card(
    *,
    phase: OperatorPhase,
    status: PhaseStatus,
    headline: str,
    continuity_advancing: bool,
    signals: list[dict[str, Any]],
    blockers: list[str] | None = None,
    last_success_at: str | None = None,
    backlog_count: int | None = None,
) -> dict[str, Any]:
    return {
        "phase": phase,
        "status": status,
        "status_label": phase_status_label(status),
        "headline": headline,
        "continuity_advancing": continuity_advancing,
        "signals": signals,
        "processed_count": None,
        "object_count_label": None,
        "backlog_count": backlog_count,
        "last_success_at": last_success_at,
        "blockers": list(blockers or [])[:6],
        "issues": [],
    }


def build_continuity_phase_cards_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
    lease: dict[str, Any] | None,
    progression: dict[str, Any],
) -> list[dict[str, Any]]:
    """Operational phase strip — indexed counts and receipts only."""
    fsm = str((lease or {}).get("fsm_state") or "").strip().upper()
    lease_running = (lease or {}).get("status") == LEASE_STATUS_RUNNING
    mirror: dict[str, str] = dict(progression.get("phase_status") or {})

    ingestion_admin = build_cortex_ingestion_admin_overview(
        session, settings, tenant_id, lite=True
    )
    connectors = list(ingestion_admin.get("connectors") or [])
    stale_connectors = 0
    latest_sync: datetime | None = None
    for row in connectors:
        if not row.get("cortex_routed"):
            continue
        if row.get("connection_status") != "active":
            stale_connectors += 1
        latest_run = row.get("latest_run") if isinstance(row.get("latest_run"), dict) else None
        finished = (latest_run or {}).get("finished_at") or (latest_run or {}).get("started_at")
        ck_at = row.get("checkpoint_last_incremental_at")
        for raw in (finished, ck_at):
            if not isinstance(raw, str):
                continue
            try:
                ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=UTC)
                if latest_sync is None or ts > latest_sync:
                    latest_sync = ts
            except ValueError:
                pass
    ingest_stalled = stale_connectors > 0 and len(connectors) > 0
    ing_status: PhaseStatus = "blocked" if ingest_stalled else "healthy"
    if ingest_stalled:
        ing_headline = "Connector freshness gap"
    else:
        ing_headline = "Connectors fresh"
    ingestion_card = _phase_card(
        phase="ingestion",
        status=ing_status,
        headline=ing_headline,
        continuity_advancing=not ingest_stalled,
        signals=[
            _signal("connector_freshness", "Active connectors", sum(1 for c in connectors if c.get("connection_status") == "active"), severity="ok"),
            _signal("ingest_stalled", "Ingest stalled", ingest_stalled, severity="bad" if ingest_stalled else "ok"),
            _signal("topology_pressure", "Stale / inactive", stale_connectors, severity="warn" if stale_connectors else "ok"),
            _signal("latest_sync", "Latest successful sync", _ago_label(_iso(latest_sync)) or "—"),
        ],
        last_success_at=_iso(latest_sync),
    )

    can_metrics = build_canonical_phase_summary_metrics_v1(session, tenant_id=tenant_id)
    operator_metrics = snapshot_canonical_operator_metrics_v1(session, tenant_id=tenant_id)
    bundle_id = resolve_default_bundle_id_for_stub_transform(session, tenant_id)
    deferral: dict[str, int] = dict(operator_metrics.get("deferral_counts") or {})
    if bundle_id and not deferral:
        deferral = count_deferrals(session, tenant_id=tenant_id, bundle_id=bundle_id)
    untreated = int((can_metrics.get("forward_progress") or {}).get("untreated_estimate") or 0)
    drainable = int(operator_metrics.get("drainable_routable_estimate") or 0)
    retry_ready = int(deferral.get("deferred_retry_ready") or 0)
    permanent = int(deferral.get("deferred_permanent_orphan") or 0)
    defer_total = int(deferral.get("deferred_total") or 0)
    permanent_pct = int(round(100 * permanent / defer_total)) if defer_total else 0
    omission_posture = evaluate_permanent_orphan_omission_posture_v1(deferral_counts=deferral)
    permanent_omission_ok = bool(omission_posture.get("is_bounded_omission_not_failure"))
    topology_wait = int(deferral.get("deferred_waiting_cooldown") or 0) > 0
    can_status: PhaseStatus = "healthy"
    if retry_ready > 1000 or drainable > 10000:
        can_status = "blocked"
    elif topology_wait or retry_ready > 0 or drainable > 500:
        can_status = "degraded"
    if fsm in ("CANONICAL", "CANONICAL_DRAINING") and lease_running:
        can_status = "running"
    if drainable > 0:
        can_headline = f"Drainable routable backlog ({drainable:,})"
    elif topology_wait:
        can_headline = "Topology wait"
    elif retry_ready == 0:
        can_headline = "Deferrals draining"
    else:
        can_headline = "Retry-ready pressure"
    can_card = _phase_card(
        phase="canonical",
        status=can_status,
        headline=can_headline,
        continuity_advancing=retry_ready == 0 and drainable < 500 and not topology_wait,
        backlog_count=drainable,
        signals=[
            _signal(
                "drainable_routable",
                "Drainable routable",
                drainable,
                severity="warn" if drainable else "ok",
            ),
            _signal("retry_ready", "Retry-ready deferrals", retry_ready, severity="warn" if retry_ready else "ok"),
            _signal(
                "permanent_orphan_omission",
                "Permanent orphan (omission)",
                f"{permanent:,} ({permanent_pct}% of deferrals)",
                severity="ok" if permanent_omission_ok else "warn",
            ),
            _signal("untreated_routable", "Untreated routable", untreated, severity="warn" if untreated else "ok"),
            _signal("topology_wait", "Topology wait", topology_wait, severity="warn" if topology_wait else "ok"),
        ],
        blockers=[f"retry_ready:{retry_ready}"] if retry_ready else None,
    )

    entity_count = count_active_org_entities_v1(session, tenant_id=tenant_id)
    open_ambiguity = int(
        session.scalar(
            select(func.count())
            .select_from(CortexOrgAmbiguityRecord)
            .where(
                CortexOrgAmbiguityRecord.tenant_id == tenant_id,
                CortexOrgAmbiguityRecord.status == "open",
            )
        )
        or 0
    )
    id_status: PhaseStatus = "degraded" if open_ambiguity else "healthy"
    if fsm == "IDENTITY" and lease_running:
        id_status = "running"
    id_card = _phase_card(
        phase="identity",
        status=id_status,
        headline="Replay conflicts" if open_ambiguity else "Handles stable",
        continuity_advancing=open_ambiguity == 0,
        signals=[
            _signal("active_handles", "Active org entities", entity_count),
            _signal("replay_conflicts", "Open ambiguities", open_ambiguity, severity="warn" if open_ambiguity else "ok"),
            _signal("continuity_advancing", "Continuity advancing", open_ambiguity == 0, severity="ok"),
        ],
    )

    linked = count_entities_with_promoted_edges_v1(session, tenant_id=tenant_id)
    promoted = count_graph_promoted_edge_count_v1(session, tenant_id=tenant_id)
    pending_candidates = count_graph_candidate_count_v1(session, tenant_id=tenant_id)
    components = list_graph_connected_components_v1(session, tenant_id=tenant_id)
    islands = len(components)
    eligible_islands = len(
        list_eligible_traversal_components_v1(session, tenant_id=tenant_id)
    )
    propagation = evaluate_traversal_propagation_v1(
        session,
        tenant_id=tenant_id,
        linked_entity_count=linked,
        entity_count=entity_count,
        orphan_disconnected_count=max(0, entity_count - linked),
        orphan_identity_unresolved_count=0,
    )
    graph_status: PhaseStatus = "healthy"
    if propagation.get("blocked"):
        graph_status = "blocked"
    elif eligible_islands < 1 and entity_count > 0:
        graph_status = "degraded"
    if fsm in ("GRAPH", "TRAVERSAL") and lease_running:
        graph_status = "running"
    graph_card = _phase_card(
        phase="graph",
        status=graph_status,
        headline="Propagation blocked" if propagation.get("blocked") else "Islands eligible for traversal",
        continuity_advancing=not propagation.get("blocked") and eligible_islands > 0,
        signals=[
            _signal("promoted_edges", "Promoted edges", promoted),
            _signal("pending_candidates", "Pending candidates", pending_candidates, severity="warn" if pending_candidates > 50 else "ok"),
            _signal("connected_islands", "Connected islands", islands),
            _signal("traversal_eligible", "Traversal-eligible islands", eligible_islands, severity="ok" if eligible_islands else "bad"),
            _signal("propagation_blocked", "Propagation blocked", propagation.get("blocked"), severity="bad" if propagation.get("blocked") else "ok"),
        ],
        blockers=[str(propagation.get("block_reason") or "")] if propagation.get("blocked") else None,
    )

    since = datetime.now(UTC) - timedelta(hours=24)
    walks = _walk_operational_counts(session, tenant_id=tenant_id, since=since)
    trav_status: PhaseStatus = "healthy"
    if walks["failed_walks_24h"] > walks["completed_walks_24h"] and walks["failed_walks_24h"] > 0:
        trav_status = "degraded"
    if fsm in ("TCRE", "AWAITING_TCRE") and lease_running:
        trav_status = "running"
    last_walk = session.scalar(
        select(CortexOctsDurableWalkRecord.created_at)
        .where(CortexOctsDurableWalkRecord.tenant_id == tenant_id)
        .order_by(CortexOctsDurableWalkRecord.created_at.desc())
        .limit(1)
    )
    trav_card = _phase_card(
        phase="reconstruction",
        status=trav_status,
        headline="Walk recurrence low" if walks["recent_walks_24h"] < 1 else "Walks executing",
        continuity_advancing=walks["completed_walks_24h"] > 0,
        signals=[
            _signal("recent_walks", "Recent walks (24h)", walks["recent_walks_24h"]),
            _signal("walk_recurrence", "Completed walks (24h)", walks["completed_walks_24h"]),
            _signal("failed_retries", "Failed walks (24h)", walks["failed_walks_24h"], severity="warn" if walks["failed_walks_24h"] else "ok"),
            _signal("last_walk", "Last walk", _ago_label(_iso(last_walk)) or "—"),
        ],
        last_success_at=_iso(last_walk),
    )

    index_stats = count_retrieval_indexed_in_published_epoch_v1(session, tenant_id=tenant_id)
    published = index_stats.get("published_index_epoch")
    indexed = int(index_stats.get("indexed_count") or 0)
    ret_published_at = _published_epoch_published_at(
        session, tenant_id=tenant_id, index_epoch=str(published) if published else None
    )
    recurring = walks["completed_walks_24h"] > 0 and indexed > 0
    ret_status: PhaseStatus = "healthy" if indexed > 0 else "waiting"
    if mirror.get(PHASE_07_RETRIEVAL) == "failed":
        ret_status = "blocked"
    if fsm == "RETRIEVAL" and lease_running:
        ret_status = "running"
    ret_card = _phase_card(
        phase="retrieval",
        status=ret_status,
        headline="Retrieval recurring" if recurring else "Awaiting index epoch",
        continuity_advancing=recurring,
        signals=[
            _signal("published_epoch", "Published epoch", published or "—"),
            _signal("indexed_in_epoch", "Indexed in epoch", indexed),
            _signal("recurring", "Recurring", recurring, severity="ok" if recurring else "warn"),
            _signal("last_epoch", "Last epoch publish", _ago_label(_iso(ret_published_at)) or "—"),
        ],
        last_success_at=_iso(ret_published_at),
    )

    synth_scope = count_synthesis_eligible_scopes_v1(session, tenant_id=tenant_id)
    eligible_scopes = int(synth_scope.get("eligible_scopes") or 0)
    synth_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisArtifact)
            .where(CortexSynthesisArtifact.tenant_id == tenant_id)
        )
        or 0
    )
    last_synth = session.scalar(
        select(CortexSynthesisArtifact.created_at)
        .where(CortexSynthesisArtifact.tenant_id == tenant_id)
        .order_by(CortexSynthesisArtifact.created_at.desc())
        .limit(1)
    )
    autonomous = lease_running and fsm == "SYNTHESIS"
    wedge_only = synth_count > 0 and not lease_running
    syn_status: PhaseStatus = "healthy" if synth_count > 0 else "waiting"
    if eligible_scopes > 0 and synth_count == 0:
        syn_status = "degraded"
    if fsm == "SYNTHESIS" and lease_running:
        syn_status = "running"
    syn_card = _phase_card(
        phase="synthesis",
        status=syn_status,
        headline="Autonomous synthesis" if autonomous else ("Wedge-generated history" if wedge_only else "Awaiting scopes"),
        continuity_advancing=autonomous or (synth_count > 0 and eligible_scopes > 0),
        signals=[
            _signal("eligible_scopes", "Eligible scopes", eligible_scopes),
            _signal("artifact_count", "Artifacts (tenant)", synth_count),
            _signal("mode", "Mode", "autonomous" if autonomous else ("wedge" if wedge_only else "idle")),
            _signal("last_artifact", "Last phase-08 artifact", _ago_label(_iso(last_synth)) or "—"),
        ],
        last_success_at=_iso(last_synth),
    )

    return [
        ingestion_card,
        can_card,
        id_card,
        graph_card,
        trav_card,
        ret_card,
        syn_card,
    ]


def build_continuity_attention_items_v1(
    *,
    continuity_status: dict[str, Any],
    phases: list[dict[str, Any]],
    lease: dict[str, Any] | None,
    propagation: dict[str, Any],
) -> list[dict[str, Any]]:
    """Ordered root-cause attention — suppress downstream when upstream explains."""
    items: list[dict[str, Any]] = []
    state = str(continuity_status.get("state") or "")
    block_code = (lease or {}).get("block_reason_code")
    if block_code:
        items.append(
            {
                "priority": "P0",
                "title": f"Execution blocked — {block_code}",
                "impact": "autonomous execution lane cannot advance",
                "action": "inspect execution lease block detail and clear upstream fault",
                "phase": "canonical",
            }
        )
    if propagation.get("blocked"):
        reason = str(propagation.get("block_reason") or "propagation_blocked")
        items.append(
            {
                "priority": "P0",
                "title": f"Graph propagation blocked — {reason}",
                "impact": "no autonomous 05→08 continuity across islands",
                "action": "resolve identity orphans or promote edges until traversal-eligible islands exist",
                "phase": "graph",
            }
        )
    if state == "STALLED":
        items.append(
            {
                "priority": "P0",
                "title": "Pipeline continuation stalled",
                "impact": "substrate phases waiting beyond safe window",
                "action": "inspect continuation waiting_on and async job health",
                "phase": "reconstruction",
            }
        )

    upstream_p0 = {i["phase"] for i in items if i["priority"] == "P0"}

    for card in phases:
        phase = str(card.get("phase") or "")
        status = str(card.get("status") or "")
        if status not in ("blocked", "degraded"):
            continue
        if phase == "graph" and "graph" in upstream_p0:
            continue
        if phase in ("retrieval", "synthesis") and upstream_p0:
            continue
        headline = str(card.get("headline") or phase)
        priority: AttentionPriority = "P1" if status == "blocked" else "P2"
        if phase == "canonical" and status in ("blocked", "degraded"):
            items.append(
                {
                    "priority": priority,
                    "title": f"Canonical topology pressure — {headline}",
                    "impact": "retry-ready deferrals not draining; 05→08 may starve",
                    "action": "inspect topology exhaustors and deferral queues",
                    "phase": phase,
                }
            )
        elif phase == "reconstruction" and walks_failed(card):
            items.append(
                {
                    "priority": "P1",
                    "title": "Traversal walk failures elevated",
                    "impact": "walk recurrence insufficient for retrieval epochs",
                    "action": "inspect failed walk records and OCTS worker schema/runtime",
                    "phase": phase,
                }
            )
        elif phase == "identity" and status == "degraded":
            items.append(
                {
                    "priority": "P2",
                    "title": "Identity replay conflicts",
                    "impact": "partial handle instability on graph frontier",
                    "action": "inspect open ambiguity records",
                    "phase": phase,
                }
            )
        elif phase == "ingestion" and status == "blocked":
            items.append(
                {
                    "priority": "P1",
                    "title": "Ingestion freshness gap",
                    "impact": "canonical topology pressure from missing parents",
                    "action": "run connector sync for stale sources",
                    "phase": phase,
                }
            )

    if continuity_status.get("canonical_lane") == "DEGRADED" and not any(
        i.get("phase") == "canonical" for i in items
    ):
        items.append(
            {
                "priority": "P1",
                "title": "Canonical lane degraded",
                "impact": "deferrals or topology wait limiting drain",
                "action": "inspect canonical deferral breakdown",
                "phase": "canonical",
            }
        )

    rank = {"P0": 0, "P1": 1, "P2": 2}
    items.sort(key=lambda x: (rank.get(str(x.get("priority")), 9), str(x.get("title"))))
    return items[:12]


def walks_failed(card: dict[str, Any]) -> bool:
    for sig in card.get("signals") or []:
        if sig.get("key") == "failed_retries":
            try:
                return int(str(sig.get("value") or "0")) > 0
            except ValueError:
                return False
    return False


def attention_items_to_legacy_lines(items: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for item in items:
        lines.append(
            f"[{item['priority']}] {item['title']} — Impact: {item['impact']} — Action: {item['action']}"
        )
    return lines


def build_continuity_overview_bundle_v1(
    session: Session,
    settings: Settings,
    *,
    tenant_id: uuid.UUID,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Returns (continuity_status, phases, attention_items, attention_lines)."""
    inspect = build_execution_inspect_v1(session, tenant_id=tenant_id, transition_limit=5)
    lease = inspect.get("lease") if isinstance(inspect.get("lease"), dict) else None
    progression = build_substrate_progression_status_v1(session, tenant_id=tenant_id)

    entity_count = count_active_org_entities_v1(session, tenant_id=tenant_id)
    linked = count_entities_with_promoted_edges_v1(session, tenant_id=tenant_id)
    propagation = evaluate_traversal_propagation_v1(
        session,
        tenant_id=tenant_id,
        linked_entity_count=linked,
        entity_count=entity_count,
        orphan_disconnected_count=max(0, entity_count - linked),
        orphan_identity_unresolved_count=0,
    )

    can_metrics = build_canonical_phase_summary_metrics_v1(session, tenant_id=tenant_id)
    continuity_status = build_continuity_status_v1(
        session,
        tenant_id=tenant_id,
        settings=settings,
        lease=lease,
        progression=progression,
        propagation=propagation,
        canonical_metrics=can_metrics,
    )
    phases = build_continuity_phase_cards_v1(
        session,
        settings,
        tenant_id=tenant_id,
        lease=lease,
        progression=progression,
    )
    attention_items = build_continuity_attention_items_v1(
        continuity_status=continuity_status,
        phases=phases,
        lease=lease,
        propagation=propagation,
    )
    return (
        continuity_status,
        phases,
        attention_items,
        attention_items_to_legacy_lines(attention_items),
    )
