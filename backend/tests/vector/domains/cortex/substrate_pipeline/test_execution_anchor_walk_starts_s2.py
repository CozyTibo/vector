"""Phase S2.5 — execution-anchor walk start selection."""

from __future__ import annotations

import uuid

from vector.domains.cortex.substrate_pipeline import substrate_traversal_execution as ste


def test_org_entity_ids_in_projection_filters_kind() -> None:
    inner = {
        "nodes": [
            {"kind": "org_entity", "id": "e1"},
            {"kind": "github.repository", "id": "r1"},
            {"kind": "org_entity", "id": "e2"},
        ]
    }
    assert ste._org_entity_ids_in_projection_v1(inner) == {"e1", "e2"}


def test_pick_execution_anchor_prefers_canonical_mat_entities(monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    inner = {
        "nodes": [
            {"kind": "org_entity", "id": "fallback-only"},
            {"kind": "org_entity", "id": "anchor-a"},
            {"kind": "org_entity", "id": "anchor-b"},
        ]
    }

    def _fake_exec_entities(session, *, tenant_id, limit):  # noqa: ANN001, ARG001
        return ["anchor-b", "anchor-a"]

    monkeypatch.setattr(
        ste,
        "org_entity_ids_for_execution_materializations_v1",
        _fake_exec_entities,
    )
    starts, count = ste._pick_execution_anchor_start_node_ids_v1(
        None,  # type: ignore[arg-type]
        tenant_id=tenant_id,
        projection_inner=inner,
        limit=2,
    )
    assert starts == ["anchor-b", "anchor-a"]
    assert count == 2


def test_pick_execution_anchor_falls_back_when_no_mat_overlap(monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    inner = {"nodes": [{"kind": "org_entity", "id": "only-node"}]}

    monkeypatch.setattr(
        ste,
        "org_entity_ids_for_execution_materializations_v1",
        lambda session, *, tenant_id, limit: ["missing"],  # noqa: ARG005
    )
    starts, count = ste._pick_execution_anchor_start_node_ids_v1(
        None,  # type: ignore[arg-type]
        tenant_id=tenant_id,
        projection_inner=inner,
        limit=1,
    )
    assert starts == ["only-node"]
    assert count == 0
