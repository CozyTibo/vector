"""Live substrate operational health (continuity, density, activation)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.retrieval.retrieval_density_metrics import (
    get_retrieval_density_metrics_snapshot_v1,
)
from vector.domains.cortex.synthesis.synthesis_eligibility_explainability import (
    explain_synthesis_eligibility_v1,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_STALLED,
    CONTINUATION_STATUS_WAITING,
    get_continuation_for_pipeline_v1,
    list_stale_waiting_continuations_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1
from vector.domains.cortex.substrate_pipeline.substrate_runtime_maturity import (
    evaluate_tenant_runtime_maturity_v1,
)


def _health_band(*, ok: bool, degraded: bool = False) -> str:
    if ok:
        return "healthy"
    if degraded:
        return "degraded"
    return "critical"


def evaluate_substrate_operational_health_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stall_threshold_seconds: int = 1800,
) -> dict[str, Any]:
    maturity = evaluate_tenant_runtime_maturity_v1(session, tenant_id=tenant_id)
    eligibility = explain_synthesis_eligibility_v1(session, tenant_id=tenant_id)
    density = get_retrieval_density_metrics_snapshot_v1()

    running = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    continuation = (
        get_continuation_for_pipeline_v1(session, pipeline_run_id=running.id)
        if running
        else None
    )
    waiting = (
        continuation is not None
        and continuation.continuation_status in (CONTINUATION_STATUS_WAITING, CONTINUATION_STATUS_STALLED)
    )
    stalled_local = bool(continuation and continuation.continuation_status == CONTINUATION_STATUS_STALLED)

    substrate_continuity_health = _health_band(
        ok=not waiting or not stalled_local,
        degraded=waiting and not stalled_local,
    )
    retrieval_density_health = _health_band(
        ok=int(eligibility.get("retrieval_row_count") or 0) > 0,
        degraded=bool(eligibility.get("published_epoch_exists")) and int(eligibility.get("retrieval_row_count") or 0) == 0,
    )
    async_resume_health = _health_band(
        ok=not bool(eligibility.get("blocked_by") and "pipeline_waiting_on_tcre" in eligibility["blocked_by"]),
        degraded=bool(eligibility.get("blocked_by") and "pipeline_waiting_on_tcre" in eligibility["blocked_by"]),
    )
    synthesis_activation_health = _health_band(
        ok=bool(eligibility.get("synthesis_ready")),
        degraded=int(eligibility.get("eligible_scopes") or 0) > 0 and not eligibility.get("synthesis_ready"),
    )
    orchestration_progress_health = _health_band(
        ok=maturity["maturity_stage"] not in ("STAGE_0_IDLE", "STAGE_3_TCRE_ACTIVE")
        or maturity.get("operationally_alive"),
        degraded=maturity["maturity_stage"] == "STAGE_3_TCRE_ACTIVE",
    )

    return {
        "tenant_id": str(tenant_id),
        "runtime_maturity": maturity,
        "eligibility_explanation": eligibility,
        "retrieval_density_metrics": density,
        "health_dimensions": {
            "substrate_continuity_health": substrate_continuity_health,
            "retrieval_density_health": retrieval_density_health,
            "async_resume_health": async_resume_health,
            "synthesis_activation_health": synthesis_activation_health,
            "orchestration_progress_health": orchestration_progress_health,
        },
        "stalled_pipeline_count": len(
            list_stale_waiting_continuations_v1(
                session,
                tenant_id=tenant_id,
                stall_threshold_seconds=stall_threshold_seconds,
                limit=20,
            )
        ),
    }
