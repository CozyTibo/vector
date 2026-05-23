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
    PHASE_08_SYNTHESIS,
    PIPELINE_TRIGGER_FLUSH_RERUN,
    PIPELINE_TRIGGER_POST_INGESTION,
    SUBSTRATE_PIPELINE_PHASE_ORDER,
)
from vector.domains.cortex.substrate_pipeline.repository import (
    compute_pipeline_idempotency_key_v1,
    create_pipeline_run_v1,
    finalize_pipeline_run_v1,
    get_running_pipeline_run_v1,
)
from vector.infrastructure.db.session import session_scope
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
    """Mark tenant dirty and enqueue convergence (compat wrapper over unified dispatch)."""
    from vector.domains.cortex.execution.convergence_dispatch import (
        mark_dirty_and_enqueue_convergence_v1,
    )

    cfg = settings or get_settings()
    if not cfg.cortex_post_ingestion_substrate_refresh_enabled:
        return {"scheduled": False, "reason": "disabled"}

    from vector.domains.cortex.operational_runtime.substrate_runtime_economics import (
        evaluate_pipeline_concurrency_v1,
    )
    from vector.domains.cortex.canonical.transform_runtime import (
        resolve_default_bundle_id_for_stub_transform,
    )

    with session_scope() as session:
        concurrency = evaluate_pipeline_concurrency_v1(session, tenant_id=tenant_id)
        if not concurrency.get("may_start_pipeline"):
            return {
                "scheduled": False,
                "reason": concurrency.get("block_reason") or "pipeline_concurrency_blocked",
                "pipeline_concurrency": concurrency,
            }
        if bundle_id is None:
            resolved_bundle = resolve_default_bundle_id_for_stub_transform(session, tenant_id)
            if resolved_bundle is None:
                _LOGGER.warning(
                    "substrate_pipeline_schedule_blocked tenant_id=%s reason=no_transformable_bundle",
                    tenant_id,
                )
                return {
                    "scheduled": False,
                    "reason": "no_transformable_bundle",
                }

    schedule_reason = f"{trigger_kind}:{reason}"
    out = mark_dirty_and_enqueue_convergence_v1(
        tenant_id=tenant_id,
        settings=cfg,
        reason=schedule_reason,
        telemetry_trigger=f"schedule_substrate_pipeline:{trigger_kind}",
    )
    if out.get("scheduled"):
        out = {
            **out,
            "coalesced": False,
            "trigger_kind": trigger_kind,
            "task_id": substrate_pipeline_celery_task_id(tenant_id),
        }
    return out


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
    """Admin/recovery-only: enqueue execution slice at ``phase_id`` (sole motion path; D5/M6)."""
    del bundle_id, batch_limit, graph_projection_stable_hash, identity_substrate_trigger
    from vector.domains.cortex.execution.enqueue import enqueue_execution_slice_at_phase_v1

    return enqueue_execution_slice_at_phase_v1(
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        phase_cursor=phase_id,
        reason="admin_recovery_execution_slice",
    )


def on_retrieval_publish_completed_for_pipeline_v1(
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    published_index_epoch: str | None = None,
    bundle_id: str | None = None,
    batch_limit: int | None = None,
) -> dict[str, Any]:
    """Chain phase 08 synthesis after phase 07 publish (**PIPE-08-01**, **G-P085-SYN-01**)."""
    from vector.domains.cortex.operational_runtime.substrate_synthesis_activation_scheduling import (
        chain_synthesis_activation_after_phase07_v1,
    )

    with session_scope() as session:
        out = chain_synthesis_activation_after_phase07_v1(
            session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
            published_index_epoch=published_index_epoch,
            bundle_id=bundle_id,
            batch_limit=batch_limit,
        )
        session.commit()
    return out


def on_tcre_job_completed_for_pipeline_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    job_scope: dict[str, Any],
    tcre_job_id: uuid.UUID | None = None,
    tcre_job_status: str = "completed",
) -> dict[str, Any] | None:
    """When TCRE completes with pipeline scope, resume phase 07 via execution lease only."""
    run_id_raw = job_scope.get("substrate_pipeline_run_id")
    if not run_id_raw:
        return None
    try:
        pipeline_run_id = uuid.UUID(str(run_id_raw))
    except ValueError:
        return None
    from vector.domains.cortex.operational_runtime.substrate_autonomous_progression import (
        assert_tcre_completion_uses_resume_path_v1,
    )

    assert_tcre_completion_uses_resume_path_v1(
        has_tcre_job_id=tcre_job_id is not None,
        pipeline_scope=True,
    )
    if tcre_job_id is None:
        return None

    from vector.domains.cortex.execution.tcre_resume import on_tcre_job_terminal_for_execution_v1

    return on_tcre_job_terminal_for_execution_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        tcre_job_id=tcre_job_id,
        tcre_job_status=tcre_job_status,
    )


def finalize_pipeline_if_complete_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
) -> dict[str, Any]:
    from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1
    from vector.domains.cortex.substrate_pipeline.constants import (
        PHASE_STATUS_COMPLETED,
        PHASE_STATUS_SKIPPED,
        PHASE_STATUS_WAITING,
    )

    phases = list(SUBSTRATE_PIPELINE_PHASE_ORDER)
    for pid in phases:
        pr = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=pid)
        if pr is None:
            return {"finalized": False, "waiting_on": pid}
        if pr.status == PHASE_STATUS_WAITING:
            return {"finalized": False, "waiting_on": pid, "waiting_reason": pr.error_detail}
        if pr.status not in (PHASE_STATUS_COMPLETED, PHASE_STATUS_SKIPPED):
            return {"finalized": False, "waiting_on": pid}
    run = finalize_pipeline_run_v1(session, pipeline_run_id=pipeline_run_id)
    return {"finalized": True, "pipeline_status": run.status}
