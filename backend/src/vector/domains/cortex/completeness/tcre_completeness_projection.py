"""TCRE reconstruction completeness (runtime accounting)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.completeness._completeness_common import build_stage_envelope_v1, pct
from vector.domains.cortex.reasoning.runtime.reasoning_runtime_orchestrator import (
    build_reasoning_runtime_health_v1,
)
from vector.infrastructure.db.models.cortex_canonical_transform_materialization import (
    CortexCanonicalTransformMaterialization,
)
from vector.infrastructure.db.models.cortex_tcre_reconstruction_job import (
    CortexTcreReconstructionJob,
)
def project_tcre_completeness_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    mat_total = int(
        session.scalar(
            select(func.count())
            .select_from(CortexCanonicalTransformMaterialization)
            .where(CortexCanonicalTransformMaterialization.tenant_id == tenant_id)
        )
        or 0
    )
    health = build_reasoning_runtime_health_v1(session, tenant_id=tenant_id)
    last_job = health.get("last_successful_job") or {}
    degraded_chron = 0
    reconstructed = 0
    completed_jobs = list(
        session.scalars(
            select(CortexTcreReconstructionJob)
            .where(
                CortexTcreReconstructionJob.tenant_id == tenant_id,
                CortexTcreReconstructionJob.status == "completed",
                CortexTcreReconstructionJob.job_kind == "reconstruct",
            )
            .order_by(CortexTcreReconstructionJob.completed_at.desc())
            .limit(50)
        ).all()
    )
    for job in completed_jobs:
        summary = job.summary_json or {}
        reconstructed += int(
            summary.get("materialization_count")
            or summary.get("chronology_count")
            or summary.get("chronology_receipt_count")
            or 0
        )
        degraded_chron += int(summary.get("chronology_degraded_count") or 0)
    reconstructed = min(reconstructed, mat_total) if mat_total else 0
    pending = max(0, mat_total - reconstructed) if mat_total else 0
    reconstruction_never_run = mat_total > 0 and not completed_jobs

    omission_classes: dict[str, int] = {}
    if pending and reconstruction_never_run:
        omission_classes["reconstruction_not_yet_run"] = pending
    elif pending:
        omission_classes["reconstruction_coverage_gap"] = pending
    if health.get("last_replay_result") is False:
        omission_classes["replay_divergence_detected"] = 1
    if float(health.get("degraded_chronology_percent") or 0) > 0:
        omission_classes["degradation_propagated"] = int(degraded_chron)

    failed_jobs = int(health.get("failed_job_count") or 0)
    if failed_jobs:
        omission_classes["causal_legality_unverified"] = failed_jobs

    replay_posture = "stable"
    if health.get("last_replay_result") is False:
        replay_posture = "unsafe"
    elif float(health.get("degraded_chronology_percent") or 0) > 5:
        replay_posture = "partial"

    substrate_state = "healthy"
    if mat_total == 0:
        substrate_state = "critical"
    elif failed_jobs and reconstructed == 0:
        substrate_state = "critical"
    elif degraded_chron or failed_jobs or (pending and not reconstruction_never_run):
        substrate_state = "degraded"
    elif reconstruction_never_run:
        substrate_state = "healthy"

    return build_stage_envelope_v1(
        stage_id="tcre",
        label="TCRE",
        total_objects=mat_total,
        processed_count=reconstructed,
        degraded_count=degraded_chron,
        unresolved_count=0 if reconstruction_never_run else pending,
        omitted_count=0,
        intentionally_excluded_count=pending if reconstruction_never_run else 0,
        replay_posture=replay_posture,
        substrate_state=substrate_state,
        last_successful_at=str(last_job.get("completed_at") or "") or None,
        drift_warnings=(
            [f"last_replay_divergence_at={health.get('last_replay_divergence_at')}"]
            if health.get("last_replay_divergence_at")
            else []
        ),
        omission_classes=omission_classes,
        detail_route=f"/admin/tenants/{tenant_id}/cortex/reasoning",
        metrics={
            "canonical_materializations_total": mat_total,
            "reconstructed_count": reconstructed,
            "pending_reconstruction_count": pending,
            "reconstruction_never_run": reconstruction_never_run,
            "degraded_chronology_percent": health.get("degraded_chronology_percent"),
            "degraded_edge_percent": health.get("degraded_edge_percent"),
            "strict_chronology_percent": pct(
                reconstructed - degraded_chron, reconstructed if reconstructed else 1
            ),
            "replay_divergence_rate": 100.0 if health.get("last_replay_result") is False else 0.0,
        },
    )
