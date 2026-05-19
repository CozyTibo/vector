"""Phase 08.5 P085-28 — operational health dimension bands (**G-P085-HEALTH-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-operational-health-maturity-doctrine.md``.
"""

from __future__ import annotations

import inspect
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.operational_runtime.substrate_operational_maturity import (
    MATURITY_CLASS_DENSITY_EMERGING_V1,
    MATURITY_CLASS_OPERATIONAL_ALIVE_V1,
    MATURITY_CLASS_PROGRESSING_V1,
    MATURITY_CLASS_PRODUCTION_READY_V1,
    MATURITY_CLASS_STRUCTURAL_ONLY_V1,
)
from vector.domains.cortex.operational_runtime.substrate_autonomous_recovery_score import (
    HEALTH_DIM_AUTONOMOUS_RECOVERY_V1,
    evaluate_autonomous_recovery_score_v1,
)
from vector.domains.cortex.operational_runtime.substrate_retrieval_density import (
    compute_retrieval_density_metrics_v1,
)
from vector.domains.cortex.operational_runtime.substrate_retrieval_starvation import (
    evaluate_retrieval_starvation_v1,
)
from vector.domains.cortex.synthesis.synthesis_eligibility_explainability import (
    explain_synthesis_eligibility_v1,
)
from vector.domains.cortex.synthesis.synthesis_idle_classification import (
    SYNTHESIS_CLASSIFICATION_LEGALITY_BLOCKED_V1,
    SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1,
)
from vector.domains.cortex.synthesis.synthesis_throughput_maturity import (
    compute_synthesis_throughput_metrics_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PIPELINE_STATUS_FAILED,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_STALLED,
    CONTINUATION_STATUS_WAITING,
    get_continuation_for_pipeline_v1,
    list_stale_waiting_continuations_v1,
)
from vector.domains.cortex.substrate_pipeline.repository import get_running_pipeline_run_v1
from vector.domains.cortex.substrate_pipeline.substrate_runtime_maturity import (
    STAGE_3_TCRE_ACTIVE,
    evaluate_tenant_runtime_maturity_v1,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
    CortexSubstratePipelineRun,
)
from vector.infrastructure.db.models.cortex_synthesis_job import CortexSynthesisJob

PHASE085_OPERATIONAL_HEALTH_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_OPERATIONAL_HEALTH_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-operational-health-maturity-doctrine.md"
)

GP085_HEALTH01_GATE_ID_V1: Final[str] = "G-P085-HEALTH-01"

HEALTH_BAND_HEALTHY_V1: Final[str] = "healthy"
HEALTH_BAND_DEGRADED_V1: Final[str] = "degraded"
HEALTH_BAND_CRITICAL_V1: Final[str] = "critical"

HEALTH_DIM_SUBSTRATE_CONTINUITY_V1: Final[str] = "substrate_continuity_health"
HEALTH_DIM_RETRIEVAL_DENSITY_V1: Final[str] = "retrieval_density_health"
HEALTH_DIM_ASYNC_RESUME_V1: Final[str] = "async_resume_health"
HEALTH_DIM_SYNTHESIS_ACTIVATION_V1: Final[str] = "synthesis_activation_health"
HEALTH_DIM_ORCHESTRATION_PROGRESS_V1: Final[str] = "orchestration_progress_health"
HEALTH_DIM_SYNTHESIS_THROUGHPUT_V1: Final[str] = "synthesis_throughput_health"
HEALTH_DIM_MULTIDIMENSIONAL_MATURITY_V1: Final[str] = "multidimensional_maturity_health"

HEALTH_DIMENSION_IDS_V1: Final[tuple[str, ...]] = (
    HEALTH_DIM_SUBSTRATE_CONTINUITY_V1,
    HEALTH_DIM_RETRIEVAL_DENSITY_V1,
    HEALTH_DIM_ASYNC_RESUME_V1,
    HEALTH_DIM_SYNTHESIS_ACTIVATION_V1,
    HEALTH_DIM_ORCHESTRATION_PROGRESS_V1,
    HEALTH_DIM_SYNTHESIS_THROUGHPUT_V1,
    HEALTH_DIM_MULTIDIMENSIONAL_MATURITY_V1,
    HEALTH_DIM_AUTONOMOUS_RECOVERY_V1,
)

HEALTH_DIMENSION_DOCTRINE_BANDS_V1: Final[dict[str, dict[str, str]]] = {
    HEALTH_DIM_SUBSTRATE_CONTINUITY_V1: {
        HEALTH_BAND_HEALTHY_V1: "no stall",
        HEALTH_BAND_DEGRADED_V1: "waiting < T_stall",
        HEALTH_BAND_CRITICAL_V1: "stalled",
    },
    HEALTH_DIM_RETRIEVAL_DENSITY_V1: {
        HEALTH_BAND_HEALTHY_V1: "indexed > 0",
        HEALTH_BAND_DEGRADED_V1: "empty publish",
        HEALTH_BAND_CRITICAL_V1: "starvation",
    },
    HEALTH_DIM_ASYNC_RESUME_V1: {
        HEALTH_BAND_HEALTHY_V1: "resumes ok",
        HEALTH_BAND_DEGRADED_V1: "duplicate stalls",
        HEALTH_BAND_CRITICAL_V1: "missing continuation",
    },
    HEALTH_DIM_SYNTHESIS_ACTIVATION_V1: {
        HEALTH_BAND_HEALTHY_V1: "scopes running",
        HEALTH_BAND_DEGRADED_V1: "eligible no jobs",
        HEALTH_BAND_CRITICAL_V1: "forbidden spike",
    },
    HEALTH_DIM_ORCHESTRATION_PROGRESS_V1: {
        HEALTH_BAND_HEALTHY_V1: "past TCRE",
        HEALTH_BAND_DEGRADED_V1: "stuck at TCRE",
        HEALTH_BAND_CRITICAL_V1: "pipeline failed",
    },
    HEALTH_DIM_SYNTHESIS_THROUGHPUT_V1: {
        HEALTH_BAND_HEALTHY_V1: "throughput targets met",
        HEALTH_BAND_DEGRADED_V1: "eligible below targets",
        HEALTH_BAND_CRITICAL_V1: "starvation with eligible scopes",
    },
    HEALTH_DIM_MULTIDIMENSIONAL_MATURITY_V1: {
        HEALTH_BAND_HEALTHY_V1: "OPERATIONAL_ALIVE or PRODUCTION_READY",
        HEALTH_BAND_DEGRADED_V1: "PROGRESSING or DENSITY_EMERGING",
        HEALTH_BAND_CRITICAL_V1: "STRUCTURAL_ONLY with starvation",
    },
    HEALTH_DIM_AUTONOMOUS_RECOVERY_V1: {
        HEALTH_BAND_HEALTHY_V1: "recovery_score >= 0.9",
        HEALTH_BAND_DEGRADED_V1: "recovery_score below target",
        HEALTH_BAND_CRITICAL_V1: "recovery_score critical",
    },
}

_BAND_ORDINAL_V1: Final[dict[str, int]] = {
    HEALTH_BAND_HEALTHY_V1: 0,
    HEALTH_BAND_DEGRADED_V1: 1,
    HEALTH_BAND_CRITICAL_V1: 2,
}


def classify_health_band_v1(*, ok: bool, degraded: bool = False) -> str:
    if ok:
        return HEALTH_BAND_HEALTHY_V1
    if degraded:
        return HEALTH_BAND_DEGRADED_V1
    return HEALTH_BAND_CRITICAL_V1


def worst_health_band_v1(bands: list[str]) -> str:
    worst = HEALTH_BAND_HEALTHY_V1
    for band in bands:
        if _BAND_ORDINAL_V1.get(band, 0) > _BAND_ORDINAL_V1[worst]:
            worst = band
    return worst


def _count_recent_synthesis_forbidden_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    try:
        from vector.settings import get_settings

        threshold = max(1, int(get_settings().cortex_synthesis_forbidden_backoff_threshold))
        window_hours = max(1, int(get_settings().cortex_synthesis_forbidden_backoff_window_hours))
    except Exception:  # noqa: BLE001
        threshold = 3
        window_hours = 24
    since = datetime.now(tz=UTC) - timedelta(hours=window_hours)
    forbidden_count = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSynthesisJob)
            .where(
                CortexSynthesisJob.tenant_id == tenant_id,
                CortexSynthesisJob.synthesis_legality_class == "synthesis_forbidden",
                CortexSynthesisJob.created_at >= since,
            )
        )
        or 0
    )
    return {
        "forbidden_count": forbidden_count,
        "forbidden_backoff_threshold": threshold,
        "forbidden_backoff_active": forbidden_count >= threshold,
    }


def _recent_pipeline_failed_v1(session: Session, *, tenant_id: uuid.UUID) -> bool:
    since = datetime.now(tz=UTC) - timedelta(days=7)
    failed = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSubstratePipelineRun)
            .where(
                CortexSubstratePipelineRun.tenant_id == tenant_id,
                CortexSubstratePipelineRun.status == PIPELINE_STATUS_FAILED,
                CortexSubstratePipelineRun.created_at >= since,
            )
        )
        or 0
    )
    return failed > 0


def evaluate_substrate_continuity_health_v1(
    *,
    continuation_status: str | None,
    stalled_continuation_count: int,
) -> dict[str, Any]:
    stalled = continuation_status == CONTINUATION_STATUS_STALLED or stalled_continuation_count > 0
    waiting = continuation_status == CONTINUATION_STATUS_WAITING
    if stalled:
        band = HEALTH_BAND_CRITICAL_V1
        reason = "stalled"
    elif waiting:
        band = HEALTH_BAND_DEGRADED_V1
        reason = "waiting_below_stall_threshold"
    else:
        band = HEALTH_BAND_HEALTHY_V1
        reason = "no_stall"
    return {"band": band, "reason": reason, "continuation_status": continuation_status}


def evaluate_retrieval_density_health_v1(
    *,
    indexed_count: int,
    index_stale: bool,
    operational_starvation: bool,
    empty_publish: bool,
) -> dict[str, Any]:
    if operational_starvation:
        band = HEALTH_BAND_CRITICAL_V1
        reason = "operational_starvation"
    elif indexed_count <= 0 or empty_publish or index_stale:
        band = HEALTH_BAND_DEGRADED_V1
        reason = "empty_publish"
    else:
        band = HEALTH_BAND_HEALTHY_V1
        reason = "indexed_gt_zero"
    return {
        "band": band,
        "reason": reason,
        "indexed_count": indexed_count,
        "index_stale": index_stale,
    }


def evaluate_async_resume_health_v1(
    *,
    running_pipeline: bool,
    continuation_present: bool,
    pipeline_waiting_on_tcre: bool,
    duplicate_stall_signals: int,
) -> dict[str, Any]:
    if running_pipeline and not continuation_present:
        band = HEALTH_BAND_CRITICAL_V1
        reason = "missing_continuation"
    elif duplicate_stall_signals > 1:
        band = HEALTH_BAND_DEGRADED_V1
        reason = "duplicate_stalls"
    elif pipeline_waiting_on_tcre:
        band = HEALTH_BAND_DEGRADED_V1
        reason = "pipeline_waiting_on_tcre"
    else:
        band = HEALTH_BAND_HEALTHY_V1
        reason = "resumes_ok"
    return {
        "band": band,
        "reason": reason,
        "duplicate_stall_signals": duplicate_stall_signals,
    }


def evaluate_synthesis_activation_health_v1(
    *,
    synthesis_ready: bool,
    eligible_scopes: int,
    forbidden_backoff_active: bool,
    classification: str,
) -> dict[str, Any]:
    if forbidden_backoff_active or classification == SYNTHESIS_CLASSIFICATION_LEGALITY_BLOCKED_V1:
        band = HEALTH_BAND_CRITICAL_V1
        reason = "forbidden_spike"
    elif synthesis_ready:
        band = HEALTH_BAND_HEALTHY_V1
        reason = "scopes_running"
    elif eligible_scopes > 0:
        band = HEALTH_BAND_DEGRADED_V1
        reason = "eligible_no_jobs"
    else:
        band = HEALTH_BAND_HEALTHY_V1
        reason = "healthy_idle"
    return {
        "band": band,
        "reason": reason,
        "eligible_scopes": eligible_scopes,
        "classification": classification,
    }


def evaluate_orchestration_progress_health_v1(
    *,
    maturity_stage: str,
    maturity_class: str,
    pipeline_failed_recent: bool,
    operationally_alive: bool,
) -> dict[str, Any]:
    if pipeline_failed_recent:
        band = HEALTH_BAND_CRITICAL_V1
        reason = "pipeline_failed"
    elif maturity_stage == STAGE_3_TCRE_ACTIVE or maturity_class in (
        MATURITY_CLASS_STRUCTURAL_ONLY_V1,
        MATURITY_CLASS_PROGRESSING_V1,
    ):
        band = HEALTH_BAND_DEGRADED_V1
        reason = "stuck_at_tcre"
    elif operationally_alive or maturity_class in (
        MATURITY_CLASS_DENSITY_EMERGING_V1,
        MATURITY_CLASS_OPERATIONAL_ALIVE_V1,
        MATURITY_CLASS_PRODUCTION_READY_V1,
    ):
        band = HEALTH_BAND_HEALTHY_V1
        reason = "past_tcre"
    else:
        band = HEALTH_BAND_DEGRADED_V1
        reason = "orchestration_incomplete"
    return {
        "band": band,
        "reason": reason,
        "maturity_stage": maturity_stage,
        "maturity_class": maturity_class,
    }


def evaluate_synthesis_throughput_health_v1(
    *,
    all_throughput_targets_met: bool,
    eligible_scopes: int,
    synthesis_classification: str,
) -> dict[str, Any]:
    if (
        eligible_scopes > 0
        and synthesis_classification == SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1
    ):
        band = HEALTH_BAND_CRITICAL_V1
        reason = "starvation_with_eligible"
    elif all_throughput_targets_met:
        band = HEALTH_BAND_HEALTHY_V1
        reason = "throughput_targets_met"
    elif eligible_scopes > 0:
        band = HEALTH_BAND_DEGRADED_V1
        reason = "below_throughput_targets"
    else:
        band = HEALTH_BAND_HEALTHY_V1
        reason = "no_eligible_scopes"
    return {"band": band, "reason": reason}


def evaluate_multidimensional_maturity_health_v1(
    *,
    maturity_class: str,
    operationally_alive: bool,
    active_starvation: bool,
) -> dict[str, Any]:
    if active_starvation and maturity_class == MATURITY_CLASS_STRUCTURAL_ONLY_V1:
        band = HEALTH_BAND_CRITICAL_V1
        reason = "structural_with_starvation"
    elif maturity_class in (
        MATURITY_CLASS_OPERATIONAL_ALIVE_V1,
        MATURITY_CLASS_PRODUCTION_READY_V1,
    ) or operationally_alive:
        band = HEALTH_BAND_HEALTHY_V1
        reason = "operationally_alive"
    elif maturity_class in (
        MATURITY_CLASS_PROGRESSING_V1,
        MATURITY_CLASS_DENSITY_EMERGING_V1,
    ):
        band = HEALTH_BAND_DEGRADED_V1
        reason = "density_emerging_or_progressing"
    else:
        band = HEALTH_BAND_DEGRADED_V1
        reason = "structural_only"
    return {"band": band, "reason": reason, "maturity_class": maturity_class}


def evaluate_operational_health_dimensions_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stall_threshold_seconds: int = 1800,
) -> dict[str, Any]:
    """Evaluate all **G-P085-HEALTH-01** dimension bands for a tenant."""
    maturity = evaluate_tenant_runtime_maturity_v1(session, tenant_id=tenant_id)
    eligibility = explain_synthesis_eligibility_v1(session, tenant_id=tenant_id)
    retrieval_density = compute_retrieval_density_metrics_v1(session, tenant_id=tenant_id)
    retrieval_starvation = evaluate_retrieval_starvation_v1(session, tenant_id=tenant_id)
    synthesis_throughput = compute_synthesis_throughput_metrics_v1(session, tenant_id=tenant_id)

    running = get_running_pipeline_run_v1(session, tenant_id=tenant_id)
    continuation = (
        get_continuation_for_pipeline_v1(session, pipeline_run_id=running.id)
        if running
        else None
    )
    continuation_status = continuation.continuation_status if continuation else None
    stalled_list = list_stale_waiting_continuations_v1(
        session,
        tenant_id=tenant_id,
        stall_threshold_seconds=stall_threshold_seconds,
        limit=20,
    )

    rd_metrics = dict(retrieval_density.get("metrics") or {})
    indexed_count = int(rd_metrics.get("retrieval_indexed_count") or 0)
    index_stale = bool(dict(retrieval_starvation.get("index_freshness") or {}).get("index_stale"))
    starvation_active = bool(retrieval_starvation.get("operational_starvation"))
    published_epoch = rd_metrics.get("published_index_epoch")
    empty_publish = published_epoch is not None and indexed_count == 0

    forbidden = _count_recent_synthesis_forbidden_v1(session, tenant_id=tenant_id)
    classification = str(eligibility.get("classification") or "")
    throughput_targets = dict(synthesis_throughput.get("throughput_targets") or {})
    multi = dict(maturity.get("multidimensional_maturity") or {})
    starvation_multi = dict(multi.get("operational_starvation") or {})

    continuity_detail = evaluate_substrate_continuity_health_v1(
        continuation_status=continuation_status,
        stalled_continuation_count=len(stalled_list),
    )
    retrieval_detail = evaluate_retrieval_density_health_v1(
        indexed_count=indexed_count,
        index_stale=index_stale,
        operational_starvation=starvation_active,
        empty_publish=empty_publish,
    )
    async_detail = evaluate_async_resume_health_v1(
        running_pipeline=running is not None,
        continuation_present=continuation is not None,
        pipeline_waiting_on_tcre=bool(
            eligibility.get("blocked_by") and "pipeline_waiting_on_tcre" in eligibility["blocked_by"]
        ),
        duplicate_stall_signals=len(stalled_list),
    )
    synthesis_detail = evaluate_synthesis_activation_health_v1(
        synthesis_ready=bool(eligibility.get("synthesis_ready")),
        eligible_scopes=int(eligibility.get("eligible_scopes") or 0),
        forbidden_backoff_active=bool(forbidden.get("forbidden_backoff_active")),
        classification=classification,
    )
    orchestration_detail = evaluate_orchestration_progress_health_v1(
        maturity_stage=str(maturity.get("maturity_stage") or ""),
        maturity_class=str(maturity.get("maturity_class") or ""),
        pipeline_failed_recent=_recent_pipeline_failed_v1(session, tenant_id=tenant_id),
        operationally_alive=bool(maturity.get("operationally_alive")),
    )
    throughput_detail = evaluate_synthesis_throughput_health_v1(
        all_throughput_targets_met=bool(throughput_targets.get("all_throughput_targets_met")),
        eligible_scopes=int(eligibility.get("eligible_scopes") or 0),
        synthesis_classification=classification,
    )
    multidim_detail = evaluate_multidimensional_maturity_health_v1(
        maturity_class=str(maturity.get("maturity_class") or ""),
        operationally_alive=bool(maturity.get("operationally_alive")),
        active_starvation=bool(starvation_multi.get("active")),
    )
    recovery_eval = evaluate_autonomous_recovery_score_v1(
        session,
        tenant_id=tenant_id,
        stall_threshold_seconds=stall_threshold_seconds,
    )
    recovery_detail = dict(recovery_eval.get("autonomous_recovery_health") or {})
    recovery_detail["operational_stability"] = recovery_eval.get("operational_stability")
    recovery_detail["metrics"] = recovery_eval.get("metrics")

    health_dimensions = {
        HEALTH_DIM_SUBSTRATE_CONTINUITY_V1: continuity_detail["band"],
        HEALTH_DIM_RETRIEVAL_DENSITY_V1: retrieval_detail["band"],
        HEALTH_DIM_ASYNC_RESUME_V1: async_detail["band"],
        HEALTH_DIM_SYNTHESIS_ACTIVATION_V1: synthesis_detail["band"],
        HEALTH_DIM_ORCHESTRATION_PROGRESS_V1: orchestration_detail["band"],
        HEALTH_DIM_SYNTHESIS_THROUGHPUT_V1: throughput_detail["band"],
        HEALTH_DIM_MULTIDIMENSIONAL_MATURITY_V1: multidim_detail["band"],
        HEALTH_DIM_AUTONOMOUS_RECOVERY_V1: recovery_detail["band"],
    }
    health_dimension_details = {
        HEALTH_DIM_SUBSTRATE_CONTINUITY_V1: continuity_detail,
        HEALTH_DIM_RETRIEVAL_DENSITY_V1: retrieval_detail,
        HEALTH_DIM_ASYNC_RESUME_V1: async_detail,
        HEALTH_DIM_SYNTHESIS_ACTIVATION_V1: synthesis_detail,
        HEALTH_DIM_ORCHESTRATION_PROGRESS_V1: orchestration_detail,
        HEALTH_DIM_SYNTHESIS_THROUGHPUT_V1: throughput_detail,
        HEALTH_DIM_MULTIDIMENSIONAL_MATURITY_V1: multidim_detail,
        HEALTH_DIM_AUTONOMOUS_RECOVERY_V1: recovery_detail,
    }

    return {
        "tenant_id": str(tenant_id),
        "gate_id": GP085_HEALTH01_GATE_ID_V1,
        "health_dimensions": health_dimensions,
        "health_dimension_details": health_dimension_details,
        "overall_health": worst_health_band_v1(list(health_dimensions.values())),
        "stalled_pipeline_count": len(stalled_list),
        "runtime_maturity": maturity,
        "eligibility_explanation": eligibility,
        "retrieval_density_metrics": retrieval_density,
        "retrieval_starvation": retrieval_starvation,
        "synthesis_throughput_metrics": synthesis_throughput,
        "multidimensional_operational_maturity": multi,
        "forbidden_metrics": forbidden,
        "autonomous_recovery": recovery_eval,
    }


def build_operational_health_card_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stall_threshold_seconds: int = 1800,
) -> dict[str, Any]:
    """Operator health dashboard card."""
    eval_out = evaluate_operational_health_dimensions_v1(
        session,
        tenant_id=tenant_id,
        stall_threshold_seconds=stall_threshold_seconds,
    )
    return {
        "surface_kind": "operational_health_card",
        "gate_id": GP085_HEALTH01_GATE_ID_V1,
        "overall_health": eval_out["overall_health"],
        "health_dimensions": eval_out["health_dimensions"],
        "health_dimension_details": eval_out["health_dimension_details"],
        "stalled_pipeline_count": eval_out["stalled_pipeline_count"],
        "maturity_class": dict(eval_out.get("runtime_maturity") or {}).get("maturity_class"),
        "operational_confidence_score": dict(eval_out.get("runtime_maturity") or {}).get(
            "operational_confidence_score"
        ),
        "recovery_score": dict(dict(eval_out.get("autonomous_recovery") or {}).get("metrics") or {}).get(
            "recovery_score"
        ),
        "detail_route": f"/admin/tenants/{tenant_id}/cortex/operational-runtime/operational-health",
    }


def build_substrate_operational_health_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_operational_health_runtime_schema_version": int(
            PHASE085_OPERATIONAL_HEALTH_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_OPERATIONAL_HEALTH_SPEC_REF_V1,
        "primary_gate_id": GP085_HEALTH01_GATE_ID_V1,
        "health_bands": [
            HEALTH_BAND_HEALTHY_V1,
            HEALTH_BAND_DEGRADED_V1,
            HEALTH_BAND_CRITICAL_V1,
        ],
        "dimension_ids": list(HEALTH_DIMENSION_IDS_V1),
        "doctrine_bands": dict(HEALTH_DIMENSION_DOCTRINE_BANDS_V1),
        "evaluation_entrypoint": "evaluate_operational_health_dimensions_v1",
        "aggregate_entrypoint": "evaluate_substrate_operational_health_v1",
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.substrate_operational_health_dimensions"
        ),
    }


def verify_gp085_health01_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_operational_health_catalog_v1()
    if cat["primary_gate_id"] != GP085_HEALTH01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")
    if set(cat["dimension_ids"]) != set(HEALTH_DIMENSION_IDS_V1):
        errors.append("dimension_ids_mismatch")

    if (
        evaluate_substrate_continuity_health_v1(
            continuation_status=CONTINUATION_STATUS_STALLED,
            stalled_continuation_count=1,
        )["band"]
        != HEALTH_BAND_CRITICAL_V1
    ):
        errors.append("continuity_stalled_band")

    if (
        evaluate_retrieval_density_health_v1(
            indexed_count=10,
            index_stale=False,
            operational_starvation=False,
            empty_publish=False,
        )["band"]
        != HEALTH_BAND_HEALTHY_V1
    ):
        errors.append("retrieval_healthy_band")

    if (
        evaluate_synthesis_activation_health_v1(
            synthesis_ready=False,
            eligible_scopes=5,
            forbidden_backoff_active=False,
            classification="progressing",
        )["band"]
        != HEALTH_BAND_DEGRADED_V1
    ):
        errors.append("synthesis_eligible_no_jobs")

    if (
        evaluate_synthesis_activation_health_v1(
            synthesis_ready=False,
            eligible_scopes=0,
            forbidden_backoff_active=True,
            classification=SYNTHESIS_CLASSIFICATION_LEGALITY_BLOCKED_V1,
        )["band"]
        != HEALTH_BAND_CRITICAL_V1
    ):
        errors.append("synthesis_forbidden_spike")

    if worst_health_band_v1([HEALTH_BAND_HEALTHY_V1, HEALTH_BAND_CRITICAL_V1]) != HEALTH_BAND_CRITICAL_V1:
        errors.append("worst_band_aggregation")

    from vector.domains.cortex.substrate_pipeline import substrate_operational_health as soh

    if "evaluate_operational_health_dimensions_v1" not in inspect.getsource(
        soh.evaluate_substrate_operational_health_v1
    ):
        errors.append("operational_health_missing_dimensions_delegate")

    passed = not errors
    return {
        "id": GP085_HEALTH01_GATE_ID_V1,
        "name": "cesp_substrate_operational_health_dimensions",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
