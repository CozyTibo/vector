"""P085-10 — Graph density metrics (**G-P085-GRAPH-01**)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_graph_density_gate import (
    verify_gp085_graph_density_gate_static,
)
from vector.domains.cortex.operational_runtime.graph_density import (
    GP085_GRAPH01_GATE_ID_V1,
    GRAPH_MATURITY_STAGE_G3_V1,
    METRIC_GRAPH_CONNECTIVITY_RATIO_V1,
    METRIC_GRAPH_DENSITY_SCORE_V1,
    build_graph_density_catalog_v1,
    classify_graph_maturity_stage_v1,
    compute_graph_connectivity_ratio_v1,
    compute_graph_density_metrics_v1,
    compute_graph_density_score_v1,
    evaluate_graph_density_fake_green_v1,
    verify_gp085_graph01_static,
)


def test_graph_density_catalog() -> None:
    cat = build_graph_density_catalog_v1()
    assert cat["primary_gate_id"] == GP085_GRAPH01_GATE_ID_V1
    assert "graph_density_score" in cat["metric_ids"]
    assert "G3" in cat["graph_maturity_stage_ids"]


def test_verify_gp085_graph01_static_passes() -> None:
    assert verify_gp085_graph01_static()["passed"] is True
    assert verify_gp085_graph_density_gate_static()["passed"] is True


def test_connectivity_ratio_formula() -> None:
    assert compute_graph_connectivity_ratio_v1(
        graph_promoted_edge_count=70,
        graph_orphan_artifact_count=30,
    ) == pytest.approx(0.7)


def test_maturity_g3_when_connected_and_no_pending() -> None:
    stage = classify_graph_maturity_stage_v1(
        entity_count=100,
        graph_orphan_artifact_count=5,
        graph_connectivity_ratio=0.8,
        pending_link_candidates=0,
    )
    assert stage == GRAPH_MATURITY_STAGE_G3_V1


def test_fake_green_blocks_healthy_when_orphans_and_pending() -> None:
    out = evaluate_graph_density_fake_green_v1(
        graph_orphan_artifact_count=50,
        pending_link_candidates=100,
        substrate_state="healthy",
        pending_threshold=10,
    )
    assert out["fake_green_blocked"] is True
    assert out["would_block_healthy_substrate_state"] is True


def test_density_score_bounded() -> None:
    score = compute_graph_density_score_v1(
        graph_connectivity_ratio=0.5,
        graph_candidate_count=100,
        graph_promoted_edge_count=20,
        pending_link_candidates=50,
    )
    assert 0 <= score <= 100


@pytest.fixture
def tenant(db_session: Session) -> Any:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085graph-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Graph Density Tenant",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()
    return row


@pytest.mark.integration
def test_compute_graph_density_metrics_empty_tenant(
    db_session: Session,
    tenant: Any,
) -> None:
    out = compute_graph_density_metrics_v1(db_session, tenant_id=tenant.id)
    assert out["gate_id"] == GP085_GRAPH01_GATE_ID_V1
    assert out["metrics"][METRIC_GRAPH_CONNECTIVITY_RATIO_V1] == 0.0
    assert out["metrics"][METRIC_GRAPH_DENSITY_SCORE_V1] >= 0
    assert "graph_maturity_stage" in out
