"""P085-21 — retrieval density maturity (**G-P085-RET-01**)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_retrieval_density_gate import (
    verify_gp085_retrieval_density_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_retrieval_density import (
    GP085_RET01_GATE_ID_V1,
    METRIC_RETRIEVAL_DENSITY_PERCENT_V1,
    METRIC_RETRIEVAL_DENSITY_SCORE_V1,
    METRIC_RETRIEVAL_INDEXED_COUNT_V1,
    RETRIEVAL_MATURITY_RET0_V1,
    RETRIEVAL_MATURITY_RET3_V1,
    build_substrate_retrieval_density_catalog_v1,
    build_retrieval_density_card_v1,
    classify_retrieval_maturity_class_v1,
    compute_retrieval_density_metrics_v1,
    compute_retrieval_density_percent_v1,
    compute_retrieval_density_score_v1,
    derive_retrieval_density_substrate_state_v1,
    verify_gp085_ret01_static,
)
from vector.domains.cortex.retrieval.retrieval_skip_registry import (
    RET_SKIP_WALK_INCOMPLETE_V1,
    normalize_retrieval_skip_reason_v1,
)


def test_retrieval_density_catalog() -> None:
    cat = build_substrate_retrieval_density_catalog_v1()
    assert cat["primary_gate_id"] == GP085_RET01_GATE_ID_V1
    assert cat["skip_code_prefix"] == "RET-SKIP-"
    assert METRIC_RETRIEVAL_DENSITY_SCORE_V1 in cat["metric_ids"]


def test_verify_gp085_ret01_static_passes() -> None:
    assert verify_gp085_ret01_static()["passed"] is True
    assert verify_gp085_retrieval_density_gate_static()["passed"] is True


def test_density_percent_and_score() -> None:
    assert compute_retrieval_density_percent_v1(
        retrieval_indexed_count=25,
        retrieval_eligible_artifact_count=100,
    ) == pytest.approx(25.0)
    assert compute_retrieval_density_score_v1(retrieval_density_percent=25.0) == 25


def test_maturity_classification() -> None:
    assert (
        classify_retrieval_maturity_class_v1(
            retrieval_density_percent=0.0,
            published_index_epoch=None,
        )
        == RETRIEVAL_MATURITY_RET0_V1
    )
    assert (
        classify_retrieval_maturity_class_v1(
            retrieval_density_percent=90.0,
            published_index_epoch="epoch-1",
        )
        == RETRIEVAL_MATURITY_RET3_V1
    )


def test_eligible_unindexed_degrades() -> None:
    assert (
        derive_retrieval_density_substrate_state_v1(
            eligible=5,
            indexed=0,
            published_epoch=None,
        )
        == "degraded"
    )


def test_ret_skip_normalization_required_keys() -> None:
    row = normalize_retrieval_skip_reason_v1(source="walk", code="walk_incomplete")
    assert row["ret_skip_code"] == RET_SKIP_WALK_INCOMPLETE_V1
    assert row["upstream_code"] == "walk_incomplete"
    assert "replay_safe" in row


@pytest.mark.integration
def test_compute_retrieval_density_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085retden-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Ret Den",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()

    snap = compute_retrieval_density_metrics_v1(db_session, tenant_id=row.id)
    assert snap["gate_id"] == GP085_RET01_GATE_ID_V1
    assert snap["retrieval_maturity_class"] == RETRIEVAL_MATURITY_RET0_V1
    metrics = snap["metrics"]
    assert metrics[METRIC_RETRIEVAL_INDEXED_COUNT_V1] == 0
    assert metrics[METRIC_RETRIEVAL_DENSITY_PERCENT_V1] == 0.0

    card = build_retrieval_density_card_v1(db_session, tenant_id=row.id)
    assert card["surface_kind"] == "retrieval_density_card"
