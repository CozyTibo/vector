"""P2-B — execution event triggers."""

from __future__ import annotations

import uuid

import pytest

from vector.domains.cortex.execution.execution_event_triggers import (
    DETAIL_KEY_LAST_GRAPH_HASH_V1,
    trigger_graph_hash_walk_schedule_v1,
)
from vector.domains.cortex.operational_runtime.substrate_traversal_scheduling import (
    TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_HASH_CHANGED_V1,
    build_substrate_traversal_scheduling_catalog_v1,
    evaluate_traversal_schedule_v1,
)


def test_catalog_includes_graph_hash_changed_trigger() -> None:
    catalog = build_substrate_traversal_scheduling_catalog_v1()
    assert TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_HASH_CHANGED_V1 in catalog["schedule_triggers"]


def test_graph_hash_trigger_eval_not_blocked_when_eligible(monkeypatch) -> None:
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling."
        "classify_tenant_graph_orphans_v1",
        lambda *_a, **_k: {
            "linked_entity_count": 10,
            "counts_by_class": {},
        },
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling."
        "compute_graph_density_metrics_v1",
        lambda *_a, **_k: {
            "metrics": {"entity_count": 10, "linked_entity_count": 10},
            "graph_maturity_stage": "G1",
        },
    )
    monkeypatch.setattr(
        "vector.domains.cortex.operational_runtime.substrate_traversal_scheduling."
        "evaluate_traversal_propagation_v1",
        lambda *_a, **_k: {
            "traversal_propagation_blocked": False,
            "islands_eligible_count": 2,
        },
    )
    monkeypatch.setattr(
        "vector.domains.cortex.traversal.runtime.durable_walk_store.resolve_octs_walk_store_v1",
        lambda *_a, **_k: type("S", (), {"walk_queue_depth_for_tenant": lambda _self, _t: 0})(),
    )

    class _Sess:
        pass

    out = evaluate_traversal_schedule_v1(
        _Sess(),
        tenant_id=uuid.uuid4(),
        trigger=TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_HASH_CHANGED_V1,
    )
    assert out["should_schedule"] is True
    assert out["schedule_reason"] == "graph_hash_changed_eligible"


def test_trigger_graph_hash_detects_change_without_db(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hash-change detection and schedule hook (schedule mocked)."""
    scheduled: list[dict] = []

    def _fake_schedule(**kwargs: object) -> dict:
        scheduled.append(dict(kwargs))
        return {"scheduled": True, "path": "inline_execution_slice"}

    class _Lease:
        detail_json: dict = {}

    lease = _Lease()
    monkeypatch.setattr(
        "vector.domains.cortex.execution.execution_event_triggers."
        "get_tenant_execution_lease_v1",
        lambda *_a, **_k: lease,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.execution.execution_event_triggers."
        "schedule_octs_walks_for_tenant_v1",
        _fake_schedule,
    )
    monkeypatch.setattr(
        "vector.domains.cortex.execution.execution_event_triggers."
        "is_execution_event_triggers_enabled_v1",
        lambda: True,
    )
    session = type("S", (), {"flush": lambda *_a, **_k: None})()
    tenant_id = uuid.uuid4()
    out = trigger_graph_hash_walk_schedule_v1(
        session,
        tenant_id=tenant_id,
        graph_projection_stable_hash="hash-a",
    )
    assert out["hash_changed"] is True
    assert scheduled[0]["trigger"] == TRAVERSAL_SCHEDULE_TRIGGER_GRAPH_HASH_CHANGED_V1
    out2 = trigger_graph_hash_walk_schedule_v1(
        session,
        tenant_id=tenant_id,
        graph_projection_stable_hash="hash-a",
    )
    assert out2["hash_changed"] is False
    assert len(scheduled) == 1
    assert lease.detail_json.get(DETAIL_KEY_LAST_GRAPH_HASH_V1) == "hash-a"
