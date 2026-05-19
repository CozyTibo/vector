"""P085-17 — Traversal density + explainability (**G-P085-WALK-04**)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_traversal_explainability_gate import (
    verify_gp085_traversal_explainability_gate_static,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_explainability import (
    GP085_WALK04_GATE_ID_V1,
    METRIC_TRAVERSAL_DENSITY_SCORE_V1,
    METRIC_WALKS_COMPLETED_RATE_V1,
    METRIC_WALKS_PENDING_GAUGE_V1,
    build_substrate_traversal_explainability_catalog_v1,
    build_traversal_explainability_panel_v1,
    compute_traversal_density_metrics_v1,
    explain_walk_early_termination_v1,
    explain_walk_replay_posture_v1,
    verify_gp085_walk04_static,
)
from vector.domains.cortex.traversal.walk_api_contract import WalkApiRecordV1


def test_traversal_explainability_catalog() -> None:
    cat = build_substrate_traversal_explainability_catalog_v1()
    assert cat["primary_gate_id"] == GP085_WALK04_GATE_ID_V1
    assert cat["panel_entrypoint"] == "build_traversal_explainability_panel_v1"
    assert METRIC_TRAVERSAL_DENSITY_SCORE_V1 in cat["metric_ids"]


def test_verify_gp085_walk04_static_passes() -> None:
    assert verify_gp085_walk04_static()["passed"] is True
    assert verify_gp085_traversal_explainability_gate_static()["passed"] is True


def test_explain_walk_early_termination_completed() -> None:
    rec = WalkApiRecordV1(
        walk_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        status="completed",
        request_body={"start_node_ids": ["n1"]},
        walk_payload={
            "walk_result": {
                "hash_body": {
                    "termination_reason": "frontier_exhausted",
                    "hop_receipts": [{"h": 1}],
                }
            },
            "telemetry": {"hops_emitted": 1},
        },
    )
    out = explain_walk_early_termination_v1(rec)
    assert out["terminated_early"] is False
    assert out["termination_reason"] == "frontier_exhausted"


def test_explain_walk_early_termination_budget_exhausted() -> None:
    rec = WalkApiRecordV1(
        walk_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        status="completed",
        request_body={},
        walk_payload={
            "walk_result": {
                "hash_body": {
                    "termination_reason": "budget_exhausted",
                    "hop_receipts": [],
                }
            },
            "telemetry": {"hops_emitted": 0},
        },
    )
    out = explain_walk_early_termination_v1(rec)
    assert out["terminated_early"] is True
    assert out["cesp_failure_class"] == "frontier_collapse"


@pytest.mark.integration
def test_build_traversal_explainability_panel_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085expl-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Explain",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()

    panel = build_traversal_explainability_panel_v1(db_session, tenant_id=row.id)
    assert panel["gate_id"] == GP085_WALK04_GATE_ID_V1
    assert METRIC_WALKS_COMPLETED_RATE_V1 in panel["metrics"]
    assert METRIC_WALKS_PENDING_GAUGE_V1 in panel["metrics"]
    assert METRIC_TRAVERSAL_DENSITY_SCORE_V1 in panel["metrics"]
    assert "why_walks_pending" in panel
    assert "upstream_graph_omissions" in panel
    assert "per_walk_explanations" in panel
    assert panel["why_walks_pending"][0]["code"] == "no_pending_walks"

    metrics = compute_traversal_density_metrics_v1(db_session, tenant_id=row.id)
    assert metrics["eligible_graph_frontiers"] >= 1
    assert metrics[METRIC_TRAVERSAL_DENSITY_SCORE_V1] >= 0.0


@pytest.mark.integration
def test_explain_walk_replay_posture_no_row(db_session: Session) -> None:
    tid = uuid.uuid4()
    rec = WalkApiRecordV1(
        walk_id=uuid.uuid4(),
        tenant_id=tid,
        status="completed",
        request_body={},
        walk_payload={
            "walk_result": {
                "hash_body": {"termination_reason": "frontier_exhausted", "hop_receipts": []}
            }
        },
    )
    out = explain_walk_replay_posture_v1(db_session, tenant_id=tid, record=rec)
    assert out["replay_legality_posture"] == "replay_safe"
