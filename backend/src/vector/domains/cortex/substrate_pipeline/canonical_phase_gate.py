"""Shared canonical→identity gate (convergence + legacy Celery must agree)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.canonical.forward_progress.constants import (
    CANONICAL_OUTCOME_PARTIAL_PROGRESS,
    CANONICAL_OUTCOME_TOPOLOGY_WAIT,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_02_CANONICAL,
    PHASE_STATUS_FAILED,
    PHASE_STATUS_WAITING,
)
from vector.domains.cortex.substrate_pipeline.repository import get_phase_run_v1
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.raw_ingestion_record import RawIngestionRecord


def untreated_raw_exists_v1(session: Session, *, tenant_id: uuid.UUID) -> bool:
    """True when at least one raw row has no materialization for the tenant."""
    mat_exists = (
        select(CortexCanonicalTransformMaterialization.id)
        .where(
            CortexCanonicalTransformMaterialization.tenant_id == tenant_id,
            CortexCanonicalTransformMaterialization.raw_record_id == RawIngestionRecord.id,
        )
        .correlate(RawIngestionRecord)
        .exists()
    )
    stmt = (
        select(RawIngestionRecord.id)
        .where(RawIngestionRecord.tenant_id == tenant_id, ~mat_exists)
        .limit(1)
    )
    return session.execute(stmt).first() is not None


def canonical_needs_more_work_v1(
    session: Session,
    *,
    canonical_summary: dict[str, Any],
    tenant_id: uuid.UUID,
) -> bool:
    """Mirror convergence worker: canonical slice not done — do not advance to identity."""
    if bool(canonical_summary.get("skipped")):
        return False
    outcome = str(canonical_summary.get("canonical_outcome") or "")
    if outcome in (CANONICAL_OUTCOME_TOPOLOGY_WAIT, CANONICAL_OUTCOME_PARTIAL_PROGRESS):
        return True
    if bool(canonical_summary.get("progress_made")):
        if bool(canonical_summary.get("slice_budget_exhausted")) or bool(
            canonical_summary.get("candidate_more_remain")
        ):
            return True
    if bool(canonical_summary.get("hit_slice_cap")) and bool(canonical_summary.get("progress_made")):
        return True
    return untreated_raw_exists_v1(session, tenant_id=tenant_id)


def _canonical_summary_from_phase_output(phase_output: dict[str, Any]) -> dict[str, Any]:
    raw = phase_output.get("canonical_summary")
    return raw if isinstance(raw, dict) else {}


def canonical_may_advance_to_identity_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    phase_output: dict[str, Any],
) -> tuple[bool, str | None]:
    """Whether phase 03 may run after phase 02 (substrate determinism contract)."""
    summary = _canonical_summary_from_phase_output(phase_output)
    total_succeeded = int(summary.get("total_succeeded") or 0)

    phase_run = get_phase_run_v1(
        session,
        pipeline_run_id=pipeline_run_id,
        phase_id=PHASE_02_CANONICAL,
    )
    if phase_run is not None:
        if phase_run.status == PHASE_STATUS_WAITING and total_succeeded == 0:
            return False, "canonical_topology_wait_zero_progress"
        if phase_run.status == PHASE_STATUS_FAILED and total_succeeded == 0:
            return False, "canonical_materialization_failed_zero_progress"

    if canonical_needs_more_work_v1(session, canonical_summary=summary, tenant_id=tenant_id):
        outcome = str(summary.get("canonical_outcome") or "incomplete")
        return False, f"canonical_incomplete:{outcome}"

    return True, None


def evaluate_legacy_canonical_chain_gate_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    phase_output: dict[str, Any],
    gate_enabled: bool = True,
) -> dict[str, Any]:
    """Legacy deprecated phase task: surface gate result (M6: no Celery phase chain)."""
    if not gate_enabled:
        return {"may_chain": True, "reason": None, "gate_enabled": False}
    may_advance, reason = canonical_may_advance_to_identity_v1(
        session,
        tenant_id=tenant_id,
        pipeline_run_id=pipeline_run_id,
        phase_output=phase_output,
    )
    return {
        "may_chain": may_advance,
        "reason": reason,
        "gate_enabled": True,
    }
