"""Phase B step B5 — graph-hash trigger → walks → TCRE → phase 07 (no unlock scripts)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.execution.execution_event_triggers import (
    DETAIL_KEY_LAST_GRAPH_HASH_V1,
    EVENT_TRIGGER_GRAPH_HASH_V1,
    get_tenant_execution_lease_v1,
    resolve_live_graph_projection_hash_v1,
    trigger_graph_hash_walk_schedule_v1,
)
from vector.domains.cortex.lineage.artifact_lineage_graph import persist_lineage_edge_v1
from vector.domains.cortex.reasoning.runtime.reasoning_runtime_orchestrator import (
    create_reconstruction_job_v1,
    execute_tcre_reconstruction_job_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_STATUS_COMPLETED,
)
from vector.domains.cortex.substrate_pipeline.phase_runners import (
    run_phase_02_canonical_v1,
    run_phase_03_identity_v1,
    run_phase_04_graph_v1,
    run_phase_05_traversal_v1,
    run_phase_07_retrieval_v1,
)
from vector.domains.cortex.substrate_pipeline.phase05_walks_persisted_gate import (
    summarize_phase05_walk_output_v1,
)
from vector.domains.cortex.substrate_pipeline.phase_runner_receipt import (
    complete_async_phase_with_receipt_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import (
    begin_phase_v1,
    create_pipeline_run_v1,
    get_phase_run_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_phase_receipt import utc_now_iso_v1
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import CortexSubstratePhaseRun

GRAPH_HASH_AUTONOMOUS_CHAIN_SCHEMA_VERSION: Final[int] = 1
P0_B5_STEP: Final[str] = "step_b5_graph_hash_autonomous_chain"
CHAIN_LINK_GRAPH_HASH_V1: Final[str] = "graph_hash_trigger"
CHAIN_LINK_WALKS_V1: Final[str] = "walks"
CHAIN_LINK_TCRE_V1: Final[str] = "tcre"
CHAIN_LINK_RETRIEVAL_V1: Final[str] = "retrieval"


def is_graph_hash_autonomous_chain_enabled_v1() -> bool:
    try:
        from vector.settings import get_settings

        return bool(get_settings().cortex_graph_hash_autonomous_chain_enabled)
    except Exception:  # noqa: BLE001
        return True


def seed_stale_graph_hash_for_chain_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Force hash-change detection on next graph-hash trigger (proof / prod drive)."""
    live_hash = resolve_live_graph_projection_hash_v1(session, tenant_id=tenant_id)
    lease = get_tenant_execution_lease_v1(session, tenant_id=tenant_id)
    if lease is None or not live_hash:
        return {"seeded": False, "reason": "missing_lease_or_live_hash"}
    detail = dict(lease.detail_json or {})
    detail[DETAIL_KEY_LAST_GRAPH_HASH_V1] = "stale_hash_for_b5_chain_proof"
    lease.detail_json = detail
    session.flush()
    return {"seeded": True, "live_hash": live_hash}


def _execute_phase06_tcre_sync_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    primary_octs_walk_id: str | None,
) -> dict[str, Any]:
    scope: dict[str, Any] = {"substrate_pipeline_run_id": str(pipeline_run_id)}
    if primary_octs_walk_id:
        scope["octs_walk_id"] = str(primary_octs_walk_id)
    begin_phase_v1(session, pipeline_run_id=pipeline_run_id, phase_id=PHASE_06_TCRE)
    started_at = utc_now_iso_v1()
    job = create_reconstruction_job_v1(session, tenant_id=tenant_id, scope=scope)
    execute_tcre_reconstruction_job_v1(session, job)
    raw_output = {"job_id": str(job.id), "status": job.status, "sync": True, "ok": job.status == "completed"}
    complete_async_phase_with_receipt_v1(
        session,
        pipeline_run_id=pipeline_run_id,
        phase_id=PHASE_06_TCRE,
        tenant_id=tenant_id,
        raw_output=raw_output,
        started_at=started_at,
    )
    if job.status == "completed" and job.summary_json:
        chain_id = job.summary_json.get("causal_chain_id")
        if chain_id:
            persist_lineage_edge_v1(
                session,
                tenant_id=tenant_id,
                from_artifact_kind="tcre_chain",
                from_artifact_ref=str(chain_id),
                to_artifact_kind="retrieval_index",
                to_artifact_ref=f"pending:{pipeline_run_id}",
                edge_kind="tcre_binds_index",
                replay_identity=job.tcre_policy_bundle_digest,
            )
    return {
        "job_id": str(job.id),
        "status": str(job.status),
        "sync": True,
        "ok": job.status == "completed",
    }


def run_graph_hash_autonomous_chain_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID | None = None,
    bundle_id: str | None = None,
    run_upstream_phases: bool = True,
    force_graph_hash_schedule: bool = False,
) -> dict[str, Any]:
    """
    Run autonomous substrate chain 04→05→06(sync)→07 without unlock scripts.

    Phase 04 invokes ``trigger_graph_hash_walk_schedule_v1`` (P2-B); this module
    continues through walks, TCRE, and retrieval materialization on the same run.
    """
    if not is_graph_hash_autonomous_chain_enabled_v1():
        return {
            "chain_ok": False,
            "reason": "graph_hash_autonomous_chain_disabled",
            "chain_links": {},
        }

    if pipeline_run_id is None:
        run = create_pipeline_run_v1(
            session,
            tenant_id=tenant_id,
            trigger_kind="graph_hash_autonomous_chain_v1",
            bundle_id=bundle_id,
            idempotency_key=f"b5-chain-{tenant_id}-{uuid.uuid4().hex[:12]}",
        )
        pipeline_run_id = run.id
    prid = pipeline_run_id
    links: dict[str, Any] = {}
    phases: dict[str, Any] = {}

    if run_upstream_phases:
        from vector.settings import get_settings

        settings = get_settings()
        p2 = run_phase_02_canonical_v1(
            session,
            settings,
            tenant_id=tenant_id,
            pipeline_run_id=prid,
            bundle_id=bundle_id,
        )
        phases["phase_02"] = p2
        if p2.get("skipped"):
            return {
                "chain_ok": False,
                "reason": "canonical_skipped",
                "pipeline_run_id": str(prid),
                "phases": phases,
                "chain_links": links,
            }
        bid = p2.get("bundle_id") or bundle_id
        phases["phase_03"] = run_phase_03_identity_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=prid,
            bundle_id=bid,
            identity_substrate_trigger="graph_hash_autonomous_chain_v1",
        )

    p4 = run_phase_04_graph_v1(session, tenant_id=tenant_id, pipeline_run_id=prid)
    phases[PHASE_04_GRAPH] = p4
    graph_hash = str(p4.get("graph_projection_stable_hash_sha256") or "")
    trigger_out = dict(p4.get("event_trigger_graph_hash") or {})
    if force_graph_hash_schedule and graph_hash:
        trigger_out = trigger_graph_hash_walk_schedule_v1(
            session,
            tenant_id=tenant_id,
            graph_projection_stable_hash=graph_hash,
            pipeline_run_id=prid,
            force_schedule=True,
        )
        p4["event_trigger_graph_hash"] = trigger_out
    walk_schedule = dict(trigger_out.get("walk_schedule") or {})
    mat = dict(walk_schedule.get("materialization") or walk_schedule.get("pass", {}).get("materialization") or {})
    links[CHAIN_LINK_GRAPH_HASH_V1] = {
        "ok": bool(trigger_out.get("triggered")) or bool(trigger_out.get("walks_scheduled")),
        "hash_changed": bool(trigger_out.get("hash_changed")),
        "walks_scheduled": bool(trigger_out.get("walks_scheduled")),
        "trigger": EVENT_TRIGGER_GRAPH_HASH_V1,
    }

    p5 = run_phase_05_traversal_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=prid,
        graph_projection_stable_hash=graph_hash or None,
    )
    phases[PHASE_05_TRAVERSAL] = p5
    walk_summary = summarize_phase05_walk_output_v1(p5)
    primary_walk = p5.get("primary_octs_walk_id") or (
        (p5.get("walk_ids") or [None])[0] if p5.get("walk_ids") else None
    )
    links[CHAIN_LINK_WALKS_V1] = {
        "ok": walk_summary["walks_persisted"] > 0 or walk_summary["walks_available"] > 0,
        **walk_summary,
        "primary_octs_walk_id": primary_walk,
    }

    p6 = _execute_phase06_tcre_sync_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=prid,
        primary_octs_walk_id=str(primary_walk) if primary_walk else None,
    )
    phases[PHASE_06_TCRE] = p6
    links[CHAIN_LINK_TCRE_V1] = {
        "ok": bool(p6.get("ok")),
        "job_id": p6.get("job_id"),
        "status": p6.get("status"),
    }

    p7 = run_phase_07_retrieval_v1(session, tenant_id=tenant_id, pipeline_run_id=prid)
    phases[PHASE_07_RETRIEVAL] = p7
    links[CHAIN_LINK_RETRIEVAL_V1] = {
        "ok": bool(p7.get("ok"))
        or str(p7.get("build_state") or "") == "PUBLISHED"
        or int(p7.get("entries_materialized") or p7.get("entry_count") or 0) > 0,
        "published_index_epoch": p7.get("published_index_epoch"),
        "entries_materialized": int(p7.get("entries_materialized") or p7.get("entry_count") or 0),
    }

    chain_ok = all(bool(link.get("ok")) for link in links.values())
    return {
        "chain_ok": chain_ok,
        "pipeline_run_id": str(prid),
        "graph_projection_stable_hash_sha256": graph_hash or None,
        "phases": phases,
        "chain_links": links,
        "autonomous_chain_schema_version": GRAPH_HASH_AUTONOMOUS_CHAIN_SCHEMA_VERSION,
        "no_unlock_scripts": True,
    }


def _phase_output_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    phase_id: str,
) -> dict[str, Any]:
    row = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=phase_id)
    return dict(row.output_json or {}) if row is not None else {}


def find_graph_hash_chain_evidence_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    lookback_hours: int = 168,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Find pipeline runs in window that exhibit graph-hash → walks → TCRE → retrieval."""
    cutoff = datetime.now(UTC) - timedelta(hours=lookback_hours)
    p07_rows = list(
        session.scalars(
            select(CortexSubstratePhaseRun)
            .where(
                CortexSubstratePhaseRun.tenant_id == tenant_id,
                CortexSubstratePhaseRun.phase_id == PHASE_07_RETRIEVAL,
                CortexSubstratePhaseRun.status == PHASE_STATUS_COMPLETED,
            )
            .order_by(CortexSubstratePhaseRun.completed_at.desc().nullslast())
            .limit(limit * 3)
        ).all()
    )
    evidence: list[dict[str, Any]] = []
    for p07 in p07_rows:
        if p07.completed_at is not None and p07.completed_at < cutoff:
            continue
        prid = p07.pipeline_run_id
        p04 = _phase_output_v1(session, pipeline_run_id=prid, phase_id=PHASE_04_GRAPH)
        p05 = _phase_output_v1(session, pipeline_run_id=prid, phase_id=PHASE_05_TRAVERSAL)
        p06 = _phase_output_v1(session, pipeline_run_id=prid, phase_id=PHASE_06_TCRE)
        trigger = dict(p04.get("event_trigger_graph_hash") or {})
        walks = summarize_phase05_walk_output_v1(p05)
        has_trigger = bool(trigger.get("triggered")) or bool(trigger.get("walks_scheduled"))
        has_walks = walks["walks_persisted"] > 0 or walks["walks_available"] > 0
        has_tcre = bool(p06.get("job_id"))
        has_retrieval = bool(
            p07.output_json.get("published_index_epoch")
            or int(p07.output_json.get("entries_materialized") or p07.output_json.get("entry_count") or 0)
            > 0
        )
        chain_ok = has_trigger and has_walks and has_tcre and has_retrieval
        evidence.append(
            {
                "pipeline_run_id": str(prid),
                "completed_at": p07.completed_at.isoformat() if p07.completed_at else None,
                "chain_ok": chain_ok,
                "graph_hash_triggered": has_trigger,
                "walks_ok": has_walks,
                "tcre_ok": has_tcre,
                "retrieval_ok": has_retrieval,
                "published_index_epoch": p07.output_json.get("published_index_epoch"),
            }
        )
        if len(evidence) >= limit:
            break
    return evidence
