"""GitHub ingestion REST pagination wrappers (Phase 01 Step 9)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from vector.domains.cortex.connectors.github import http_client


def test_list_repo_pulls_page_forwards_page_and_per_page(monkeypatch: Any) -> None:
    seen: dict[str, Any] = {}

    def _fake_array(
        settings: Any,
        token: str,
        *,
        path: str,
        params: dict[str, Any] | None = None,
        timeout: float = 60.0,
    ) -> list[dict[str, Any]]:
        seen["token"] = token
        seen["path"] = path
        seen["params"] = dict(params or {})
        return [{"number": 1}]

    monkeypatch.setattr(http_client, "_github_rest_array", _fake_array)
    out = http_client.list_repo_pulls_page(
        SimpleNamespace(),
        "inst-token",
        owner="acme",
        repo="vector",
        page=3,
        per_page=75,
    )
    assert out == [{"number": 1}]
    assert seen["token"] == "inst-token"
    assert seen["path"] == "/repos/acme/vector/pulls"
    assert seen["params"]["page"] == 3
    assert seen["params"]["per_page"] == 75


def test_list_repo_workflow_runs_page_extracts_workflow_runs(monkeypatch: Any) -> None:
    def _fake_object(
        settings: Any,
        token: str,
        *,
        path: str,
        params: dict[str, Any] | None = None,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        assert path == "/repos/acme/vector/actions/runs"
        assert params is not None and params["page"] == 2
        return {"total_count": 4, "workflow_runs": [{"id": 11}, {"id": 12}]}

    monkeypatch.setattr(http_client, "_github_rest_object", _fake_object)
    rows, total = http_client.list_repo_workflow_runs_page(
        SimpleNamespace(),
        "inst-token",
        owner="acme",
        repo="vector",
        page=2,
    )
    assert total == 4
    assert [r["id"] for r in rows] == [11, 12]


def test_list_repo_check_runs_page_extracts_check_runs(monkeypatch: Any) -> None:
    def _fake_object(
        settings: Any,
        token: str,
        *,
        path: str,
        params: dict[str, Any] | None = None,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        assert path == "/repos/acme/vector/commits/deadbeef/check-runs"
        return {"total_count": 1, "check_runs": [{"id": 99}]}

    monkeypatch.setattr(http_client, "_github_rest_object", _fake_object)
    rows, total = http_client.list_repo_check_runs_page(
        SimpleNamespace(),
        "inst-token",
        owner="acme",
        repo="vector",
        ref="deadbeef",
        page=1,
    )
    assert total == 1
    assert rows == [{"id": 99}]
