"""P085-28 — Operational health dimensions (**G-P085-HEALTH-01**)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_operational_health_gate import (
    verify_gp085_operational_health_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_operational_health_dimensions import (
    GP085_HEALTH01_GATE_ID_V1,
    HEALTH_BAND_CRITICAL_V1,
    HEALTH_BAND_DEGRADED_V1,
    HEALTH_BAND_HEALTHY_V1,
    HEALTH_DIM_ORCHESTRATION_PROGRESS_V1,
    HEALTH_DIM_RETRIEVAL_DENSITY_V1,
    HEALTH_DIM_SUBSTRATE_CONTINUITY_V1,
    HEALTH_DIM_SYNTHESIS_ACTIVATION_V1,
    HEALTH_DIMENSION_IDS_V1,
    build_substrate_operational_health_catalog_v1,
    evaluate_async_resume_health_v1,
    evaluate_multidimensional_maturity_health_v1,
    evaluate_operational_health_dimensions_v1,
    evaluate_orchestration_progress_health_v1,
    evaluate_retrieval_density_health_v1,
    evaluate_substrate_continuity_health_v1,
    evaluate_synthesis_activation_health_v1,
    evaluate_synthesis_throughput_health_v1,
    verify_gp085_health01_static,
    worst_health_band_v1,
)
from vector.domains.cortex.substrate_pipeline.pipeline_continuation import (
    CONTINUATION_STATUS_STALLED,
    CONTINUATION_STATUS_WAITING,
)
from vector.domains.cortex.substrate_pipeline.substrate_operational_health import (
    evaluate_substrate_operational_health_v1,
)
from vector.domains.cortex.substrate_pipeline.substrate_runtime_maturity import (
    STAGE_3_TCRE_ACTIVE,
)


def test_operational_health_catalog() -> None:
    cat = build_substrate_operational_health_catalog_v1()
    assert cat["primary_gate_id"] == GP085_HEALTH01_GATE_ID_V1
    assert len(cat["health_bands"]) == 3
    assert set(cat["dimension_ids"]) == set(HEALTH_DIMENSION_IDS_V1)


def test_verify_gp085_health01_static_passes() -> None:
    assert verify_gp085_health01_static()["passed"] is True
    assert verify_gp085_operational_health_gate_static()["passed"] is True


def test_continuity_health_bands() -> None:
    healthy = evaluate_substrate_continuity_health_v1(
        continuation_status=None,
        stalled_continuation_count=0,
    )
    assert healthy["band"] == HEALTH_BAND_HEALTHY_V1

    waiting = evaluate_substrate_continuity_health_v1(
        continuation_status=CONTINUATION_STATUS_WAITING,
        stalled_continuation_count=0,
    )
    assert waiting["band"] == HEALTH_BAND_DEGRADED_V1

    stalled = evaluate_substrate_continuity_health_v1(
        continuation_status=CONTINUATION_STATUS_STALLED,
        stalled_continuation_count=1,
    )
    assert stalled["band"] == HEALTH_BAND_CRITICAL_V1


def test_retrieval_density_health_bands() -> None:
    assert (
        evaluate_retrieval_density_health_v1(
            indexed_count=5,
            index_stale=False,
            operational_starvation=False,
            empty_publish=False,
        )["band"]
        == HEALTH_BAND_HEALTHY_V1
    )
    assert (
        evaluate_retrieval_density_health_v1(
            indexed_count=0,
            index_stale=False,
            operational_starvation=False,
            empty_publish=True,
        )["band"]
        == HEALTH_BAND_DEGRADED_V1
    )
    assert (
        evaluate_retrieval_density_health_v1(
            indexed_count=0,
            index_stale=True,
            operational_starvation=True,
            empty_publish=True,
        )["band"]
        == HEALTH_BAND_CRITICAL_V1
    )


def test_synthesis_activation_forbidden_critical() -> None:
    out = evaluate_synthesis_activation_health_v1(
        synthesis_ready=False,
        eligible_scopes=0,
        forbidden_backoff_active=True,
        classification="legality_blocked",
    )
    assert out["band"] == HEALTH_BAND_CRITICAL_V1


def test_orchestration_progress_pipeline_failed() -> None:
    out = evaluate_orchestration_progress_health_v1(
        maturity_stage=STAGE_3_TCRE_ACTIVE,
        maturity_class="PROGRESSING",
        pipeline_failed_recent=True,
        operationally_alive=False,
    )
    assert out["band"] == HEALTH_BAND_CRITICAL_V1


def test_worst_health_band() -> None:
    assert worst_health_band_v1([HEALTH_BAND_HEALTHY_V1, HEALTH_BAND_DEGRADED_V1]) == HEALTH_BAND_DEGRADED_V1
    assert worst_health_band_v1([HEALTH_BAND_HEALTHY_V1, HEALTH_BAND_CRITICAL_V1]) == HEALTH_BAND_CRITICAL_V1


def test_async_resume_missing_continuation() -> None:
    out = evaluate_async_resume_health_v1(
        running_pipeline=True,
        continuation_present=False,
        pipeline_waiting_on_tcre=False,
        duplicate_stall_signals=0,
    )
    assert out["band"] == HEALTH_BAND_CRITICAL_V1


def test_throughput_and_maturity_health_units() -> None:
    throughput = evaluate_synthesis_throughput_health_v1(
        all_throughput_targets_met=True,
        eligible_scopes=0,
        synthesis_classification="healthy_idle",
    )
    assert throughput["band"] == HEALTH_BAND_HEALTHY_V1

    maturity = evaluate_multidimensional_maturity_health_v1(
        maturity_class="OPERATIONAL_ALIVE",
        operationally_alive=True,
        active_starvation=False,
    )
    assert maturity["band"] == HEALTH_BAND_HEALTHY_V1


@pytest.mark.integration
def test_evaluate_operational_health_dimensions_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085health-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 HEALTH",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    dims = evaluate_operational_health_dimensions_v1(db_session, tenant_id=tenant.id)
    assert dims["gate_id"] == GP085_HEALTH01_GATE_ID_V1
    assert set(dims["health_dimensions"].keys()) == set(HEALTH_DIMENSION_IDS_V1)
    assert dims["overall_health"] in {
        HEALTH_BAND_HEALTHY_V1,
        HEALTH_BAND_DEGRADED_V1,
        HEALTH_BAND_CRITICAL_V1,
    }
    assert HEALTH_DIM_SUBSTRATE_CONTINUITY_V1 in dims["health_dimension_details"]
    assert HEALTH_DIM_RETRIEVAL_DENSITY_V1 in dims["health_dimension_details"]
    assert HEALTH_DIM_SYNTHESIS_ACTIVATION_V1 in dims["health_dimension_details"]
    assert HEALTH_DIM_ORCHESTRATION_PROGRESS_V1 in dims["health_dimension_details"]


@pytest.mark.integration
def test_substrate_operational_health_delegates_health01(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085healthagg-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(
        company_name="P085 HEALTH AGG",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(tenant)
    db_session.flush()

    out = evaluate_substrate_operational_health_v1(db_session, tenant_id=tenant.id)
    assert out["gate_id"] == GP085_HEALTH01_GATE_ID_V1
    assert "health_dimension_details" in out
    assert "tcre_density_metrics" in out
    assert "overall_health" in out
