"""P085-19 — TCRE reconstruction density metrics (**G-P085-TCRE-02**)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_tcre_density_gate import (
    verify_gp085_tcre_density_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_tcre_density import (
    GP085_TCRE02_GATE_ID_V1,
    METRIC_TCRE_DENSITY_SCORE_V1,
    METRIC_TCRE_MATERIALIZATION_TOTAL_V1,
    METRIC_TCRE_PENDING_COUNT_V1,
    METRIC_TCRE_RECONSTRUCTED_COUNT_V1,
    METRIC_TCRE_SATURATION_PERCENT_V1,
    TCRE_MATURITY_R0_V1,
    TCRE_MATURITY_R2_V1,
    TCRE_MATURITY_R3_V1,
    build_substrate_tcre_density_catalog_v1,
    build_tcre_density_card_v1,
    classify_tcre_maturity_class_v1,
    compute_tcre_density_metrics_v1,
    compute_tcre_density_score_v1,
    compute_tcre_saturation_percent_v1,
    derive_tcre_substrate_state_v1,
    verify_gp085_tcre02_static,
)


def test_tcre_density_catalog() -> None:
    cat = build_substrate_tcre_density_catalog_v1()
    assert cat["primary_gate_id"] == GP085_TCRE02_GATE_ID_V1
    assert METRIC_TCRE_DENSITY_SCORE_V1 in cat["metric_ids"]
    assert "R3" in cat["tcre_maturity_class_ids"]


def test_verify_gp085_tcre02_static_passes() -> None:
    assert verify_gp085_tcre02_static()["passed"] is True
    assert verify_gp085_tcre_density_gate_static()["passed"] is True


def test_saturation_percent_and_density_score() -> None:
    assert compute_tcre_saturation_percent_v1(
        tcre_materialization_total=200,
        tcre_reconstructed_count=50,
    ) == pytest.approx(25.0)
    assert compute_tcre_density_score_v1(tcre_saturation_percent=25.0) == 25


def test_maturity_classification() -> None:
    assert (
        classify_tcre_maturity_class_v1(tcre_saturation_percent=0.0, completed_reconstruct_jobs=0)
        == TCRE_MATURITY_R0_V1
    )
    assert (
        classify_tcre_maturity_class_v1(tcre_saturation_percent=90.0, completed_reconstruct_jobs=1)
        == TCRE_MATURITY_R3_V1
    )
    assert (
        classify_tcre_maturity_class_v1(tcre_saturation_percent=50.0, completed_reconstruct_jobs=1)
        == TCRE_MATURITY_R2_V1
    )


def test_never_run_degrades_substrate_state() -> None:
    assert (
        derive_tcre_substrate_state_v1(
            mat_total=10,
            reconstructed=0,
            reconstruction_never_run=True,
            failed_jobs=0,
            degraded_chron=0,
            pending=10,
        )
        == "degraded"
    )


@pytest.mark.integration
def test_compute_tcre_density_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085tden-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 TCRE Den",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()

    snap = compute_tcre_density_metrics_v1(db_session, tenant_id=row.id)
    assert snap["gate_id"] == GP085_TCRE02_GATE_ID_V1
    assert snap["tcre_maturity_class"] == TCRE_MATURITY_R0_V1
    metrics = snap["metrics"]
    assert metrics[METRIC_TCRE_MATERIALIZATION_TOTAL_V1] == 0
    assert metrics[METRIC_TCRE_SATURATION_PERCENT_V1] == 0.0

    card = build_tcre_density_card_v1(db_session, tenant_id=row.id)
    assert card["surface_kind"] == "tcre_density_card"
    assert METRIC_TCRE_PENDING_COUNT_V1 in card["metrics"] or card[METRIC_TCRE_PENDING_COUNT_V1] == 0
