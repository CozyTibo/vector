"""Phase 08.5 P085-25 — CESP surface for synthesis idle vs starved (**G-P085-SYN-02**).

Classification core: ``vector.domains.cortex.synthesis.synthesis_idle_classification``.
"""

from __future__ import annotations

import inspect
import uuid
from typing import Any, Final

from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.normative import (
    PHASE085_NORMATIVE_TREE_V1,
)
from vector.domains.cortex.synthesis.synthesis_idle_classification import (
    GP085_SYN02_GATE_ID_V1,
    METRIC_SYNTHESIS_CLASSIFICATION_V1,
    METRIC_SYNTHESIS_IDLE_UI_COLOR_V1,
    SYNTHESIS_CLASSIFICATION_CONTINUITY_INCOMPLETE_V1,
    SYNTHESIS_CLASSIFICATION_HEALTHY_IDLE_V1,
    SYNTHESIS_CLASSIFICATION_LEGALITY_BLOCKED_V1,
    SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1,
    SYNTHESIS_CLASSIFICATION_PROGRESSING_V1,
    SYNTHESIS_CLASSIFICATION_REPLAY_UNSAFE_V1,
    SYNTHESIS_STAGE_OMISSION_OPERATIONAL_STARVATION_V1,
    apply_synthesis_idle_classification_to_stage_v1,
    classify_synthesis_eligibility_v1,
    coerce_synthesis_substrate_state_for_classification_v1,
    evaluate_synthesis_classification_context_v1,
    project_synthesis_completeness_with_idle_classification_v1,
)

PHASE085_SYNTHESIS_IDLE_RUNTIME_SCHEMA_VERSION: Final[int] = 1

PHASE085_SYNTHESIS_IDLE_SPEC_REF_V1: Final[str] = (
    f"{PHASE085_NORMATIVE_TREE_V1}phase-085-synthesis-activation-doctrine.md"
)


def propagate_synthesis_idle_classification_stage_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """CESP propagation entry — delegates to synthesis package (**G-P085-SYN-02**)."""
    return project_synthesis_completeness_with_idle_classification_v1(
        session,
        tenant_id=tenant_id,
    )


def build_synthesis_idle_classification_panel_v1(
    session: Session,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Operator panel — synthesis idle vs starved classification."""
    from vector.domains.cortex.synthesis.synthesis_eligibility_explainability import (
        explain_synthesis_eligibility_v1,
    )

    expl = explain_synthesis_eligibility_v1(session, tenant_id=tenant_id)
    stage = propagate_synthesis_idle_classification_stage_v1(session, tenant_id=tenant_id)
    metrics = dict(stage.get("metrics") or {})
    classification = str(metrics.get(METRIC_SYNTHESIS_CLASSIFICATION_V1) or expl.get("classification"))
    messages: list[str] = []
    if classification == SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1:
        messages.append(
            "Synthesis is operationally starved — upstream produced work but no eligible scopes."
        )
    elif classification == SYNTHESIS_CLASSIFICATION_HEALTHY_IDLE_V1:
        messages.append("Synthesis is healthily idle — no eligible scopes and no upstream starvation.")
    elif classification == SYNTHESIS_CLASSIFICATION_LEGALITY_BLOCKED_V1:
        messages.append("Synthesis blocked by legality — recent synthesis_forbidden jobs detected.")
    elif classification == SYNTHESIS_CLASSIFICATION_CONTINUITY_INCOMPLETE_V1:
        messages.append("Substrate pipeline continuity incomplete — waiting or stalled.")
    elif classification == SYNTHESIS_CLASSIFICATION_REPLAY_UNSAFE_V1:
        messages.append("Synthesis replay posture unsafe — resolve replay divergence upstream.")
    elif classification == SYNTHESIS_CLASSIFICATION_PROGRESSING_V1:
        messages.append("Synthesis progressing — eligible scopes exist.")
    return {
        "panel_title": "Synthesis idle vs starved",
        "classification": classification,
        "ui_color": metrics.get(METRIC_SYNTHESIS_IDLE_UI_COLOR_V1),
        "messages": messages,
        "explanation": expl,
        "stage_card": stage,
    }


def build_synthesis_idle_classification_catalog_v1() -> dict[str, Any]:
    return {
        "surface_kind": "doctrine_catalog",
        "phase085_synthesis_idle_runtime_schema_version": int(
            PHASE085_SYNTHESIS_IDLE_RUNTIME_SCHEMA_VERSION,
        ),
        "spec_ref": PHASE085_SYNTHESIS_IDLE_SPEC_REF_V1,
        "primary_gate_id": GP085_SYN02_GATE_ID_V1,
        "classifications": [
            SYNTHESIS_CLASSIFICATION_HEALTHY_IDLE_V1,
            SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1,
            SYNTHESIS_CLASSIFICATION_LEGALITY_BLOCKED_V1,
            SYNTHESIS_CLASSIFICATION_CONTINUITY_INCOMPLETE_V1,
            SYNTHESIS_CLASSIFICATION_REPLAY_UNSAFE_V1,
            SYNTHESIS_CLASSIFICATION_PROGRESSING_V1,
        ],
        "synthesis_stage_omission_classes": [SYNTHESIS_STAGE_OMISSION_OPERATIONAL_STARVATION_V1],
        "explain_entrypoint": "explain_synthesis_eligibility_v1",
        "propagation_entrypoint": "propagate_synthesis_idle_classification_stage_v1",
        "classification_package": "vector.domains.cortex.synthesis.synthesis_idle_classification",
        "p0_gap_closed": "P0-085-05",
        "runtime_package": (
            "vector.domains.cortex.operational_runtime.synthesis_idle_starved_classification"
        ),
    }


def verify_gp085_syn02_static() -> dict[str, Any]:
    errors: list[str] = []
    cat = build_synthesis_idle_classification_catalog_v1()
    if cat["primary_gate_id"] != GP085_SYN02_GATE_ID_V1:
        errors.append("primary_gate_id_mismatch")

    starved = classify_synthesis_eligibility_v1(
        eligible_scopes=0,
        synthesized_scopes=0,
        retrieval_operational_starvation=True,
        upstream_work_present=True,
        forbidden_count=0,
        forbidden_backoff_active=False,
        pipeline_waiting=False,
        pipeline_stalled=False,
        replay_unsafe=False,
    )
    if starved["classification"] != SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1:
        errors.append("operational_starvation_classification")

    idle = classify_synthesis_eligibility_v1(
        eligible_scopes=0,
        synthesized_scopes=0,
        retrieval_operational_starvation=False,
        upstream_work_present=False,
        forbidden_count=0,
        forbidden_backoff_active=False,
        pipeline_waiting=False,
        pipeline_stalled=False,
        replay_unsafe=False,
    )
    if idle["classification"] != SYNTHESIS_CLASSIFICATION_HEALTHY_IDLE_V1:
        errors.append("healthy_idle_classification")

    coerced, _ = coerce_synthesis_substrate_state_for_classification_v1(
        substrate_state="healthy",
        classification=SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1,
    )
    if coerced != "degraded":
        errors.append("healthy_coercion_under_starvation")

    from vector.domains.cortex.synthesis import synthesis_completeness_projection as scp
    from vector.domains.cortex.synthesis import synthesis_throughput_maturity as stm

    proj_src = inspect.getsource(scp.project_synthesis_completeness_v1)
    if (
        "project_synthesis_completeness_with_idle_classification_v1" not in proj_src
        and "project_synthesis_completeness_with_throughput_maturity_v1" not in proj_src
    ):
        errors.append("synthesis_completeness_projection_missing_idle_or_throughput_delegate")
    if "project_synthesis_completeness_with_idle_classification_v1" not in inspect.getsource(
        stm.project_synthesis_completeness_with_throughput_maturity_v1
    ):
        errors.append("throughput_missing_idle_classification_chain")

    from vector.domains.cortex.synthesis import synthesis_eligibility_explainability as see

    expl_src = inspect.getsource(see.explain_synthesis_eligibility_v1)
    if "classification" not in expl_src:
        errors.append("explain_synthesis_eligibility_missing_classification")

    from vector.domains.cortex.completeness import completeness_degradation_projection as cdp

    rules_src = inspect.getsource(cdp)
    if SYNTHESIS_STAGE_OMISSION_OPERATIONAL_STARVATION_V1 not in rules_src:
        errors.append("degradation_chain_missing_synthesis_operational_starvation")

    upstream = __import__(
        "vector.domains.cortex.operational_runtime.phase_boundaries",
        fromlist=["list_upstream_packages_importing_cesp_violations_v1"],
    ).list_upstream_packages_importing_cesp_violations_v1()
    if upstream:
        errors.append(f"acyclic_upstream_cesp_imports:{upstream[:3]}")

    passed = not errors
    return {
        "id": GP085_SYN02_GATE_ID_V1,
        "name": "cesp_synthesis_idle_starved_classification",
        "passed": passed,
        "severity": "hard_fail",
        "detail": {"errors": errors},
    }
