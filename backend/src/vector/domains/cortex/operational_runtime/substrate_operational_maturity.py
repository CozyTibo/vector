"""Phase 08.5 P085-27 — multi-dimensional operational maturity (**G-P085-MAT-01**).

Normative: ``DOCS/cortex/operational-runtime/phase-085-operational-health-maturity-doctrine.md``.
"""

from __future__ import annotations

import inspect
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, Final

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.operational_runtime.substrate_retrieval_starvation import (
    evaluate_retrieval_starvation_v1,
)
from vector.domains.cortex.substrate_pipeline.constants import (
    PHASE_07_RETRIEVAL,
    PHASE_08_SYNTHESIS,
    PHASE_STATUS_COMPLETED,
    PHASE_STATUS_SKIPPED,
    PIPELINE_STATUS_COMPLETED,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    list_stale_waiting_continuations_v1,
)
from vector.domains.cortex.synthesis.synthesis_eligibility_explainability import (
    explain_synthesis_eligibility_v1,
)
from vector.infrastructure.db.models.cortex_substrate_pipeline_run import (
    CortexSubstratePhaseRun,
    CortexSubstratePipelineRun,
)

PHASE085_OPERATIONAL_MATURITY_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_OPERATIONAL_MATURITY_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-operational-health-maturity-doctrine.md"
)

GP085_MAT01_GATE_ID_V1: Final[str] = "G-P085-MAT-01"

MATURITY_CLASS_STRUCTURAL_ONLY_V1: Final[str] = "STRUCTURAL_ONLY"
MATURITY_CLASS_PROGRESSING_V1: Final[str] = "PROGRESSING"
MATURITY_CLASS_DENSITY_EMERGING_V1: Final[str] = "DENSITY_EMERGING"
MATURITY_CLASS_OPERATIONAL_ALIVE_V1: Final[str] = "OPERATIONAL_ALIVE"
MATURITY_CLASS_PRODUCTION_READY_V1: Final[str] = "PRODUCTION_READY"

DIMENSION_CONTINUITY_V1: Final[str] = "continuity"
DIMENSION_GRAPH_DENSITY_V1: Final[str] = "graph_density"
DIMENSION_TRAVERSAL_COMPLETION_V1: Final[str] = "traversal_completion"
DIMENSION_TCRE_SATURATION_V1: Final[str] = "tcre_saturation"
DIMENSION_RETRIEVAL_DENSITY_V1: Final[str] = "retrieval_density"
DIMENSION_SYNTHESIS_ACTIVATION_V1: Final[str] = "synthesis_activation"

MATURITY_DIMENSION_IDS_V1: Final[tuple[str, ...]] = (
    DIMENSION_CONTINUITY_V1,
    DIMENSION_GRAPH_DENSITY_V1,
    DIMENSION_TRAVERSAL_COMPLETION_V1,
    DIMENSION_TCRE_SATURATION_V1,
    DIMENSION_RETRIEVAL_DENSITY_V1,
    DIMENSION_SYNTHESIS_ACTIVATION_V1,
)

MATURITY_DIMENSION_WEIGHTS_V1: Final[dict[str, float]] = {
    DIMENSION_CONTINUITY_V1: 0.25,
    DIMENSION_GRAPH_DENSITY_V1: 0.15,
    DIMENSION_TRAVERSAL_COMPLETION_V1: 0.15,
    DIMENSION_TCRE_SATURATION_V1: 0.15,
    DIMENSION_RETRIEVAL_DENSITY_V1: 0.20,
    DIMENSION_SYNTHESIS_ACTIVATION_V1: 0.10,
}

METRIC_OPERATIONAL_CONFIDENCE_SCORE_V1: Final[str] = "operational_confidence_score"

_DEFAULT_DIMENSION_ALIVE_FLOOR_V1: Final[float] = 60.0
_DEFAULT_COMPOSITE_ALIVE_FLOOR_V1: Final[float] = 70.0
_DEFAULT_PRODUCTION_SOAK_DAYS_V1: Final[int] = 7


def get_operational_maturity_thresholds_v1() -> dict[str, Any]:
    try:
        from vector.settings import get_settings

        cfg = get_settings()
        return {
            "dimension_alive_floor": float(cfg.cortex_operational_maturity_dimension_alive_floor),
            "composite_alive_floor": float(cfg.cortex_operational_maturity_composite_alive_floor),
            "production_soak_days": int(cfg.cortex_operational_maturity_production_soak_days),
            "progressing_continuity_floor": float(
                cfg.cortex_operational_maturity_progressing_continuity_floor
            ),
            "density_emerging_retrieval_floor": float(
                cfg.cortex_operational_maturity_density_emerging_retrieval_floor
            ),
        }
    except Exception:  # noqa: BLE001
        return {
            "dimension_alive_floor": _DEFAULT_DIMENSION_ALIVE_FLOOR_V1,
            "composite_alive_floor": _DEFAULT_COMPOSITE_ALIVE_FLOOR_V1,
            "production_soak_days": _DEFAULT_PRODUCTION_SOAK_DAYS_V1,
            "progressing_continuity_floor": 40.0,
            "density_emerging_retrieval_floor": 40.0,
        }


def _clamp_score_0_100(value: float) -> float:
    return round(max(0.0, min(100.0, float(value))), 2)


def compute_continuity_dimension_score_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stall_threshold_seconds: int = 1800,
) -> dict[str, Any]:
    """Pipeline phase 07–08 completion rate minus stall penalty."""
    since = datetime.now(tz=UTC) - timedelta(days=30)
    runs = list(
        session.scalars(
            select(CortexSubstratePipelineRun)
            .where(
                CortexSubstratePipelineRun.tenant_id == tenant_id,
                CortexSubstratePipelineRun.created_at >= since,
            )
            .order_by(CortexSubstratePipelineRun.created_at.desc())
            .limit(32)
        ).all()
    )
    completed_runs = [r for r in runs if r.status == PIPELINE_STATUS_COMPLETED]
    total = len(completed_runs)
    both_07_08 = 0
    for run in completed_runs:
        phases = list(
            session.scalars(
                select(CortexSubstratePhaseRun).where(
                    CortexSubstratePhaseRun.pipeline_run_id == run.id,
                    CortexSubstratePhaseRun.phase_id.in_((PHASE_07_RETRIEVAL, PHASE_08_SYNTHESIS)),
                )
            ).all()
        )
        by_id = {p.phase_id: p.status for p in phases}
        ok_07 = by_id.get(PHASE_07_RETRIEVAL) in (PHASE_STATUS_COMPLETED, PHASE_STATUS_SKIPPED)
        ok_08 = by_id.get(PHASE_08_SYNTHESIS) in (PHASE_STATUS_COMPLETED, PHASE_STATUS_SKIPPED)
        if ok_07 and ok_08:
            both_07_08 += 1

    completion_rate = (float(both_07_08) / float(total)) * 100.0 if total > 0 else 0.0
    stalled = list_stale_waiting_continuations_v1(
        session,
        tenant_id=tenant_id,
        stall_threshold_seconds=stall_threshold_seconds,
        limit=20,
    )
    stall_penalty = min(40.0, float(len(stalled)) * 10.0)
    score = _clamp_score_0_100(completion_rate - stall_penalty)
    return {
        "score": score,
        "pipeline_runs_sampled": len(runs),
        "completed_pipeline_runs": total,
        "phase_07_08_both_complete": both_07_08,
        "stalled_continuations": len(stalled),
        "completion_rate_percent": round(completion_rate, 2),
    }


def compute_graph_density_dimension_score_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.graph_density import (
        METRIC_GRAPH_DENSITY_SCORE_V1,
        compute_graph_density_metrics_v1,
    )

    snap = compute_graph_density_metrics_v1(session, tenant_id=tenant_id)
    score = float(dict(snap.get("metrics") or {}).get(METRIC_GRAPH_DENSITY_SCORE_V1) or 0)
    return {
        "score": _clamp_score_0_100(score),
        "graph_maturity_stage": snap.get("graph_maturity_stage"),
        "connectivity_ratio": dict(snap.get("metrics") or {}).get("graph_connectivity_ratio"),
    }


def compute_traversal_completion_dimension_score_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.substrate_traversal_explainability import (
        METRIC_TRAVERSAL_DENSITY_SCORE_V1,
        METRIC_WALKS_COMPLETED_RATE_V1,
        compute_traversal_density_metrics_v1,
    )

    metrics = compute_traversal_density_metrics_v1(session, tenant_id=tenant_id)
    density = float(metrics.get(METRIC_TRAVERSAL_DENSITY_SCORE_V1) or 0.0)
    walks_rate = float(metrics.get(METRIC_WALKS_COMPLETED_RATE_V1) or 0.0)
    score = max(density * 100.0, walks_rate * 100.0)
    return {
        "score": _clamp_score_0_100(score),
        "walks_completed_rate": walks_rate,
        "traversal_density_score": density,
    }


def compute_tcre_saturation_dimension_score_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.substrate_tcre_density import (
        METRIC_TCRE_SATURATION_PERCENT_V1,
        TCRE_MATURITY_R2_V1,
        TCRE_MATURITY_R3_V1,
        compute_tcre_density_metrics_v1,
    )

    snap = compute_tcre_density_metrics_v1(session, tenant_id=tenant_id)
    metrics = dict(snap.get("metrics") or {})
    saturation = float(metrics.get(METRIC_TCRE_SATURATION_PERCENT_V1) or 0.0)
    maturity = str(snap.get("tcre_maturity_class") or "")
    return {
        "score": _clamp_score_0_100(saturation),
        "tcre_maturity_class": maturity,
        "tcre_at_least_r2": maturity in (TCRE_MATURITY_R2_V1, TCRE_MATURITY_R3_V1),
    }


def compute_retrieval_density_dimension_score_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    from vector.domains.cortex.operational_runtime.substrate_retrieval_density import (
        METRIC_RETRIEVAL_DENSITY_SCORE_V1,
        compute_retrieval_density_metrics_v1,
    )

    snap = compute_retrieval_density_metrics_v1(session, tenant_id=tenant_id)
    score = float(dict(snap.get("metrics") or {}).get(METRIC_RETRIEVAL_DENSITY_SCORE_V1) or 0)
    return {
        "score": _clamp_score_0_100(score),
        "retrieval_maturity_class": snap.get("retrieval_maturity_class"),
    }


def compute_synthesis_activation_dimension_score_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    from vector.domains.cortex.synthesis.synthesis_throughput_maturity import (
        METRIC_SYNTHESIS_SCOPE_COVERAGE_PERCENT_V1,
        compute_synthesis_throughput_metrics_v1,
    )

    snap = compute_synthesis_throughput_metrics_v1(session, tenant_id=tenant_id)
    coverage = float(
        dict(snap.get("metrics") or {}).get(METRIC_SYNTHESIS_SCOPE_COVERAGE_PERCENT_V1) or 0.0
    )
    return {
        "score": _clamp_score_0_100(coverage),
        "synthesis_maturity_class": snap.get("synthesis_maturity_class"),
    }


def compute_operational_confidence_score_v1(
    dimension_scores: Mapping[str, float],
) -> float:
    total = 0.0
    for dim_id, weight in MATURITY_DIMENSION_WEIGHTS_V1.items():
        total += float(dimension_scores.get(dim_id) or 0.0) * weight
    return _clamp_score_0_100(total)


def detect_active_operational_starvation_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    retrieval = evaluate_retrieval_starvation_v1(session, tenant_id=tenant_id)
    synthesis = explain_synthesis_eligibility_v1(session, tenant_id=tenant_id)
    retrieval_starved = bool(retrieval.get("operational_starvation"))
    synthesis_starved = str(synthesis.get("classification") or "") == "operational_starvation"
    return {
        "active": retrieval_starved or synthesis_starved,
        "retrieval_operational_starvation": retrieval_starved,
        "synthesis_operational_starvation": synthesis_starved,
    }


def classify_operational_maturity_v1(
    *,
    dimension_scores: Mapping[str, float],
    operational_confidence_score: float,
    continuity_score: float,
    retrieval_density_score: float,
    tcre_at_least_r2: bool,
    active_starvation: bool,
    production_soak_met: bool,
    close_gate_met: bool,
    thresholds: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    th = dict(thresholds or get_operational_maturity_thresholds_v1())
    dim_floor = float(th["dimension_alive_floor"])
    composite_floor = float(th["composite_alive_floor"])
    progressing_floor = float(th["progressing_continuity_floor"])
    density_ret_floor = float(th["density_emerging_retrieval_floor"])

    all_dims_alive = all(float(dimension_scores.get(d) or 0) >= dim_floor for d in MATURITY_DIMENSION_IDS_V1)
    composite_alive = float(operational_confidence_score) >= composite_floor

    if (
        production_soak_met
        and close_gate_met
        and all_dims_alive
        and composite_alive
        and not active_starvation
    ):
        maturity_class = MATURITY_CLASS_PRODUCTION_READY_V1
    elif all_dims_alive and composite_alive and not active_starvation:
        maturity_class = MATURITY_CLASS_OPERATIONAL_ALIVE_V1
    elif float(retrieval_density_score) >= density_ret_floor and tcre_at_least_r2:
        maturity_class = MATURITY_CLASS_DENSITY_EMERGING_V1
    elif float(continuity_score) >= progressing_floor:
        maturity_class = MATURITY_CLASS_PROGRESSING_V1
    else:
        maturity_class = MATURITY_CLASS_STRUCTURAL_ONLY_V1

    return {
        "maturity_class": maturity_class,
        "operationally_alive": maturity_class
        in (MATURITY_CLASS_OPERATIONAL_ALIVE_V1, MATURITY_CLASS_PRODUCTION_READY_V1),
        "all_dimensions_alive": all_dims_alive,
        "composite_alive": composite_alive,
        "thresholds": th,
    }


def _evaluate_production_soak_met_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    soak_days: int,
) -> bool:
    since = datetime.now(tz=UTC) - timedelta(days=max(1, int(soak_days)))
    completed_recent = int(
        session.scalar(
            select(func.count())
            .select_from(CortexSubstratePipelineRun)
            .where(
                CortexSubstratePipelineRun.tenant_id == tenant_id,
                CortexSubstratePipelineRun.status == PIPELINE_STATUS_COMPLETED,
                CortexSubstratePipelineRun.completed_at >= since,
            )
        )
        or 0
    )
    return completed_recent > 0


def _evaluate_close_gate_met_v1() -> bool:
    try:
        import importlib

        mod = importlib.import_module(
            "vector.domains.cortex.operational_runtime.cesp_closure_gates"
        )
        verify = getattr(mod, "verify_gp085_close01_static", None)
        if verify is None:
            return False
        return bool(verify().get("passed"))
    except Exception:  # noqa: BLE001
        return False


def evaluate_multidimensional_operational_maturity_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stall_threshold_seconds: int = 1800,
) -> dict[str, Any]:
    """Full **G-P085-MAT-01** tenant maturity evaluation."""
    thresholds = get_operational_maturity_thresholds_v1()

    continuity = compute_continuity_dimension_score_v1(
        session,
        tenant_id=tenant_id,
        stall_threshold_seconds=stall_threshold_seconds,
    )
    graph = compute_graph_density_dimension_score_v1(session, tenant_id=tenant_id)
    traversal = compute_traversal_completion_dimension_score_v1(session, tenant_id=tenant_id)
    tcre = compute_tcre_saturation_dimension_score_v1(session, tenant_id=tenant_id)
    retrieval = compute_retrieval_density_dimension_score_v1(session, tenant_id=tenant_id)
    synthesis = compute_synthesis_activation_dimension_score_v1(session, tenant_id=tenant_id)

    dimension_scores = {
        DIMENSION_CONTINUITY_V1: float(continuity["score"]),
        DIMENSION_GRAPH_DENSITY_V1: float(graph["score"]),
        DIMENSION_TRAVERSAL_COMPLETION_V1: float(traversal["score"]),
        DIMENSION_TCRE_SATURATION_V1: float(tcre["score"]),
        DIMENSION_RETRIEVAL_DENSITY_V1: float(retrieval["score"]),
        DIMENSION_SYNTHESIS_ACTIVATION_V1: float(synthesis["score"]),
    }
    composite = compute_operational_confidence_score_v1(dimension_scores)
    starvation = detect_active_operational_starvation_v1(session, tenant_id=tenant_id)
    soak_met = _evaluate_production_soak_met_v1(
        session,
        tenant_id=tenant_id,
        soak_days=int(thresholds["production_soak_days"]),
    )
    close_met = _evaluate_close_gate_met_v1()

    classification = classify_operational_maturity_v1(
        dimension_scores=dimension_scores,
        operational_confidence_score=composite,
        continuity_score=float(continuity["score"]),
        retrieval_density_score=float(retrieval["score"]),
        tcre_at_least_r2=bool(tcre.get("tcre_at_least_r2")),
        active_starvation=bool(starvation["active"]),
        production_soak_met=soak_met,
        close_gate_met=close_met,
        thresholds=thresholds,
    )

    dimensions_detail = {
        DIMENSION_CONTINUITY_V1: {**continuity, "weight": MATURITY_DIMENSION_WEIGHTS_V1[DIMENSION_CONTINUITY_V1]},
        DIMENSION_GRAPH_DENSITY_V1: {**graph, "weight": MATURITY_DIMENSION_WEIGHTS_V1[DIMENSION_GRAPH_DENSITY_V1]},
        DIMENSION_TRAVERSAL_COMPLETION_V1: {
            **traversal,
            "weight": MATURITY_DIMENSION_WEIGHTS_V1[DIMENSION_TRAVERSAL_COMPLETION_V1],
        },
        DIMENSION_TCRE_SATURATION_V1: {**tcre, "weight": MATURITY_DIMENSION_WEIGHTS_V1[DIMENSION_TCRE_SATURATION_V1]},
        DIMENSION_RETRIEVAL_DENSITY_V1: {
            **retrieval,
            "weight": MATURITY_DIMENSION_WEIGHTS_V1[DIMENSION_RETRIEVAL_DENSITY_V1],
        },
        DIMENSION_SYNTHESIS_ACTIVATION_V1: {
            **synthesis,
            "weight": MATURITY_DIMENSION_WEIGHTS_V1[DIMENSION_SYNTHESIS_ACTIVATION_V1],
        },
    }

    return {
        "tenant_id": str(tenant_id),
        "gate_id": GP085_MAT01_GATE_ID_V1,
        METRIC_OPERATIONAL_CONFIDENCE_SCORE_V1: composite,
        "dimension_scores": dimension_scores,
        "dimension_weights": dict(MATURITY_DIMENSION_WEIGHTS_V1),
        "dimensions": dimensions_detail,
        "operational_starvation": starvation,
        "production_readiness": {
            "soak_met": soak_met,
            "close_gate_met": close_met,
            "soak_days_required": int(thresholds["production_soak_days"]),
        },
        **classification,
    }


def map_maturity_class_to_legacy_stage_v1(
    maturity_class: str,
    *,
    synthesis_score: float,
) -> str:
    """Map **G-P085-MAT-01** class to legacy STAGE_0–6 for backward compatibility."""
    from vector.domains.cortex.substrate_pipeline.substrate_runtime_maturity import (
        STAGE_0_IDLE,
        STAGE_1_INGESTING,
        STAGE_2_PIPELINE_RUNNING,
        STAGE_3_TCRE_ACTIVE,
        STAGE_4_RETRIEVAL_PUBLISHED,
        STAGE_5_SYNTHESIS_ACTIVE,
        STAGE_6_CONTINUOUSLY_OPERATIONAL,
    )

    if maturity_class == MATURITY_CLASS_PRODUCTION_READY_V1:
        return STAGE_6_CONTINUOUSLY_OPERATIONAL
    if maturity_class == MATURITY_CLASS_OPERATIONAL_ALIVE_V1:
        return STAGE_6_CONTINUOUSLY_OPERATIONAL if synthesis_score >= 60.0 else STAGE_5_SYNTHESIS_ACTIVE
    if maturity_class == MATURITY_CLASS_DENSITY_EMERGING_V1:
        return STAGE_4_RETRIEVAL_PUBLISHED
    if maturity_class == MATURITY_CLASS_PROGRESSING_V1:
        return STAGE_2_PIPELINE_RUNNING
    return STAGE_0_IDLE if maturity_class == MATURITY_CLASS_STRUCTURAL_ONLY_V1 else STAGE_1_INGESTING


def build_operational_maturity_card_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Operator maturity dashboard card."""
    eval_out = evaluate_multidimensional_operational_maturity_v1(session, tenant_id=tenant_id)
    return {
        "surface_kind": "operational_maturity_card",
        "gate_id": GP085_MAT01_GATE_ID_V1,
        **eval_out,
        "detail_route": f"/admin/tenants/{tenant_id}/cortex/operational-runtime/operational-maturity",
    }


def build_substrate_operational_maturity_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_operational_maturity_runtime_schema_version": int(
            PHASE085_OPERATIONAL_MATURITY_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_OPERATIONAL_MATURITY_SPEC_REF_V1,
        "primary_gate_id": GP085_MAT01_GATE_ID_V1,
        "maturity_classes": [
            MATURITY_CLASS_STRUCTURAL_ONLY_V1,
            MATURITY_CLASS_PROGRESSING_V1,
            MATURITY_CLASS_DENSITY_EMERGING_V1,
            MATURITY_CLASS_OPERATIONAL_ALIVE_V1,
            MATURITY_CLASS_PRODUCTION_READY_V1,
        ],
        "dimension_ids": list(MATURITY_DIMENSION_IDS_V1),
        "dimension_weights": dict(MATURITY_DIMENSION_WEIGHTS_V1),
        "composite_metric": METRIC_OPERATIONAL_CONFIDENCE_SCORE_V1,
        "evaluation_entrypoint": "evaluate_multidimensional_operational_maturity_v1",
        "legacy_stage_entrypoint": "evaluate_tenant_runtime_maturity_v1",
        "runtime_package": "vector.domains.cortex.operational_runtime.substrate_operational_maturity",
    }


def verify_gp085_mat01_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_substrate_operational_maturity_catalog_v1()
    if cat["primary_gate_id"] != GP085_MAT01_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")
    if abs(sum(MATURITY_DIMENSION_WEIGHTS_V1.values()) - 1.0) > 0.001:
        errors.append("dimension_weights_must_sum_to_one")

    scores = {
        DIMENSION_CONTINUITY_V1: 80.0,
        DIMENSION_GRAPH_DENSITY_V1: 70.0,
        DIMENSION_TRAVERSAL_COMPLETION_V1: 65.0,
        DIMENSION_TCRE_SATURATION_V1: 75.0,
        DIMENSION_RETRIEVAL_DENSITY_V1: 80.0,
        DIMENSION_SYNTHESIS_ACTIVATION_V1: 90.0,
    }
    composite = compute_operational_confidence_score_v1(scores)
    if composite < 70.0:
        errors.append("composite_fixture_below_expected")

    alive = classify_operational_maturity_v1(
        dimension_scores=scores,
        operational_confidence_score=composite,
        continuity_score=80.0,
        retrieval_density_score=80.0,
        tcre_at_least_r2=True,
        active_starvation=False,
        production_soak_met=False,
        close_gate_met=False,
    )
    if alive["maturity_class"] != MATURITY_CLASS_OPERATIONAL_ALIVE_V1:
        errors.append("operational_alive_classification")

    starved = classify_operational_maturity_v1(
        dimension_scores={d: 70.0 for d in MATURITY_DIMENSION_IDS_V1},
        operational_confidence_score=70.0,
        continuity_score=70.0,
        retrieval_density_score=70.0,
        tcre_at_least_r2=True,
        active_starvation=True,
        production_soak_met=True,
        close_gate_met=True,
    )
    if starved["maturity_class"] == MATURITY_CLASS_OPERATIONAL_ALIVE_V1:
        errors.append("starvation_must_block_operational_alive")

    from vector.domains.cortex.substrate_pipeline import substrate_runtime_maturity as srm

    if "evaluate_multidimensional_operational_maturity_v1" not in inspect.getsource(
        srm.evaluate_tenant_runtime_maturity_v1
    ):
        errors.append("legacy_maturity_missing_multidimensional_delegate")

    from vector.domains.cortex.substrate_pipeline import substrate_operational_health as soh

    if "evaluate_operational_health_dimensions_v1" not in inspect.getsource(
        soh.evaluate_substrate_operational_health_v1
    ):
        errors.append("operational_health_missing_health01_delegate")

    passed = not errors
    return {
        "id": GP085_MAT01_GATE_ID_V1,
        "name": "cesp_substrate_operational_maturity",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
