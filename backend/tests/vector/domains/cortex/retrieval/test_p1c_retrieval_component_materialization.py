"""P1-C — component-scoped retrieval materialization unit tests."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from vector.domains.cortex.retrieval.retrieval_component_materialization import (
    RETRIEVAL_PROPAGATION_MODE_COMPONENT_V1,
    org_link_within_island_v1,
    select_largest_eligible_island_v1,
    walk_record_intersects_island_v1,
)


class _FakeWalk:
    def __init__(self, *, walk_id: uuid.UUID, status: str, payload: dict) -> None:
        self.walk_id = walk_id
        self.status = status
        self.walk_payload = payload


def test_walk_record_intersects_island_by_start_nodes() -> None:
    e1 = uuid.uuid4()
    e2 = uuid.uuid4()
    island = frozenset({e1})
    record = _FakeWalk(
        walk_id=uuid.uuid4(),
        status="completed",
        payload={"walk_request": {"start_node_ids": [str(e1), str(e2)]}},
    )
    assert walk_record_intersects_island_v1(record, island) is True
    unrelated = frozenset({uuid.uuid4()})
    assert walk_record_intersects_island_v1(record, unrelated) is False


def test_org_link_within_island_requires_both_endpoints() -> None:
    e1, e2, e3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    island = frozenset({e1, e2})

    class _Link:
        source_entity_id = e1
        target_entity_id = e2

    assert org_link_within_island_v1(_Link(), island) is True
    _Link2 = type("_L", (), {"source_entity_id": e1, "target_entity_id": e3})()
    assert org_link_within_island_v1(_Link2, island) is False


@pytest.mark.integration
def test_materialize_pipeline_dispatches_to_component_when_enabled(db_session) -> None:
    """When P1-C enabled, pipeline materialization uses component mode."""
    from vector.domains.cortex.retrieval.retrieval_index_materialization import (
        materialize_retrieval_index_for_pipeline_v1,
    )

    tenant_id = uuid.uuid4()
    pipeline_run_id = uuid.uuid4()
    island = frozenset({uuid.uuid4(), uuid.uuid4()})
    fake_stats = {
        "retrieval_propagation_mode": RETRIEVAL_PROPAGATION_MODE_COMPONENT_V1,
        "entries_materialized": 3,
        "ok": True,
        "build_state": "PUBLISHED",
        "island_entity_count": 2,
    }
    with (
        patch(
            "vector.domains.cortex.retrieval.retrieval_component_materialization.is_retrieval_component_scope_enabled_v1",
            return_value=True,
        ),
        patch(
            "vector.domains.cortex.retrieval.retrieval_index_materialization.materialize_retrieval_index_for_largest_island_v1",
            return_value=fake_stats,
        ) as mock_island,
    ):
        out = materialize_retrieval_index_for_pipeline_v1(
            db_session,
            tenant_id=tenant_id,
            pipeline_run_id=pipeline_run_id,
        )
    mock_island.assert_called_once()
    assert out["retrieval_propagation_mode"] == RETRIEVAL_PROPAGATION_MODE_COMPONENT_V1


def test_select_largest_island_picks_max_component() -> None:
    c_small = frozenset({uuid.uuid4()})
    c_large = frozenset({uuid.uuid4(), uuid.uuid4(), uuid.uuid4()})
    with patch(
        "vector.domains.cortex.retrieval.retrieval_component_materialization.list_eligible_traversal_components_v1",
        return_value=[c_small, c_large],
    ):
        island, meta = select_largest_eligible_island_v1(None, tenant_id=uuid.uuid4())  # type: ignore[arg-type]
    assert island == c_large
    assert meta["largest_island_entity_count"] == 3
    assert meta["islands_eligible_count"] == 2
