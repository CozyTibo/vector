"""Celery tasks for Cortex substrate pipeline (phases 02–08)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
    PIPELINE_TRIGGER_POST_INGESTION,
)
from vector.domains.cortex.substrate_pipeline.orchestrator import (
    chain_after_phase_v1,
    enqueue_next_pipeline_phase_v1,
    finalize_pipeline_if_complete_v1,
    on_retrieval_publish_completed_for_pipeline_v1,
    start_substrate_pipeline_run_v1,
)
from vector.domains.cortex.substrate_pipeline.phase_runners import (
    run_phase_02_canonical_v1,
    run_phase_03_identity_v1,
    run_phase_04_graph_v1,
    run_phase_05_traversal_v1,
    run_phase_06_tcre_v1,
    run_phase_07_retrieval_v1,
    run_phase_08_synthesis_v1,
)
from vector.infrastructure.db.session import session_scope
from vector.settings import get_settings

_LOGGER = logging.getLogger("app")

_TASK_COORDINATOR = "vector.cortex.substrate_pipeline.coordinator"
_TASK_PHASE = "vector.cortex.substrate_pipeline.phase"
_TASK_PHASE_08 = "vector.cortex.substrate_pipeline.phase_08_synthesis"


@celery_app.task(name=_TASK_COORDINATOR, queue="vector")
def run_cortex_substrate_pipeline_coordinator_task(
    tenant_id: str,
    trigger_kind: str = PIPELINE_TRIGGER_POST_INGESTION,
    bundle_id: str | None = None,
    batch_limit: int | None = None,
    reason: str = "ingestion",
) -> dict[str, Any]:
    """Create durable pipeline run and enqueue phase 02 (canonical)."""
    tid = uuid.UUID(tenant_id)
    _LOGGER.info(
        "substrate_pipeline_coordinator_start tenant_id=%s trigger=%s reason=%s",
        tenant_id,
        trigger_kind,
        reason,
    )
    with session_scope() as session:
        run_id, created = start_substrate_pipeline_run_v1(
            session,
            tenant_id=tid,
            trigger_kind=trigger_kind,
            bundle_id=bundle_id,
            celery_root_task_id=run_cortex_substrate_pipeline_coordinator_task.request.id,
        )
        session.commit()
    chain = enqueue_next_pipeline_phase_v1(
        tenant_id=tid,
        pipeline_run_id=run_id,
        phase_id=PHASE_02_CANONICAL,
        bundle_id=bundle_id,
        batch_limit=batch_limit,
        identity_substrate_trigger=f"substrate_pipeline:{reason}",
    )
    return {
        "tenant_id": tenant_id,
        "pipeline_run_id": str(run_id),
        "created": created,
        "first_phase": chain,
    }


@celery_app.task(name=_TASK_PHASE, queue="vector", bind=True, max_retries=3)
def run_cortex_substrate_pipeline_phase_task(
    self,
    tenant_id: str,
    pipeline_run_id: str,
    phase_id: str,
    bundle_id: str | None = None,
    batch_limit: int | None = None,
    identity_substrate_trigger: str = "substrate_pipeline",
    graph_projection_stable_hash: str | None = None,
) -> dict[str, Any]:
    """Execute one substrate pipeline phase and chain to the next."""
    tid = uuid.UUID(tenant_id)
    prid = uuid.UUID(pipeline_run_id)
    settings = get_settings()
    _LOGGER.info(
        "substrate_pipeline_phase_start tenant_id=%s pipeline_run_id=%s phase=%s",
        tenant_id,
        pipeline_run_id,
        phase_id,
    )
    graph_hash = graph_projection_stable_hash
    with session_scope() as session:
        if phase_id == PHASE_02_CANONICAL:
            out = run_phase_02_canonical_v1(
                session,
                settings,
                tenant_id=tid,
                pipeline_run_id=prid,
                bundle_id=bundle_id,
                batch_limit=batch_limit,
            )
        elif phase_id == PHASE_03_IDENTITY:
            out = run_phase_03_identity_v1(
                session,
                tenant_id=tid,
                pipeline_run_id=prid,
                bundle_id=bundle_id,
                identity_substrate_trigger=identity_substrate_trigger,
            )
        elif phase_id == PHASE_04_GRAPH:
            out = run_phase_04_graph_v1(session, tenant_id=tid, pipeline_run_id=prid)
            graph_hash = out.get("graph_projection_stable_hash_sha256")
        elif phase_id == PHASE_05_TRAVERSAL:
            out = run_phase_05_traversal_v1(
                session,
                tenant_id=tid,
                pipeline_run_id=prid,
                graph_projection_stable_hash=graph_hash,
            )
        elif phase_id == PHASE_06_TCRE:
            out = run_phase_06_tcre_v1(session, tenant_id=tid, pipeline_run_id=prid)
            session.commit()
            return {
                "tenant_id": tenant_id,
                "pipeline_run_id": pipeline_run_id,
                "phase_id": phase_id,
                "output": out,
                "chained": False,
                "awaiting_tcre": True,
            }
        elif phase_id == PHASE_07_RETRIEVAL:
            out = run_phase_07_retrieval_v1(session, tenant_id=tid, pipeline_run_id=prid)
            session.commit()
            chain = on_retrieval_publish_completed_for_pipeline_v1(
                tenant_id=tid,
                pipeline_run_id=prid,
                published_index_epoch=out.get("published_index_epoch") or out.get("index_epoch"),
                bundle_id=bundle_id,
                batch_limit=batch_limit,
            )
            return {
                "tenant_id": tenant_id,
                "pipeline_run_id": pipeline_run_id,
                "phase_id": phase_id,
                "output": out,
                "chained": bool(chain.get("chained", True) if isinstance(chain, dict) else chain),
                "next_phase": chain,
            }
        elif phase_id == PHASE_08_SYNTHESIS:
            out = run_phase_08_synthesis_v1(session, tenant_id=tid, pipeline_run_id=prid)
            finalize_pipeline_if_complete_v1(session, pipeline_run_id=prid)
            session.commit()
            return {
                "tenant_id": tenant_id,
                "pipeline_run_id": pipeline_run_id,
                "phase_id": phase_id,
                "output": out,
                "chained": False,
                "pipeline_complete": True,
            }
        else:
            msg = f"unknown_phase:{phase_id}"
            raise ValueError(msg)
        session.commit()

    next_chain = chain_after_phase_v1(
        tenant_id=tid,
        pipeline_run_id=prid,
        completed_phase_id=phase_id,
        bundle_id=bundle_id,
        batch_limit=batch_limit,
        graph_projection_stable_hash=graph_hash,
        identity_substrate_trigger=identity_substrate_trigger,
    )
    return {
        "tenant_id": tenant_id,
        "pipeline_run_id": pipeline_run_id,
        "phase_id": phase_id,
        "output": out,
        "chained": next_chain is not None,
        "next_phase": next_chain,
    }


@celery_app.task(name=_TASK_PHASE_08, queue="vector", bind=True, max_retries=3)
def run_cortex_substrate_pipeline_phase_08_task(
    self,
    tenant_id: str,
    pipeline_run_id: str,
    published_index_epoch: str | None = None,
    bundle_id: str | None = None,
    batch_limit: int | None = None,
) -> dict[str, Any]:
    """Dedicated Celery entry for phase_08_synthesis (delegates to unified phase task)."""
    return run_cortex_substrate_pipeline_phase_task(
        self,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        phase_id=PHASE_08_SYNTHESIS,
        bundle_id=bundle_id,
        batch_limit=batch_limit,
    )
