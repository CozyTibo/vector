"""Single authoritative tenant execution worker — substrate phases under durable lease + FSM."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform
from vector.domains.cortex.execution.enqueue import enqueue_tenant_convergence_v1
from vector.domains.cortex.execution.execution_path_telemetry import (
    EXECUTION_PATH_CONVERGENCE,
    emit_execution_path_telemetry_v1,
)
from vector.domains.cortex.execution.dual_lane_lease import (
    is_execution_dual_lane_enabled_v1,
    should_mark_execution_lane_stalled_v1,
    sync_dual_lane_fields_on_lease_v1,
)
from vector.domains.cortex.execution.dual_lane_worker import run_dual_lane_convergence_v1
from vector.domains.cortex.execution.lease import (
    complete_convergence_lease_v1,
    mark_tenant_stalled_v1,
    schedule_convergence_retry_v1,
    try_acquire_convergence_lease_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PIPELINE_TRIGGER_POST_INGESTION,
)
from vector.domains.cortex.substrate_pipeline.orchestrator import start_substrate_pipeline_run_v1
from vector.settings import Settings, get_settings

_LOGGER = logging.getLogger(__name__)

SERIAL_FALLBACK_REMOVED_CODE_V1 = "execution_serial_fallback_removed_s5_1"


class ExecutionSerialFallbackRemovedError(RuntimeError):
    """Raised when ``CORTEX_EXECUTION_DUAL_LANE=0`` (serial path removed in S5.1)."""

    def __init__(self) -> None:
        super().__init__(SERIAL_FALLBACK_REMOVED_CODE_V1)


def run_tenant_convergence_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    settings: Settings | None = None,
    reason: str = "worker",
    celery_task_id: str | None = None,
) -> dict[str, Any]:
    """Execute one execution slice for a tenant; self-requeue when incomplete."""
    cfg = settings or get_settings()
    started = time.monotonic()

    lease, block_reason = try_acquire_convergence_lease_v1(session, tenant_id=tenant_id, settings=cfg)
    if lease is None:
        return {"tenant_id": str(tenant_id), "acquired": False, "reason": block_reason}

    emit_execution_path_telemetry_v1(
        tenant_id=tenant_id,
        execution_path=EXECUTION_PATH_CONVERGENCE,
        trigger=f"execution_slice:{reason}",
        pipeline_run_id=lease.pipeline_run_id,
        celery_task_id=celery_task_id,
        detail={
            "phase_cursor": lease.phase_cursor,
            "lease_status": lease.status,
            "fsm_state": lease.fsm_state,
        },
    )

    pipeline_run_id: uuid.UUID | None = lease.pipeline_run_id

    try:
        if pipeline_run_id is None:
            pipeline_run_id, _created = start_substrate_pipeline_run_v1(
                session,
                tenant_id=tenant_id,
                trigger_kind=PIPELINE_TRIGGER_POST_INGESTION,
                bundle_id=None,
                celery_root_task_id=celery_task_id,
            )
            lease.pipeline_run_id = pipeline_run_id
            session.flush()

        bundle_id = resolve_default_bundle_id_for_stub_transform(session, tenant_id)
        if bundle_id is not None:
            from vector.domains.cortex.operational_runtime.graph_density_promotion import (
                schedule_graph_density_promotion_on_convergence_worker_v1,
            )

            schedule_graph_density_promotion_on_convergence_worker_v1(
                session,
                tenant_id=tenant_id,
                convergence_reason=reason,
            )
        if bundle_id is None:
            complete_convergence_lease_v1(session, lease=lease, pipeline_run_id=pipeline_run_id)
            session.commit()
            return {
                "tenant_id": str(tenant_id),
                "acquired": True,
                "outcome": "no_transformable_bundle",
                "fsm_state": lease.fsm_state,
            }

        if is_execution_dual_lane_enabled_v1():
            return run_dual_lane_convergence_v1(
                session,
                tenant_id=tenant_id,
                lease=lease,
                pipeline_run_id=pipeline_run_id,
                bundle_id=bundle_id,
                cfg=cfg,
                started=started,
                reason=reason,
                celery_task_id=celery_task_id,
            )

        raise ExecutionSerialFallbackRemovedError()

    except ExecutionSerialFallbackRemovedError:
        mark_tenant_stalled_v1(
            session,
            tenant_id=tenant_id,
            error=SERIAL_FALLBACK_REMOVED_CODE_V1,
        )
        session.commit()
        return {
            "tenant_id": str(tenant_id),
            "acquired": True,
            "outcome": "serial_fallback_removed",
            "error_code": SERIAL_FALLBACK_REMOVED_CODE_V1,
            "rollback": "set CORTEX_EXECUTION_DUAL_LANE=1",
        }
    except Exception as exc:  # noqa: BLE001
        if should_mark_execution_lane_stalled_v1(lease):
            mark_tenant_stalled_v1(session, tenant_id=tenant_id, error=str(exc))
        else:
            schedule_convergence_retry_v1(
                session,
                tenant_id=tenant_id,
                phase_cursor=PHASE_02_CANONICAL,
                last_error=str(exc)[:500],
            )
            sync_dual_lane_fields_on_lease_v1(session, lease=lease)
        session.commit()
        enqueue_tenant_convergence_v1(tenant_id, reason="stalled_retry")
        _LOGGER.exception(
            "execution_worker_failed tenant_id=%s pipeline_run_id=%s",
            tenant_id,
            pipeline_run_id,
        )
        raise


run_tenant_execution_v1 = run_tenant_convergence_v1
