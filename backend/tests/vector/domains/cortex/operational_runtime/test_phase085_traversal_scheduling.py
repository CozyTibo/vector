"""P085-14 — Automatic OCTS walk scheduling (**G-P085-WALK-01**)."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from vector.domains.cortex.operational_runtime.cesp_traversal_scheduling_gate import (
    verify_gp085_traversal_scheduling_gate_static,
)
from vector.domains.cortex.operational_runtime.graph_density import (
    GRAPH_MATURITY_STAGE_G1_V1,
    METRIC_GRAPH_DENSITY_SCORE_V1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    CELERY_TRAVERSAL_SCHEDULE_TASK_NAME_V1,
    GP085_WALK01_GATE_ID_V1,
    TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
    _is_traversal_propagation_blocked_v1,
    build_substrate_traversal_scheduling_catalog_v1,
    evaluate_traversal_schedule_v1,
    rank_walk_frontiers_by_density_v1,
    schedule_octs_walks_for_tenant_v1,
    verify_gp085_walk01_static,
)


def test_traversal_scheduling_catalog() -> None:
    cat = build_substrate_traversal_scheduling_catalog_v1()
    assert cat["primary_gate_id"] == GP085_WALK01_GATE_ID_V1
    assert cat["scheduler_entrypoint"] == "schedule_octs_walks_for_tenant_v1"
    assert cat["max_walks_per_pass"] == 32


def test_verify_gp085_walk01_static_passes() -> None:
    assert verify_gp085_walk01_static()["passed"] is True
    assert verify_gp085_traversal_scheduling_gate_static()["passed"] is True


def test_traversal_propagation_blocked_when_disconnected() -> None:
    assert _is_traversal_propagation_blocked_v1(
        linked_entity_count=10,
        entity_count=20,
        orphan_disconnected_count=3,
        orphan_identity_unresolved_count=0,
    )


def test_evaluate_schedule_after_phase_05_g1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.graph_density.compute_graph_density_metrics_v1",
        lambda *_a, **_k: {
            "graph_maturity_stage": GRAPH_MATURITY_STAGE_G1_V1,
            "metrics": {
                "entity_count": 10,
                "linked_entity_count": 5,
                METRIC_GRAPH_DENSITY_SCORE_V1: 40,
                "pending_link_candidates": 0,
            },
        },
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.graph_orphan_continuity.classify_tenant_graph_orphans_v1",
        lambda *_a, **_k: {"counts_by_class": {}},
    )
    monkeypatch.setattr(
        "vector.domains.cortex.traversal.runtime.durable_walk_store.resolve_octs_walk_store_v1",
        lambda *_a, **_k: MagicMock(walk_queue_depth_for_tenant=lambda _t: 0),
    )
    out = evaluate_traversal_schedule_v1(
        session,
        tenant_id=tid,
        trigger=TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
    )
    assert out["should_schedule"] is True


def test_rank_frontiers_from_components(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    e1, e2, e3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.graph_density.compute_graph_density_metrics_v1",
        lambda *_a, **_k: {
            "graph_maturity_stage": GRAPH_MATURITY_STAGE_G1_V1,
            "metrics": {METRIC_GRAPH_DENSITY_SCORE_V1: 50, "entity_count": 3},
        },
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling.list_graph_connected_components_v1",
        lambda *_a, **_k: [frozenset({e1, e2}), frozenset({e3})],
    )
    starts, meta = rank_walk_frontiers_by_density_v1(session, tenant_id=tid, limit=2)
    assert len(starts) == 2
    assert meta["connected_component_count"] == 2


def test_schedule_octs_walks_runs_inline(monkeypatch: pytest.MonkeyPatch) -> None:
    tid = uuid.uuid4()

    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling."
        "run_octs_walk_schedule_pass_v1",
        lambda *_a, **_k: {"gate_id": "G-P085-WALK-01", "scheduled": True},
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling."
        "evaluate_traversal_schedule_v1",
        lambda *_a, **_k: {"should_schedule": True, "schedule_reason": "test"},
    )
    out = schedule_octs_walks_for_tenant_v1(tenant_id=tid, force=True)
    assert out["scheduled"] is True
    assert out["path"] == "inline_execution_slice"
    assert "pass" in out


@pytest.mark.integration
def test_run_octs_walk_schedule_pass_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.tenant import Tenant

    slug = f"p085walk-{uuid.uuid4().hex[:8]}"
    row = Tenant(
        company_name="P085 Walk",
        primary_email=f"{slug}@example.com",
        email_domain="example.com",
        slug=slug,
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add(row)
    db_session.flush()

    from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
        run_octs_walk_schedule_pass_v1,
    )

    out = run_octs_walk_schedule_pass_v1(db_session, tenant_id=row.id)
    assert out["gate_id"] == GP085_WALK01_GATE_ID_V1
    assert out["scheduled"] is False or "materialization" in out
