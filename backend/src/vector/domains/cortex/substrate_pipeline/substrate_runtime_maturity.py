"""Tenant runtime maturity stages (structural legality vs operational aliveness)."""

from __future__ import annotations

import uuid
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.substrate_operational_maturity import (
    evaluate_multidimensional_operational_maturity_v1,
    map_maturity_class_to_legacy_stage_v1,
)

STAGE_0_IDLE: Final[str] = "STAGE_0_IDLE"
STAGE_1_INGESTING: Final[str] = "STAGE_1_INGESTING"
STAGE_2_PIPELINE_RUNNING: Final[str] = "STAGE_2_PIPELINE_RUNNING"
STAGE_3_TCRE_ACTIVE: Final[str] = "STAGE_3_TCRE_ACTIVE"
STAGE_4_RETRIEVAL_PUBLISHED: Final[str] = "STAGE_4_RETRIEVAL_PUBLISHED"
STAGE_5_SYNTHESIS_ACTIVE: Final[str] = "STAGE_5_SYNTHESIS_ACTIVE"
STAGE_6_CONTINUOUSLY_OPERATIONAL: Final[str] = "STAGE_6_CONTINUOUSLY_OPERATIONAL"

MATURITY_STAGES_ORDER_V1: Final[tuple[str, ...]] = (
    STAGE_0_IDLE,
    STAGE_1_INGESTING,
    STAGE_2_PIPELINE_RUNNING,
    STAGE_3_TCRE_ACTIVE,
    STAGE_4_RETRIEVAL_PUBLISHED,
    STAGE_5_SYNTHESIS_ACTIVE,
    STAGE_6_CONTINUOUSLY_OPERATIONAL,
)


def evaluate_tenant_runtime_maturity_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Classify tenant maturity — **G-P085-MAT-01** multidimensional model + legacy STAGE_0–6."""
    multi = evaluate_multidimensional_operational_maturity_v1(session, tenant_id=tenant_id)
    synthesis_score = float(
        multi.get("dimension_scores", {}).get("synthesis_activation") or 0.0
    )
    legacy_stage = map_maturity_class_to_legacy_stage_v1(
        str(multi.get("maturity_class") or ""),
        synthesis_score=synthesis_score,
    )
    dimensions = dict(multi.get("dimensions") or {})
    continuity_detail = dimensions.get("continuity") or {}

    return {
        "tenant_id": str(tenant_id),
        "maturity_stage": legacy_stage,
        "maturity_stage_ordinal": MATURITY_STAGES_ORDER_V1.index(legacy_stage),
        "maturity_class": multi.get("maturity_class"),
        "operational_confidence_score": multi.get("operational_confidence_score"),
        "dimension_scores": multi.get("dimension_scores"),
        "dimension_weights": multi.get("dimension_weights"),
        "dimensions": dimensions,
        "operational_starvation": multi.get("operational_starvation"),
        "production_readiness": multi.get("production_readiness"),
        "operationally_alive": bool(multi.get("operationally_alive")),
        "multidimensional_maturity": multi,
        "signals": {
            "ingestion_runs": None,
            "pipeline_running": continuity_detail.get("pipeline_runs_sampled", 0) > 0,
            "tcre_active_jobs": None,
            "published_index_epoch": None,
            "eligible_scopes": None,
            "completed_synthesis_jobs": None,
            "continuation_waiting": continuity_detail.get("stalled_continuations", 0) > 0,
            "phase_07_08_completion_rate": continuity_detail.get("completion_rate_percent"),
        },
        "structurally_legal_but_idle": multi.get("maturity_class") == "STRUCTURAL_ONLY",
    }
