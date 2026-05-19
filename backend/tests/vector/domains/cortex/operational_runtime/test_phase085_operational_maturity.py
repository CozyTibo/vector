"""P085-27 — Multi-dimensional operational maturity (**G-P085-MAT-01**)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_operational_maturity_gate import (
    verify_gp085_operational_maturity_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_operational_maturity import (
    DIMENSION_CONTINUITY_V1,
    DIMENSION_GRAPH_DENSITY_V1,
    DIMENSION_RETRIEVAL_DENSITY_V1,
    DIMENSION_SYNTHESIS_ACTIVATION_V1,
    DIMENSION_TCRE_SATURATION_V1,
    DIMENSION_TRAVERSAL_COMPLETION_V1,
    GP085_MAT01_GATE_ID_V1,
    MATURITY_CLASS_DENSITY_EMERGING_V1,
    MATURITY_CLASS_OPERATIONAL_ALIVE_V1,
    MATURITY_CLASS_PROGRESSING_V1,
    MATURITY_CLASS_PRODUCTION_READY_V1,
    MATURITY_CLASS_STRUCTURAL_ONLY_V1,
    MATURITY_DIMENSION_IDS_V1,
    MATURITY_DIMENSION_WEIGHTS_V1,
    build_substrate_operational_maturity_catalog_v1,
    classify_operational_maturity_v1,
    compute_operational_confidence_score_v1,
    map_maturity_class_to_legacy_stage_v1,
    verify_gp085_mat01_static,
)
from vector.domains.cortex.substrate_pipeline.substrate_runtime_maturity import (
    STAGE_0_IDLE,
    STAGE_4_RETRIEVAL_PUBLISHED,
    STAGE_6_CONTINUOUSLY_OPERATIONAL,
    evaluate_tenant_runtime_maturity_v1,
)


def test_operational_maturity_catalog() -> None:
    cat = build_substrate_operational_maturity_catalog_v1()
    assert cat["primary_gate_id"] == GP085_MAT01_GATE_ID_V1
    assert len(cat["maturity_classes"]) == 5
    assert set(cat["dimension_weights"].keys()) == set(MATURITY_DIMENSION_IDS_V1)
    assert abs(sum(MATURITY_DIMENSION_WEIGHTS_V1.values()) - 1.0) < 0.001


def test_verify_gp085_mat01_static_passes() -> None:
    assert verify_gp085_mat01_static()["passed"] is True
    assert verify_gp085_operational_maturity_gate_static()["passed"] is True


def test_composite_score_weighted_sum() -> None:
    scores = {d: 80.0 for d in MATURITY_DIMENSION_IDS_V1}
    composite = compute_operational_confidence_score_v1(scores)
    assert composite == 80.0


def test_classify_operational_alive() -> None:
    scores = {d: 75.0 for d in MATURITY_DIMENSION_IDS_V1}
    out = classify_operational_maturity_v1(
        dimension_scores=scores,
        operational_confidence_score=75.0,
        continuity_score=75.0,
        retrieval_density_score=75.0,
        tcre_at_least_r2=True,
        active_starvation=False,
        production_soak_met=False,
        close_gate_met=False,
    )
    assert out["maturity_class"] == MATURITY_CLASS_OPERATIONAL_ALIVE_V1
    assert out["operationally_alive"] is True


def test_classify_starvation_blocks_operational_alive() -> None:
    scores = {d: 80.0 for d in MATURITY_DIMENSION_IDS_V1}
    out = classify_operational_maturity_v1(
        dimension_scores=scores,
        operational_confidence_score=80.0,
        continuity_score=80.0,
        retrieval_density_score=80.0,
        tcre_at_least_r2=True,
        active_starvation=True,
        production_soak_met=True,
        close_gate_met=True,
    )
    assert out["maturity_class"] != MATURITY_CLASS_OPERATIONAL_ALIVE_V1
    assert out["maturity_class"] != MATURITY_CLASS_PRODUCTION_READY_V1


def test_classify_progressing_and_density_emerging() -> None:
    scores = {d: 30.0 for d in MATURITY_DIMENSION_IDS_V1}
    structural = classify_operational_maturity_v1(
        dimension_scores=scores,
        operational_confidence_score=30.0,
        continuity_score=20.0,
        retrieval_density_score=20.0,
        tcre_at_least_r2=False,
        active_starvation=False,
        production_soak_met=False,
        close_gate_met=False,
    )
    assert structural["maturity_class"] == MATURITY_CLASS_STRUCTURAL_ONLY_V1

    progressing = classify_operational_maturity_v1(
        dimension_scores=scores,
        operational_confidence_score=45.0,
        continuity_score=50.0,
        retrieval_density_score=20.0,
        tcre_at_least_r2=False,
        active_starvation=False,
        production_soak_met=False,
        close_gate_met=False,
    )
    assert progressing["maturity_class"] == MATURITY_CLASS_PROGRESSING_V1

    density = classify_operational_maturity_v1(
        dimension_scores=scores,
        operational_confidence_score=50.0,
        continuity_score=50.0,
        retrieval_density_score=50.0,
        tcre_at_least_r2=True,
        active_starvation=False,
        production_soak_met=False,
        close_gate_met=False,
    )
    assert density["maturity_class"] == MATURITY_CLASS_DENSITY_EMERGING_V1


def test_map_maturity_class_to_legacy_stage() -> None:
    assert map_maturity_class_to_legacy_stage_v1(
        MATURITY_CLASS_PRODUCTION_READY_V1,
        synthesis_score=50.0,
    ) == STAGE_6_CONTINUOUSLY_OPERATIONAL
    assert map_maturity_class_to_legacy_stage_v1(
        MATURITY_CLASS_OPERATIONAL_ALIVE_V1,
        synthesis_score=80.0,
    ) == STAGE_6_CONTINUOUSLY_OPERATIONAL
    assert map_maturity_class_to_legacy_stage_v1(
        MATURITY_CLASS_DENSITY_EMERGING_V1,
        synthesis_score=0.0,
    ) == STAGE_4_RETRIEVAL_PUBLISHED
    assert map_maturity_class_to_legacy_stage_v1(
        MATURITY_CLASS_STRUCTURAL_ONLY_V1,
        synthesis_score=0.0,
    ) == STAGE_0_IDLE


@pytest.mark.integration
def test_evaluate_tenant_runtime_maturity_multidimensional(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085mat-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 MAT",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    out = evaluate_tenant_runtime_maturity_v1(db_session, tenant_id=tenant.id)
    assert out["maturity_class"] in {
        MATURITY_CLASS_STRUCTURAL_ONLY_V1,
        MATURITY_CLASS_PROGRESSING_V1,
        MATURITY_CLASS_DENSITY_EMERGING_V1,
        MATURITY_CLASS_OPERATIONAL_ALIVE_V1,
        MATURITY_CLASS_PRODUCTION_READY_V1,
    }
    assert "operational_confidence_score" in out
    assert DIMENSION_CONTINUITY_V1 in out["dimension_scores"]
    assert DIMENSION_GRAPH_DENSITY_V1 in out["dimension_scores"]
    assert DIMENSION_TRAVERSAL_COMPLETION_V1 in out["dimension_scores"]
    assert DIMENSION_TCRE_SATURATION_V1 in out["dimension_scores"]
    assert DIMENSION_RETRIEVAL_DENSITY_V1 in out["dimension_scores"]
    assert DIMENSION_SYNTHESIS_ACTIVATION_V1 in out["dimension_scores"]
    assert "multidimensional_maturity" in out
