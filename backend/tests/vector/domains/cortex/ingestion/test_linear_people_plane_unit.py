"""Unit tests for Linear people plane (no database)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

import vector.domains.cortex.ingestion.connectors.linear.sync as linear_sync
from vector.domains.cortex.ingestion.sync_context import IngestionSyncContext


def test_sync_linear_people_plane_writes_user_team_rows(monkeypatch) -> None:
    settings = SimpleNamespace(
        cortex_linear_projects_max_pages_per_sync=5,
        cortex_linear_stream_first=50,
        cortex_linear_time_budget_seconds=3600.0,
        linear_graphql_url=lambda: "https://api.linear.app/graphql",
    )
    ctx = IngestionSyncContext.live_incremental()
    session = MagicMock()
    written: list[str] = []

    def _fake_append(*_a, resource_type: str, **_k) -> bool:
        written.append(resource_type)
        return True

    def _fake_graphql(
        _settings: object,
        _token: str,
        *,
        operation_name: str,
        query: str,
        root_field: str,
        first: int,
        after: str | None,
    ) -> tuple[int, dict, list, dict]:
        del query, first, after
        if operation_name == "LinearIngestUsers":
            return 200, {}, [{"id": "u1", "name": "Ada"}], {"hasNextPage": False, "endCursor": None}
        if operation_name == "LinearIngestTeams":
            return (
                200,
                {},
                [{"id": "t1", "name": "Eng", "members": {"nodes": [{"id": "u1"}]}}],
                {"hasNextPage": False, "endCursor": None},
            )
        return 200, {}, [], {"hasNextPage": False, "endCursor": None}

    monkeypatch.setattr(linear_sync, "append_raw", _fake_append)
    monkeypatch.setattr(linear_sync, "linear_graphql_connection_page", _fake_graphql)

    n, patch = linear_sync._sync_linear_people_plane(
        session,
        settings,
        ctx=ctx,
        tenant_id=uuid.uuid4(),
        connection_id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        source_trigger="test",
        token="tok",
        linear_existing={},
        start_t=0.0,
    )
    assert n >= 3
    assert "linear.user" in written
    assert "linear.team" in written
    assert "linear.team_membership" in written
    assert "users" in patch
    assert patch["users"].get("introduced_at")
