"""Linear canonical mapper — lightweight behavior checks (no DB required)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from vector.domains.canonical.linear_mapper import handle_linear_canonical_row
from vector.infrastructure.db.repositories.ingestion import CONNECTOR_LINEAR


def test_handle_linear_skips_non_linear_connector() -> None:
    session = MagicMock()
    raw = SimpleNamespace(connector="github", http_status=200, resource_type="x")
    handle_linear_canonical_row(session, raw)
    assert not session.mock_calls


def test_handle_linear_skips_bad_http_status() -> None:
    session = MagicMock()
    raw = SimpleNamespace(
        connector=CONNECTOR_LINEAR,
        http_status=500,
        resource_type="x",
    )
    handle_linear_canonical_row(session, raw)
    assert not session.mock_calls
