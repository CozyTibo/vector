"""P085-25 — Synthesis idle vs starved classification (**G-P085-SYN-02**)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.completeness.completeness_degradation_projection import (
    build_degradation_propagation_chain_v1,
)
from vector.domains.cortex.operational_runtime.cesp_synthesis_idle_starved_gate import (
    verify_gp085_synthesis_idle_starved_gate_static,
)
from vector.domains.cortex.operational_runtime.synthesis_idle_starved_classification import (
    build_synthesis_idle_classification_catalog_v1,
    verify_gp085_syn02_static,
)
from vector.domains.cortex.synthesis.synthesis_idle_classification import (
    GP085_SYN02_GATE_ID_V1,
    SYNTHESIS_CLASSIFICATION_CONTINUITY_INCOMPLETE_V1,
    SYNTHESIS_CLASSIFICATION_HEALTHY_IDLE_V1,
    SYNTHESIS_CLASSIFICATION_LEGALITY_BLOCKED_V1,
    SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1,
    SYNTHESIS_CLASSIFICATION_PROGRESSING_V1,
    SYNTHESIS_CLASSIFICATION_REPLAY_UNSAFE_V1,
    SYNTHESIS_STAGE_OMISSION_OPERATIONAL_STARVATION_V1,
    apply_synthesis_idle_classification_to_stage_v1,
    assert_synthesis_never_healthy_under_operational_starvation_v1,
    classify_synthesis_eligibility_v1,
    coerce_synthesis_substrate_state_for_classification_v1,
)
from vector.domains.cortex.synthesis.synthesis_completeness_projection import (
    project_synthesis_completeness_v1,
)
from vector.domains.cortex.synthesis.synthesis_eligibility_explainability import (
    explain_synthesis_eligibility_v1,
)


def test_synthesis_idle_catalog() -> None:
    cat = build_synthesis_idle_classification_catalog_v1()
    assert cat["primary_gate_id"] == GP085_SYN02_GATE_ID_V1
    assert cat["p0_gap_closed"] == "P0-085-05"
    assert SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1 in cat["classifications"]


def test_verify_gp085_syn02_static_passes() -> None:
    assert verify_gp085_syn02_static()["passed"] is True
    assert verify_gp085_synthesis_idle_starved_gate_static()["passed"] is True


def test_classify_operational_starvation_vs_healthy_idle() -> None:
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
    assert starved["classification"] == SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1
    assert starved["operational_starvation"] is True

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
    assert idle["classification"] == SYNTHESIS_CLASSIFICATION_HEALTHY_IDLE_V1
    assert idle["operational_starvation"] is False


def test_classify_priority_replay_legality_continuity() -> None:
    assert (
        classify_synthesis_eligibility_v1(
            eligible_scopes=5,
            synthesized_scopes=0,
            retrieval_operational_starvation=False,
            upstream_work_present=False,
            forbidden_count=0,
            forbidden_backoff_active=False,
            pipeline_waiting=False,
            pipeline_stalled=False,
            replay_unsafe=True,
        )["classification"]
        == SYNTHESIS_CLASSIFICATION_REPLAY_UNSAFE_V1
    )
    assert (
        classify_synthesis_eligibility_v1(
            eligible_scopes=5,
            synthesized_scopes=0,
            retrieval_operational_starvation=False,
            upstream_work_present=False,
            forbidden_count=2,
            forbidden_backoff_active=True,
            pipeline_waiting=False,
            pipeline_stalled=False,
            replay_unsafe=False,
        )["classification"]
        == SYNTHESIS_CLASSIFICATION_LEGALITY_BLOCKED_V1
    )
    assert (
        classify_synthesis_eligibility_v1(
            eligible_scopes=0,
            synthesized_scopes=0,
            retrieval_operational_starvation=False,
            upstream_work_present=False,
            forbidden_count=0,
            forbidden_backoff_active=False,
            pipeline_waiting=True,
            pipeline_stalled=False,
            replay_unsafe=False,
        )["classification"]
        == SYNTHESIS_CLASSIFICATION_CONTINUITY_INCOMPLETE_V1
    )
    assert (
        classify_synthesis_eligibility_v1(
            eligible_scopes=3,
            synthesized_scopes=1,
            retrieval_operational_starvation=False,
            upstream_work_present=False,
            forbidden_count=0,
            forbidden_backoff_active=False,
            pipeline_waiting=False,
            pipeline_stalled=False,
            replay_unsafe=False,
        )["classification"]
        == SYNTHESIS_CLASSIFICATION_PROGRESSING_V1
    )


def test_coerce_healthy_under_operational_starvation() -> None:
    state, drift = coerce_synthesis_substrate_state_for_classification_v1(
        substrate_state="healthy",
        classification=SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1,
    )
    assert state == "degraded"
    assert drift

    with pytest.raises(Exception):  # noqa: PT011
        assert_synthesis_never_healthy_under_operational_starvation_v1(
            classification=SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1,
            substrate_state="healthy",
        )


def test_apply_classification_to_stage_coerces_healthy() -> None:
    stage = {
        "stage_id": "synthesis",
        "substrate_state": "healthy",
        "metrics": {},
        "omission_classes": {},
        "drift_warnings": [],
    }
    context = {"eligible_scopes": 0, "retrieval_operational_starvation": True, "forbidden_count": 0}
    classification = classify_synthesis_eligibility_v1(
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
    out = apply_synthesis_idle_classification_to_stage_v1(
        stage,
        context=context,
        classification=classification,
    )
    assert out["substrate_state"] == "degraded"
    assert (
        out["omission_classes"].get(SYNTHESIS_STAGE_OMISSION_OPERATIONAL_STARVATION_V1) == 1
    )
    assert out["metrics"]["synthesis_classification"] == SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1


def test_degradation_chain_synthesis_operational_starvation() -> None:
    stages = [
        {
            "stage_id": "synthesis",
            "omission_classes": {SYNTHESIS_STAGE_OMISSION_OPERATIONAL_STARVATION_V1: 1},
        },
    ]
    chain = build_degradation_propagation_chain_v1(stages)
    assert any(
        e["propagation_consequence"] == "synthesis_operational_starvation_self_block"
        for e in chain
    )


@pytest.mark.integration
def test_explain_synthesis_eligibility_includes_classification(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085syncl-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 SYN CL",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    expl = explain_synthesis_eligibility_v1(db_session, tenant_id=tenant.id)
    assert "classification" in expl
    assert expl["classification"] in {
        SYNTHESIS_CLASSIFICATION_HEALTHY_IDLE_V1,
        SYNTHESIS_CLASSIFICATION_OPERATIONAL_STARVATION_V1,
        SYNTHESIS_CLASSIFICATION_CONTINUITY_INCOMPLETE_V1,
        SYNTHESIS_CLASSIFICATION_LEGALITY_BLOCKED_V1,
        SYNTHESIS_CLASSIFICATION_REPLAY_UNSAFE_V1,
        SYNTHESIS_CLASSIFICATION_PROGRESSING_V1,
    }
    assert "ui_color" in expl


@pytest.mark.integration
def test_project_synthesis_completeness_applies_classification(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085synpr-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 SYN PR",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    stage = project_synthesis_completeness_v1(db_session, tenant_id=tenant.id)
    assert stage["stage_id"] == "synthesis"
    metrics = dict(stage.get("metrics") or {})
    assert "synthesis_classification" in metrics
    if metrics.get("operational_starvation"):
        assert stage["substrate_state"] != "healthy"

