"""Durable substrate pipeline run + phase state."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_STATUS_COMPLETED,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_QUEUED,
    PHASE_STATUS_RUNNING,
    PHASE_STATUS_SKIPPED,
    PIPELINE_STATUS_COMPLETED,
    PIPELINE_STATUS_FAILED,
    PIPELINE_STATUS_PARTIAL,
    PIPELINE_STATUS_QUEUED,
    PIPELINE_STATUS_RUNNING,
    SUBSTRATE_PIPELINE_PHASE_ORDER,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
    CortexSubstratePhaseRun,
    CortexSubstratePipelineRun,
)


def derive_substrate_pipeline_replay_identity_v1(
    *,
    tenant_id: uuid.UUID,
    trigger_kind: str,
    bundle_id: str | None,
) -> str:
    from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
        hash_reasoning_canonical_json_sha256_v1,
    )

    return hash_reasoning_canonical_json_sha256_v1(
        {
            "tenant_id": str(tenant_id),
            "trigger_kind": trigger_kind,
            "bundle_id": bundle_id or "",
            "purpose": "substrate_pipeline_v1",
        }
    )


def compute_pipeline_idempotency_key_v1(
    *,
    tenant_id: uuid.UUID,
    trigger_kind: str,
    ingestion_epoch: str | None = None,
) -> str:
    from vector.domains.cortex.reasoning.reasoning_receipts_proof_artifacts import (
        hash_reasoning_canonical_json_sha256_v1,
    )

    return hash_reasoning_canonical_json_sha256_v1(
        {
            "tenant_id": str(tenant_id),
            "trigger_kind": trigger_kind,
            "ingestion_epoch": ingestion_epoch or "live",
        }
    )[:64]


def get_running_pipeline_run_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> CortexSubstratePipelineRun | None:
    return session.scalar(
        select(CortexSubstratePipelineRun)
        .where(
            CortexSubstratePipelineRun.tenant_id == tenant_id,
            CortexSubstratePipelineRun.status == PIPELINE_STATUS_RUNNING,
        )
        .order_by(CortexSubstratePipelineRun.created_at.desc())
        .limit(1)
    )


def create_pipeline_run_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    trigger_kind: str,
    bundle_id: str | None,
    idempotency_key: str,
    celery_root_task_id: str | None = None,
) -> CortexSubstratePipelineRun:
    existing = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    if existing is not None:
        return existing

    run = CortexSubstratePipelineRun(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        trigger_kind=trigger_kind,
        status=PIPELINE_STATUS_QUEUED,
        bundle_id=bundle_id,
        idempotency_key=idempotency_key,
        current_phase_id=None,
        summary_json={},
        celery_root_task_id=celery_root_task_id,
    )
    session.add(run)
    for ordinal, phase_id in enumerate(SUBSTRATE_PIPELINE_PHASE_ORDER):
        session.add(
            CortexSubstratePhaseRun(
                id=uuid.uuid4(),
                pipeline_run_id=run.id,
                tenant_id=tenant_id,
                phase_id=phase_id,
                phase_ordinal=ordinal,
                status=PHASE_STATUS_QUEUED,
                attempt=0,
                output_json={},
            )
        )
    session.flush()
    return run


def get_phase_run_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    phase_id: str,
) -> CortexSubstratePhaseRun | None:
    return session.scalar(
        select(CortexSubstratePhaseRun).where(
            CortexSubstratePhaseRun.pipeline_run_id == pipeline_run_id,
            CortexSubstratePhaseRun.phase_id == phase_id,
        )
    )


def mark_pipeline_running_v1(session: Session, run: CortexSubstratePipelineRun) -> None:
    if run.status == PIPELINE_STATUS_QUEUED:
        run.status = PIPELINE_STATUS_RUNNING
        run.started_at = datetime.now(UTC)
    session.flush()


def begin_phase_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    phase_id: str,
    celery_task_id: str | None = None,
) -> CortexSubstratePhaseRun:
    phase = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=phase_id)
    if phase is None:
        msg = f"unknown_phase:{phase_id}"
        raise ValueError(msg)
    run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
    if run is None:
        msg = "pipeline_run_not_found"
        raise ValueError(msg)
    mark_pipeline_running_v1(session, run)
    run.current_phase_id = phase_id
    phase.status = PHASE_STATUS_RUNNING
    phase.attempt = int(phase.attempt or 0) + 1
    phase.started_at = datetime.now(UTC)
    phase.celery_task_id = celery_task_id
    phase.error_detail = None
    session.flush()
    return phase


def complete_phase_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    phase_id: str,
    output: dict[str, Any],
) -> CortexSubstratePhaseRun:
    phase = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=phase_id)
    if phase is None:
        msg = f"unknown_phase:{phase_id}"
        raise ValueError(msg)
    phase.status = PHASE_STATUS_COMPLETED
    phase.output_json = dict(output)
    phase.completed_at = datetime.now(UTC)
    phase.error_detail = None
    session.flush()
    return phase


def fail_phase_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    phase_id: str,
    error: str,
    output: dict[str, Any] | None = None,
) -> CortexSubstratePhaseRun:
    phase = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=phase_id)
    if phase is None:
        msg = f"unknown_phase:{phase_id}"
        raise ValueError(msg)
    phase.status = PHASE_STATUS_FAILED
    phase.error_detail = error[:4000]
    if output:
        phase.output_json = dict(output)
    phase.completed_at = datetime.now(UTC)
    run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
    if run is not None:
        run.status = PIPELINE_STATUS_FAILED
        run.error_detail = error[:4000]
        run.completed_at = datetime.now(UTC)
    session.flush()
    return phase


def skip_phase_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
    phase_id: str,
    reason: str,
) -> CortexSubstratePhaseRun:
    phase = get_phase_run_v1(session, pipeline_run_id=pipeline_run_id, phase_id=phase_id)
    if phase is None:
        msg = f"unknown_phase:{phase_id}"
        raise ValueError(msg)
    phase.status = PHASE_STATUS_SKIPPED
    phase.output_json = {"skipped": True, "reason": reason}
    phase.completed_at = datetime.now(UTC)
    session.flush()
    return phase


def finalize_pipeline_run_v1(
    session: Session,
    *,
    pipeline_run_id: uuid.UUID,
) -> CortexSubstratePipelineRun:
    run = session.get(CortexSubstratePipelineRun, pipeline_run_id)
    if run is None:
        msg = "pipeline_run_not_found"
        raise ValueError(msg)
    phases = list(
        session.scalars(
            select(CortexSubstratePhaseRun).where(
                CortexSubstratePhaseRun.pipeline_run_id == pipeline_run_id,
            )
        ).all()
    )
    failed = [p for p in phases if p.status == PHASE_STATUS_FAILED]
    skipped = [p for p in phases if p.status == PHASE_STATUS_SKIPPED]
    if failed:
        run.status = PIPELINE_STATUS_FAILED
    elif skipped:
        run.status = PIPELINE_STATUS_PARTIAL
    else:
        run.status = PIPELINE_STATUS_COMPLETED
    run.completed_at = datetime.now(UTC)
    run.current_phase_id = None
    run.summary_json = {
        "phase_statuses": {p.phase_id: p.status for p in phases},
        "replay_identity": derive_substrate_pipeline_replay_identity_v1(
            tenant_id=run.tenant_id,
            trigger_kind=run.trigger_kind,
            bundle_id=run.bundle_id,
        ),
    }
    session.flush()
    return run
