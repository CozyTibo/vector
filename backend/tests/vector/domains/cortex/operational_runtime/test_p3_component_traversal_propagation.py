"""P1-A — P3′ component-scoped traversal propagation (Phase 1 step 1.1)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from vector.domains.cortex.operational_runtime.graph_completeness_propagation import (
    build_graph_completeness_propagation_manifest_v1,
    derive_graph_completeness_substrate_state_v1,
)
from vector.domains.cortex.operational_runtime.graph_density import (
    GRAPH_MATURITY_STAGE_G1_V1,
    METRIC_GRAPH_DENSITY_SCORE_V1,
)
from vector.domains.cortex.operational_runtime.graph_orphan_continuity import (
    ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    TRAVERSAL_PROPAGATION_MODE_COMPONENT_V1,
    TRAVERSAL_PROPAGATION_MODE_GLOBAL_V1,
    TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
    _is_traversal_propagation_blocked_global_v1,
    evaluate_traversal_propagation_v1,
    evaluate_traversal_schedule_v1,
    list_eligible_traversal_components_v1,
)


def test_global_law_blocks_disconnected_orphans_with_linked_mass() -> None:
    assert _is_traversal_propagation_blocked_global_v1(
        linked_entity_count=216,
        entity_count=7286,
        orphan_disconnected_count=7070,
        orphan_identity_unresolved_count=0,
    )


def test_component_law_unblocks_fizzer_like_islands(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    island = frozenset({uuid.uuid4(), uuid.uuid4()})

    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling."
        "is_component_traversal_schedule_enabled_v1",
        lambda: True,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling."
        "list_eligible_traversal_components_v1",
        lambda *_a, **_k: [island],
    )

    out = evaluate_traversal_propagation_v1(
        session,
        tenant_id=tid,
        linked_entity_count=216,
        entity_count=7286,
        orphan_disconnected_count=7070,
        orphan_identity_unresolved_count=0,
    )
    assert out["traversal_propagation_mode"] == TRAVERSAL_PROPAGATION_MODE_COMPONENT_V1
    assert out["islands_eligible_count"] == 1
    assert out["traversal_propagation_blocked"] is False


def test_component_law_blocks_when_no_eligible_islands(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling."
        "is_component_traversal_schedule_enabled_v1",
        lambda: True,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling."
        "list_eligible_traversal_components_v1",
        lambda *_a, **_k: [],
    )
    out = evaluate_traversal_propagation_v1(
        session,
        tenant_id=tid,
        linked_entity_count=10,
        entity_count=100,
        orphan_disconnected_count=90,
        orphan_identity_unresolved_count=0,
    )
    assert out["traversal_propagation_blocked"] is True
    assert out["islands_eligible_count"] == 0


def test_evaluate_schedule_eligible_under_p3_prime(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    island = frozenset({uuid.uuid4(), uuid.uuid4()})

    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.graph_density.compute_graph_density_metrics_v1",
        lambda *_a, **_k: {
            "graph_maturity_stage": GRAPH_MATURITY_STAGE_G1_V1,
            "metrics": {
                "entity_count": 7286,
                "linked_entity_count": 216,
                METRIC_GRAPH_DENSITY_SCORE_V1: 40,
                "pending_link_candidates": 0,
            },
        },
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.graph_orphan_continuity.classify_tenant_graph_orphans_v1",
        lambda *_a, **_k: {
            "counts_by_class": {ORPHAN_CLASS_DISCONNECTED_COMPONENT_V1: 7070},
        },
    )
    monkeypatch.setattr(
        "vector.domains.cortex.traversal.runtime.durable_walk_store.resolve_octs_walk_store_v1",
        lambda *_a, **_k: MagicMock(walk_queue_depth_for_tenant=lambda _t: 0),
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling."
        "list_eligible_traversal_components_v1",
        lambda *_a, **_k: [island],
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling."
        "is_component_traversal_schedule_enabled_v1",
        lambda: True,
    )

    out = evaluate_traversal_schedule_v1(
        session,
        tenant_id=tid,
        trigger=TRAVERSAL_SCHEDULE_TRIGGER_AFTER_PHASE_05_V1,
    )
    assert out["should_schedule"] is True
    assert out["traversal_propagation_blocked"] is False
    assert out["islands_eligible_count"] == 1


def test_propagation_manifest_includes_component_fields() -> None:
    manifest = build_graph_completeness_propagation_manifest_v1(
        substrate_state="healthy",
        fake_green_evaluation={"fake_green_blocked": False},
        orphan_classification={"orphan_entity_count": 7070, "counts_by_class": {}},
        traversal_propagation_blocked=False,
        traversal_propagation={
            "traversal_propagation_mode": TRAVERSAL_PROPAGATION_MODE_COMPONENT_V1,
            "islands_eligible_count": 3,
            "traversal_propagation_block_reason": "component_islands_eligible",
        },
    )
    assert manifest["traversal_propagation_mode"] == TRAVERSAL_PROPAGATION_MODE_COMPONENT_V1
    assert manifest["islands_eligible_count"] == 3
    assert manifest["traversal_propagation_blocked"] is False


def test_substrate_state_not_degraded_by_disconnect_when_islands_eligible() -> None:
    global_state = derive_graph_completeness_substrate_state_v1(
        entity_count=7286,
        linked_entities=216,
        orphan_count=100,
        link_count=400,
        candidate_count=100,
        pending_candidates=0,
        graph_maturity_stage="G1",
        fake_green_blocked=False,
        orphan_disconnected_count=7070,
        orphan_identity_unresolved_count=0,
        islands_eligible_count=0,
        traversal_propagation_mode=TRAVERSAL_PROPAGATION_MODE_GLOBAL_V1,
    )
    component_state = derive_graph_completeness_substrate_state_v1(
        entity_count=7286,
        linked_entities=216,
        orphan_count=100,
        link_count=400,
        candidate_count=100,
        pending_candidates=0,
        graph_maturity_stage="G1",
        fake_green_blocked=False,
        orphan_disconnected_count=7070,
        orphan_identity_unresolved_count=0,
        islands_eligible_count=2,
        traversal_propagation_mode=TRAVERSAL_PROPAGATION_MODE_COMPONENT_V1,
    )
    assert global_state == "degraded"
    assert component_state == "healthy"


def test_list_eligible_filters_small_components(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    tid = uuid.uuid4()
    e1, e2, e3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling."
        "list_graph_connected_components_v1",
        lambda *_a, **_k: [frozenset({e1, e2}), frozenset({e3})],
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling."
        "get_traversal_min_component_entities_v1",
        lambda: 2,
    )
    eligible = list_eligible_traversal_components_v1(session, tenant_id=tid)
    assert len(eligible) == 1
    assert len(eligible[0]) == 2
