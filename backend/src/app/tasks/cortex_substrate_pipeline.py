"""Legacy substrate pipeline Celery tasks (M6: admin break-glass only; no phase chaining)."""

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
from vector.domains.cortex.execution.execution_path_telemetry import (
    EXECUTION_PATH_LEGACY,
    emit_execution_path_telemetry_v1,
)
from vector.domains.cortex.substrate_pipeline.canonical_phase_gate import (
    evaluate_legacy_canonical_chain_gate_v1,
)
from vector.domains.cortex.substrate_pipeline.orchestrator import (
    finalize_pipeline_if_complete_v1,
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
    """Deprecated (M4/M6): mark dirty and enqueue execution slice instead of phase chain."""
    tid = uuid.UUID(tenant_id)
    _LOGGER.warning(
        "DEPRECATED substrate_pipeline_coordinator tenant_id=%s (M6: use execution slice)",
        tenant_id,
    )
    from vector.infrastructure.cortex_substrate_pipeline_schedule import (
        clear_substrate_pipeline_schedule_anchor_v1,
    )
    from vector.domains.cortex.execution.enqueue import enqueue_execution_slice_at_phase_v1
    from vector.domains.cortex.execution.lease import mark_tenant_dirty_v1

    clear_substrate_pipeline_schedule_anchor_v1(tid)
    emit_execution_path_telemetry_v1(
        tenant_id=tid,
        execution_path=EXECUTION_PATH_LEGACY,
        trigger=f"substrate_pipeline_coordinator:{trigger_kind}",
        celery_task_id=str(run_cortex_substrate_pipeline_coordinator_task.request.id),
        detail={"reason": reason, "deprecated": True},
    )
    with session_scope() as session:
        run_id, created = start_substrate_pipeline_run_v1(
            session,
            tenant_id=tid,
            trigger_kind=trigger_kind,
            bundle_id=bundle_id,
            celery_root_task_id=run_cortex_substrate_pipeline_coordinator_task.request.id,
        )
        mark_tenant_dirty_v1(session, tenant_id=tid, reason=f"coordinator_break_glass:{reason}")
        session.commit()
    hint = enqueue_execution_slice_at_phase_v1(
        tenant_id=tid,
        pipeline_run_id=run_id,
        phase_cursor=PHASE_02_CANONICAL,
        reason="coordinator_break_glass",
    )
    return {
        "tenant_id": tenant_id,
        "pipeline_run_id": str(run_id),
        "created": created,
        "deprecated": True,
        "execution_enqueue": hint,
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
    """Deprecated (M6): run a single phase inline; never chains — use execution slice."""
    tid = uuid.UUID(tenant_id)
    prid = uuid.UUID(pipeline_run_id)
    settings = get_settings()
    _LOGGER.warning(
        "DEPRECATED substrate_pipeline_phase_task tenant_id=%s phase=%s (M6: use execution slice)",
        tenant_id,
        phase_id,
    )
    emit_execution_path_telemetry_v1(
        tenant_id=tid,
        execution_path=EXECUTION_PATH_LEGACY,
        trigger=f"substrate_pipeline_phase_deprecated:{phase_id}",
        pipeline_run_id=prid,
        phase_id=phase_id,
        celery_task_id=str(self.request.id),
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
            chain_gate = evaluate_legacy_canonical_chain_gate_v1(
                session,
                tenant_id=tid,
                pipeline_run_id=prid,
                phase_output=out,
                gate_enabled=settings.cortex_substrate_pipeline_canonical_chain_gate_enabled,
            )
            session.commit()
            may_continue = bool(chain_gate and chain_gate.get("may_chain"))
            return {
                "tenant_id": tenant_id,
                "pipeline_run_id": pipeline_run_id,
                "phase_id": phase_id,
                "output": out,
                "chained": False,
                "deprecated": True,
                "canonical_chain_gate": chain_gate,
                "hint": "enqueue_execution_slice" if may_continue else "blocked",
            }
        if phase_id == PHASE_03_IDENTITY:
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
                "deprecated": True,
            }
        elif phase_id == PHASE_07_RETRIEVAL:
            out = run_phase_07_retrieval_v1(session, tenant_id=tid, pipeline_run_id=prid)
            session.commit()
            return {
                "tenant_id": tenant_id,
                "pipeline_run_id": pipeline_run_id,
                "phase_id": phase_id,
                "output": out,
                "chained": False,
                "deprecated": True,
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
                "deprecated": True,
            }
        else:
            msg = f"unknown_phase:{phase_id}"
            raise ValueError(msg)
        session.commit()

    return {
        "tenant_id": tenant_id,
        "pipeline_run_id": pipeline_run_id,
        "phase_id": phase_id,
        "output": out,
        "chained": False,
        "deprecated": True,
        "hint": "enqueue_execution_slice_for_continuation",
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
    """Deprecated phase 08 entry — delegates to unified deprecated phase task."""
    del published_index_epoch
    return run_cortex_substrate_pipeline_phase_task(
        self,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        phase_id=PHASE_08_SYNTHESIS,
        bundle_id=bundle_id,
        batch_limit=batch_limit,
    )
