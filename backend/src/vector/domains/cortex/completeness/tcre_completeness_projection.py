"""TCRE reconstruction completeness (runtime accounting)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.completeness._completeness_common import build_stage_envelope_v1, pct
from vector.domains.cortex.operational_runtime.substrate_tcre_density import (
    compute_tcre_density_metrics_v1,
    derive_tcre_substrate_state_v1,
)
from vector.domains.cortex.operational_runtime.substrate_tcre_omission_explainability import (
    build_tcre_omission_classes_for_completeness_v1,
)
from vector.domains.cortex.reasoning.runtime.reasoning_runtime_orchestrator import (
    build_reasoning_runtime_health_v1,
)


def _derive_tcre_substrate_state_v1(
    *,
    mat_total: int,
    reconstructed: int,
    reconstruction_never_run: bool,
    failed_jobs: int,
    degraded_chron: int,
    pending: int,
) -> str:
    """Backward-compatible alias — delegates to **G-P085-TCRE-02** density law."""
    return derive_tcre_substrate_state_v1(
        mat_total=mat_total,
        reconstructed=reconstructed,
        reconstruction_never_run=reconstruction_never_run,
        failed_jobs=failed_jobs,
        degraded_chron=degraded_chron,
        pending=pending,
    )


def project_tcre_completeness_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    density = compute_tcre_density_metrics_v1(session, tenant_id=tenant_id)
    dm = dict(density["metrics"])
    mat_total = int(dm["tcre_materialization_total"])
    reconstructed = int(dm["tcre_reconstructed_count"])
    pending = int(dm["tcre_pending_count"])
    reconstruction_never_run = bool(dm["reconstruction_never_run"])
    degraded_chron = int(dm["degraded_chronology_count"])

    health = build_reasoning_runtime_health_v1(session, tenant_id=tenant_id)

    omission_classes = build_tcre_omission_classes_for_completeness_v1(
        session,
        tenant_id=tenant_id,
    )

    replay_posture = "stable"
    if health.get("last_replay_result") is False:
        replay_posture = "unsafe"
    elif float(health.get("degraded_chronology_percent") or 0) > 5:
        replay_posture = "partial"

    substrate_state = str(density["substrate_state"])

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
        last_successful_at=str((health.get("last_successful_job") or {}).get("completed_at") or "")
        or None,
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
            "tcre_saturation_percent": dm["tcre_saturation_percent"],
            "tcre_density_score": dm["tcre_density_score"],
            "tcre_maturity_class": density["tcre_maturity_class"],
            "degraded_chronology_percent": health.get("degraded_chronology_percent"),
            "degraded_edge_percent": health.get("degraded_edge_percent"),
            "strict_chronology_percent": pct(
                reconstructed - degraded_chron, reconstructed if reconstructed else 1
            ),
            "replay_divergence_rate": 100.0 if health.get("last_replay_result") is False else 0.0,
        },
    )
