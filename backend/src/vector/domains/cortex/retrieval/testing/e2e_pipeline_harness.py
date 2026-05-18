"""Sync substrate pipeline runner for E2E tests (real orchestration, no row injection)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.lineage.artifact_lineage_graph import persist_lineage_edge_v1
from vector.domains.cortex.reasoning.runtime.reasoning_runtime_orchestrator import (
    create_reconstruction_job_v1,
    execute_tcre_reconstruction_job_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
)
from vector.domains.cortex.substrate_pipeline.phase_runners import (
    run_phase_02_canonical_v1,
    run_phase_03_identity_v1,
    run_phase_04_graph_v1,
    run_phase_05_traversal_v1,
    run_phase_07_retrieval_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import (
    begin_phase_v1,
    complete_phase_v1,
    create_pipeline_run_v1,
)
from vector.settings import get_settings


def run_substrate_pipeline_sync_through_retrieval_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    bundle_id: str | None = None,
    batch_limit: int | None = None,
) -> dict[str, Any]:
    """Run phases 02–07 synchronously in-process (TCRE executed sync, not Celery)."""
    settings = get_settings()
    run = create_pipeline_run_v1(
        session,
        tenant_id=tenant_id,
        trigger_kind="e2e_test",
        bundle_id=bundle_id,
        idempotency_key=f"e2e-{tenant_id}-{uuid.uuid4().hex[:8]}",
    )
    prid = run.id
    out: dict[str, Any] = {"pipeline_run_id": str(prid), "phases": {}}

    p2 = run_phase_02_canonical_v1(
        session,
        settings,
        tenant_id=tenant_id,
        pipeline_run_id=prid,
        bundle_id=bundle_id,
        batch_limit=batch_limit,
    )
    out["phases"][PHASE_02_CANONICAL] = p2
    if p2.get("skipped"):
        return {**out, "skipped": True, "reason": p2.get("reason")}

    out["phases"][PHASE_03_IDENTITY] = run_phase_03_identity_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=prid,
        bundle_id=p2.get("bundle_id") or bundle_id,
        identity_substrate_trigger="e2e_pipeline",
    )
    p4 = run_phase_04_graph_v1(session, tenant_id=tenant_id, pipeline_run_id=prid)
    out["phases"][PHASE_04_GRAPH] = p4

    p5 = run_phase_05_traversal_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=prid,
        graph_projection_stable_hash=p4.get("graph_projection_stable_hash_sha256"),
    )
    out["phases"][PHASE_05_TRAVERSAL] = p5

    begin_phase_v1(session, pipeline_run_id=prid, phase_id=PHASE_06_TCRE)
    walk_id = p5.get("primary_octs_walk_id")
    scope: dict[str, Any] = {"substrate_pipeline_run_id": str(prid)}
    if walk_id:
        scope["octs_walk_id"] = str(walk_id)
    job = create_reconstruction_job_v1(session, tenant_id=tenant_id, scope=scope)
    execute_tcre_reconstruction_job_v1(session, job)
    complete_phase_v1(
        session,
        pipeline_run_id=prid,
        phase_id=PHASE_06_TCRE,
        output={"job_id": str(job.id), "status": job.status, "sync": True},
    )
    out["phases"][PHASE_06_TCRE] = {"job_id": str(job.id), "status": job.status}

    if job.status == "completed" and job.summary_json:
        chain_id = job.summary_json.get("causal_chain_id")
        if chain_id:
            persist_lineage_edge_v1(
                session,
                tenant_id=tenant_id,
                from_artifact_kind="tcre_chain",
                from_artifact_ref=str(chain_id),
                to_artifact_kind="retrieval_index",
                to_artifact_ref=f"pending:{prid}",
                edge_kind="tcre_binds_index",
                replay_identity=job.tcre_policy_bundle_digest,
            )

    p7 = run_phase_07_retrieval_v1(session, tenant_id=tenant_id, pipeline_run_id=prid)
    out["phases"][PHASE_07_RETRIEVAL] = p7
    out["index_epoch"] = p7.get("index_epoch")
    out["build_state"] = p7.get("build_state")
    return out
