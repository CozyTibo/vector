"""Unit tests for Linear GraphQL ingestion helpers (no DB)."""

from __future__ import annotations

from vector.domains.ingestion.linear_graphql_sync import _node_activity_timestamp, _nodes_at_path


def test_nodes_at_path_nested() -> None:
    body = {
        "data": {
            "issues": {
                "nodes": [{"id": "a1"}, {"id": "b2"}],
                "pageInfo": {"hasNextPage": True, "endCursor": "b2"},
            },
        },
    }
    nodes, pi = _nodes_at_path(body["data"], ("issues",))
    assert [n["id"] for n in nodes] == ["a1", "b2"]
    assert pi["hasNextPage"] is True


def test_nodes_at_path_missing() -> None:
    nodes, pi = _nodes_at_path(None, ("teams",))
    assert nodes == []
    assert pi == {}


def test_node_activity_timestamp_prefers_updated() -> None:
    assert _node_activity_timestamp({"updatedAt": "b", "createdAt": "a"}) == "b"
    assert _node_activity_timestamp({"createdAt": "a"}) == "a"
    assert _node_activity_timestamp({}) is None
