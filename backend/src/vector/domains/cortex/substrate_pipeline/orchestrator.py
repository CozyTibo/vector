"""Substrate pipeline scheduling and Celery phase chaining."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_03_IDENTITY,
    PHASE_04_GRAPH,
    PHASE_05_TRAVERSAL,
    PHASE_06_TCRE,
    PHASE_07_RETRIEVAL,
    PIPELINE_TRIGGER_FLUSH_RERUN,
    PIPELINE_TRIGGER_POST_INGESTION,
)
from vector.domains.cortex.substrate_pipeline.repository import (
    compute_pipeline_idempotency_key_v1,
    create_pipeline_run_v1,
    finalize_pipeline_run_v1,
    get_running_pipeline_run_v1,
)
from vector.settings import Settings, get_settings

_LOGGER = logging.getLogger(__name__)

_PIPELINE_TASK_PREFIX = "cortex-substrate-pipeline-"


def substrate_pipeline_celery_task_id(tenant_id: uuid.UUID | str) -> str:
    return f"{_PIPELINE_TASK_PREFIX}{tenant_id}"


def schedule_substrate_pipeline_v1(
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
    trigger_kind: str = PIPELINE_TRIGGER_POST_INGESTION,
    bundle_id: str | None = None,
    batch_limit: int | None = None,
    reason: str = "ingestion",
) -> dict[str, Any]:
    """Debounce and enqueue full substrate pipeline (phases 02–07) for one tenant."""
    cfg = settings or get_settings()
    if not cfg.cortex_post_ingestion_substrate_refresh_enabled:
        return {"scheduled": False, "reason": "disabled"}

    debounce = max(30, int(cfg.cortex_post_ingestion_substrate_refresh_debounce_seconds))
    task_id = substrate_pipeline_celery_task_id(tenant_id)

    from app.celery_app import celery_app
    from app.tasks.cortex_substrate_pipeline import run_cortex_substrate_pipeline_coordinator_task

    try:
        celery_app.control.revoke(task_id, terminate=False)
    except Exception:  # noqa: BLE001
        pass

    async_result = run_cortex_substrate_pipeline_coordinator_task.apply_async(
        kwargs={
            "tenant_id": str(tenant_id),
            "trigger_kind": trigger_kind,
            "bundle_id": bundle_id,
            "batch_limit": batch_limit,
            "reason": reason,
        },
        queue="vector",
        countdown=debounce,
        task_id=task_id,
    )
    _LOGGER.info(
        "substrate_pipeline_scheduled tenant_id=%s trigger=%s countdown_s=%s",
        tenant_id,
        trigger_kind,
        debounce,
    )
    return {
        "scheduled": True,
        "reason": reason,
        "trigger_kind": trigger_kind,
        "task_id": task_id,
        "celery_task_id": str(async_result.id),
        "countdown_seconds": debounce,
    }


def start_substrate_pipeline_run_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    trigger_kind: str,
    bundle_id: str | None,
    celery_root_task_id: str | None = None,
) -> tuple[uuid.UUID, bool]:
    """Create or reuse a running pipeline run. Returns (run_id, created)."""
    existing = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    if existing is not None:
        return existing.id, False
    idem = compute_pipeline_idempotency_key_v1(
        tenant_id=tenant_id,
        trigger_kind=trigger_kind,
    )
    run = create_pipeline_run_v1(
        session,
        tenant_id=tenant_id,
        trigger_kind=trigger_kind,
        bundle_id=bundle_id,
        idempotency_key=idem,
        celery_root_task_id=celery_root_task_id,
    )
    session.flush()
    return run.id, True


def enqueue_next_pipeline_phase_v1(
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    phase_id: str,
    bundle_id: str | None = None,
    batch_limit: int | None = None,
    graph_projection_stable_hash: str | None = None,
    identity_substrate_trigger: str = "substrate_pipeline",
) -> dict[str, Any]:
    from app.tasks.cortex_substrate_pipeline import (
        run_cortex_substrate_pipeline_phase_task,
    )

    kwargs: dict[str, Any] = {
        "tenant_id": str(tenant_id),
        "pipeline_run_id": str(pipeline_run_id),
        "phase_id": phase_id,
        "bundle_id": bundle_id,
        "batch_limit": batch_limit,
        "identity_substrate_trigger": identity_substrate_trigger,
        "graph_projection_stable_hash": graph_projection_stable_hash,
    }
    async_result = run_cortex_substrate_pipeline_phase_task.apply_async(
        kwargs=kwargs,
        queue="vector",
    )
    return {"phase_id": phase_id, "celery_task_id": str(async_result.id)}


def chain_after_phase_v1(
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    completed_phase_id: str,
    bundle_id: str | None = None,
    batch_limit: int | None = None,
    graph_projection_stable_hash: str | None = None,
    identity_substrate_trigger: str = "substrate_pipeline",
) -> dict[str, Any] | None:
    """Enqueue the next phase after ``completed_phase_id`` completes."""
    order = [
        PHASE_02_CANONICAL,
        PHASE_03_IDENTITY,
        PHASE_04_GRAPH,
        PHASE_05_TRAVERSAL,
        PHASE_06_TCRE,
        PHASE_07_RETRIEVAL,
    ]
    try:
        idx = order.index(completed_phase_id)
    except ValueError:
        return None
    if idx + 1 >= len(order):
        return None
    next_phase = order[idx + 1]
    if completed_phase_id == PHASE_06_TCRE:
        return None
    return enqueue_next_pipeline_phase_v1(
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        phase_id=next_phase,
        bundle_id=bundle_id,
        batch_limit=batch_limit,
        graph_projection_stable_hash=graph_projection_stable_hash,
        identity_substrate_trigger=identity_substrate_trigger,
    )


def on_tcre_job_completed_for_pipeline_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_scope: dict[str, Any],
) -> dict[str, Any] | None:
    """When TCRE completes with pipeline scope, enqueue phase 07 retrieval."""
    run_id_raw = job_scope.get("substrate_pipeline_run_id")
    if not run_id_raw:
        return None
    try:
        pipeline_run_id = uuid.UUID(str(run_id_raw))
    except ValueError:
        return None
    return enqueue_next_pipeline_phase_v1(
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        phase_id=PHASE_07_RETRIEVAL,
    )


def finalize_pipeline_if_complete_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
) -> dict[str, Any]:
    from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1
    from vector.domains.cortex.substrate_pipeline.constants import PHASE_STATUS_COMPLETED, PHASE_STATUS_SKIPPED

    phases = [
        PHASE_02_CANONICAL,
        PHASE_03_IDENTITY,
        PHASE_04_GRAPH,
        PHASE_05_TRAVERSAL,
        PHASE_06_TCRE,
        PHASE_07_RETRIEVAL,
    ]
    for pid in phases:
        pr = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=pid)
        if pr is None or pr.status not in (PHASE_STATUS_COMPLETED, PHASE_STATUS_SKIPPED):
            return {"finalized": False, "waiting_on": pid}
    run = finalize_pipeline_run_v1(session, pipeline_run_id=pipeline_run_id)
    return {"finalized": True, "pipeline_status": run.status}
