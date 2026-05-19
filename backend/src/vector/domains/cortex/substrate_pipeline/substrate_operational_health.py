"""Live substrate operational health (continuity, density, activation)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.substrate_operational_health_dimensions import (
    GP085_HEALTH01_GATE_ID_V1,
    evaluate_operational_health_dimensions_v1,
)
from vector.domains.cortex.operational_runtime.substrate_tcre_density import (
    compute_tcre_density_metrics_v1,
)
from vector.domains.cortex.operational_runtime.substrate_tcre_omission_explainability import (
    build_tcre_omission_explainability_panel_v1,
)
from vector.domains.cortex.operational_runtime.substrate_retrieval_starvation import (
    build_retrieval_starvation_panel_v1,
    explain_retrieval_eligibility_v1,
)
from vector.domains.cortex.retrieval.retrieval_density_metrics import (
    get_retrieval_density_metrics_snapshot_v1,
)


def evaluate_substrate_operational_health_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    stall_threshold_seconds: int = 1800,
) -> dict[str, Any]:
    """Tenant operational health aggregate — delegates dimension bands to **G-P085-HEALTH-01**."""
    core = evaluate_operational_health_dimensions_v1(
        session,
        tenant_id=tenant_id,
        stall_threshold_seconds=stall_threshold_seconds,
    )
    maturity = dict(core.get("runtime_maturity") or {})
    eligibility = dict(core.get("eligibility_explanation") or {})
    retrieval_density = dict(core.get("retrieval_density_metrics") or {})
    retrieval_starvation = dict(core.get("retrieval_starvation") or {})

    tcre_density = compute_tcre_density_metrics_v1(session, tenant_id=tenant_id)
    tcre_omission_explainability = build_tcre_omission_explainability_panel_v1(
        session,
        tenant_id=tenant_id,
    )
    retrieval_starvation_panel = build_retrieval_starvation_panel_v1(session, tenant_id=tenant_id)
    retrieval_eligibility_explain = explain_retrieval_eligibility_v1(session, tenant_id=tenant_id)
    density_global = get_retrieval_density_metrics_snapshot_v1()

    return {
        "tenant_id": str(tenant_id),
        "gate_id": GP085_HEALTH01_GATE_ID_V1,
        "overall_health": core["overall_health"],
        "runtime_maturity": maturity,
        "eligibility_explanation": eligibility,
        "retrieval_density_metrics": retrieval_density,
        "retrieval_starvation": retrieval_starvation_panel,
        "retrieval_starvation_eval": retrieval_starvation,
        "retrieval_eligibility_explain": retrieval_eligibility_explain,
        "retrieval_density_global_metrics": density_global,
        "tcre_density_metrics": tcre_density,
        "tcre_omission_explainability": tcre_omission_explainability,
        "synthesis_throughput_metrics": core.get("synthesis_throughput_metrics"),
        "multidimensional_operational_maturity": core.get("multidimensional_operational_maturity"),
        "forbidden_metrics": core.get("forbidden_metrics"),
        "health_dimensions": core["health_dimensions"],
        "health_dimension_details": core["health_dimension_details"],
        "stalled_pipeline_count": core["stalled_pipeline_count"],
        "autonomous_recovery": core.get("autonomous_recovery"),
    }
