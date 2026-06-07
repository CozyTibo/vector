"""Linear sync must not mark issue backfill complete on GraphQL auth failures."""

from __future__ import annotations

from vector.domains.cortex.ingestion.connectors.linear.sync import _linear_graphql_page_failed


def test_linear_graphql_page_failed_on_http_401() -> None:
    assert _linear_graphql_page_failed(401, {}) is True


def test_linear_graphql_page_failed_on_graphql_errors() -> None:
    assert _linear_graphql_page_failed(200, {"errors": [{"message": "auth"}]}) is True


def test_linear_graphql_page_failed_false_on_success() -> None:
    assert _linear_graphql_page_failed(200, {"data": {"issues": {"nodes": []}}}) is False
