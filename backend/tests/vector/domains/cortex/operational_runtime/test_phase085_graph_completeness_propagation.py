"""P085-13 — Graph completeness propagation (**G-P085-GRAPH-PROP-01**)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.completeness.completeness_degradation_projection import (
    build_degradation_propagation_chain_v1,
)
from vector.domains.cortex.completeness.graph_completeness_projection import (
    _derive_graph_substrate_state_v1,
    project_graph_completeness_v1,
)
from vector.domains.cortex.operational_runtime.cesp_graph_propagation_gate import (
    verify_gp085_graph_propagation_gate_static,
)
from vector.domains.cortex.operational_runtime.graph_completeness_propagation import (
    GP085_GRAPH_PROP01_GATE_ID_V1,
    ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1,
    build_graph_completeness_propagation_catalog_v1,
    derive_graph_completeness_substrate_state_v1,
    propagate_graph_completeness_stage_v1,
    verify_gp085_graph_prop01_static,
)
from vector.domains.cortex.operational_runtime.graph_density import (
    METRIC_GRAPH_CANDIDATE_COUNT_V1,
    METRIC_GRAPH_CONNECTIVITY_RATIO_V1,
    METRIC_GRAPH_DENSITY_SCORE_V1,
    METRIC_GRAPH_ORPHAN_ARTIFACT_COUNT_V1,
    METRIC_GRAPH_PROMOTED_EDGE_COUNT_V1,
)
from vector.domains.cortex.operational_runtime.graph_orphan_continuity import (
    ORPHAN_CLASS_AWAITING_PROMOTION_V1,
)


def test_propagation_catalog() -> None:
    cat = build_graph_completeness_propagation_catalog_v1()
    assert cat["primary_gate_id"] == GP085_GRAPH_PROP01_GATE_ID_V1
    assert cat["p0_gap_closed"] == "P0-085-02"
    assert ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1 in cat["graph_stage_omission_classes"]


def test_verify_gp085_graph_prop01_static_passes() -> None:
    assert verify_gp085_graph_prop01_static()["passed"] is True
    assert verify_gp085_graph_propagation_gate_static()["passed"] is True


def test_derive_substrate_all_orphans_degraded() -> None:
    assert (
        derive_graph_completeness_substrate_state_v1(
            entity_count=100,
            linked_entities=0,
            orphan_count=100,
            link_count=0,
            candidate_count=0,
            pending_candidates=0,
            graph_maturity_stage="G0",
            fake_green_blocked=False,
            orphan_disconnected_count=0,
            orphan_identity_unresolved_count=0,
        )
        == "degraded"
    )


def test_derive_substrate_fake_green_forces_degraded() -> None:
    assert (
        derive_graph_completeness_substrate_state_v1(
            entity_count=50,
            linked_entities=40,
            orphan_count=10,
            link_count=30,
            candidate_count=100,
            pending_candidates=100,
            graph_maturity_stage="G2",
            fake_green_blocked=True,
            orphan_disconnected_count=0,
            orphan_identity_unresolved_count=0,
        )
        == "degraded"
    )


def test_legacy_derive_wrapper_matches() -> None:
    assert (
        _derive_graph_substrate_state_v1(
            entity_count=100,
            linked_entities=0,
            orphan_count=100,
            link_count=0,
            candidate_count=0,
        )
        == "degraded"
    )


def test_degradation_chain_propagates_orphan_disconnected_to_traversal() -> None:
    stages = [
        {
            "stage_id": "graph",
            "omission_classes": {ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1: 5},
        },
        {"stage_id": "traversal", "omission_classes": {}},
    ]
    chain = build_degradation_propagation_chain_v1(stages)
    assert any(
        e["from_stage"] == "graph"
        and e["to_stage"] == "traversal"
        and e["triggering_omission_class"] == ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1
        for e in chain
    )


def test_graph_projection_includes_density_score_and_propagation_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tid = uuid.uuid4()
    session = MagicMock()
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.graph_density.compute_graph_density_metrics_v1",
        lambda *_a, **_k: {
            "graph_maturity_stage": "G0",
            "metrics": {
                "entity_count": 50,
                "linked_entity_count": 0,
                METRIC_GRAPH_PROMOTED_EDGE_COUNT_V1: 0,
                METRIC_GRAPH_CANDIDATE_COUNT_V1: 20,
                METRIC_GRAPH_ORPHAN_ARTIFACT_COUNT_V1: 50,
                METRIC_GRAPH_CONNECTIVITY_RATIO_V1: 0.0,
                METRIC_GRAPH_DENSITY_SCORE_V1: 12,
                "pending_link_candidates": 20,
            },
        },
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.graph_orphan_continuity.classify_tenant_graph_orphans_v1",
        lambda *_a, **_k: {
            "orphan_entity_count": 50,
            "counts_by_class": {
                ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1: 50,
                ORPHAN_CLASS_AWAITING_PROMOTION_V1: 0,
            },
        },
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling."
        "list_eligible_traversal_components_v1",
        lambda *_a, **_k: [],
    )
    out = project_graph_completeness_v1(session, tenant_id=tid)
    assert out["substrate_state"] == "degraded"
    assert out["metrics"]["graph_density_score"] == 12
    manifest = out["metrics"]["graph_completeness_propagation"]
    assert manifest["gate_id"] == GP085_GRAPH_PROP01_GATE_ID_V1
    assert manifest["traversal_propagation_blocked"] is True
    assert out["omission_classes"][ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1] == 50


@pytest.mark.integration
def test_propagate_graph_completeness_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085prop-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Prop",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()

    out = propagate_graph_completeness_stage_v1(db_session, tenant_id=row.id)
    assert out["stage_id"] == "graph"
    assert out["substrate_state"] == "critical"
    assert "graph_density_score" in out["metrics"]


@pytest.fixture
def tenant(db_session: Session) -> Any:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085prop2-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Prop 2",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()
    return row
