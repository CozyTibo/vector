"""Tests for Manager insights Step 1 fetch bundle assembly."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from vector.contracts.manager_insights_activity import ConnectorFetchResult
from vector.domains.manager_insights import fetch_activity as mod


def _fake_result(connector: str, *, window_start: datetime, window_end: datetime) -> ConnectorFetchResult:
    return ConnectorFetchResult(
        connector=connector,  # type: ignore[arg-type]
        status="ok",
        fetched_at=window_end,
        window_start=window_start,
        window_end=window_end,
        caps_applied=[],
        errors=[],
        payload={"probe": True},
    )


def test_run_fetch_activity_bundle_includes_all_connectors(monkeypatch: Any) -> None:
    fixed_end = datetime(2026, 1, 20, 0, 0, 0, tzinfo=UTC)
    tenant_id = uuid.uuid4()

    def _patch(connector: str):
        def _fn(*args: Any, **kwargs: Any) -> ConnectorFetchResult:
            return _fake_result(
                connector,
                window_start=kwargs["window_start"],
                window_end=kwargs["window_end"],
            )

        return _fn

    monkeypatch.setattr(mod, "_fetch_slack", _patch("slack"))
    monkeypatch.setattr(mod, "_fetch_github", _patch("github"))
    monkeypatch.setattr(mod, "_fetch_linear", _patch("linear"))
    monkeypatch.setattr(mod, "_fetch_notion", _patch("notion"))
    monkeypatch.setattr(mod, "_fetch_calls", _patch("calls"))

    bundle = mod.run_fetch_activity_bundle(
        session=object(),  # type: ignore[arg-type]
        settings=SimpleNamespace(),
        tenant_id=tenant_id,
        window_days=30,
        as_of=fixed_end,
    )
    assert bundle.tenant_id == tenant_id
    assert sorted(bundle.connectors.keys()) == ["calls", "github", "linear", "notion", "slack"]
    assert bundle.connectors["slack"].window_end == fixed_end
    assert bundle.connectors["slack"].window_start < fixed_end


def test_notion_title_extraction_handles_user_named_title_property() -> None:
    row = {
        "id": "abc",
        "properties": {
            "Name": {
                "id": "title",
                "type": "title",
                "title": [{"plain_text": "V0 - Teammate Report"}],
            }
        },
    }
    assert mod._notion_result_title(row) == "V0 - Teammate Report"


def test_run_fetch_activity_bundle_mock_mode_builds_full_company_payload(monkeypatch: Any) -> None:
    tenant_id = uuid.uuid4()
    fixed_end = datetime(2026, 1, 20, 0, 0, 0, tzinfo=UTC)
    in_window = "2026-01-10T10:00:00Z"
    dataset = {
        "github": {
            "repos": [{"id": 1, "full_name": "nexora/api"}],
            "pull_requests": [
                {
                    "number": 42,
                    "title": "Implement NEX-42",
                    "body": "Closes NEX-42",
                    "state": "closed",
                    "html_url": "https://github.com/nexora/api/pull/42",
                    "created_at": in_window,
                    "updated_at": in_window,
                    "closed_at": in_window,
                    "_repo_full": "nexora/api",
                    "user": {"login": "thagler"},
                }
            ],
            "issues": [],
        },
        "linear": {
            "projects": [{"id": "p1", "name": "API"}],
            "issues": [
                {
                    "id": "lin-1",
                    "identifier": "NEX-42",
                    "title": "Rollout cache fix",
                    "description": "Need to ship this week",
                    "createdAt": in_window,
                    "updatedAt": in_window,
                    "state": {"name": "Done"},
                    "project": {"name": "API"},
                    "assignee": {"name": "Thibault"},
                }
            ],
        },
        "slack_events": [
            {
                "channel": "#eng-core",
                "text": "Follow up on NEX-42",
                "ts": in_window,
                "user_email": "thibault@nexora.dev",
            }
        ],
        "notion": {
            "has_more": False,
            "users_me_ok": True,
            "sampled_pages": [
                {
                    "id": "page-1",
                    "url": "https://notion.so/page-1",
                    "title": "NEX-42 spec",
                    "owner": "Thibault",
                    "last_edited_time": in_window,
                    "snippet": "Execution notes",
                }
            ],
        },
        "calls": {
            "sampled_events": [
                {
                    "calendar_id": "eng-team@nexora.dev",
                    "id": "call-1",
                    "summary": "NEX-42 handoff",
                    "description": "Need to ship this week",
                    "status": "confirmed",
                    "html_link": "https://meet.google.com/abc-defg-hij",
                    "organizer_email": "manager@nexora.dev",
                    "created": in_window,
                    "updated": in_window,
                    "start": in_window,
                    "end": "2026-01-10T11:00:00Z",
                }
            ]
        },
    }

    class _Resp:
        status_code = 200

        def __init__(self, payload: dict[str, Any]) -> None:
            self._payload = payload

        def json(self) -> dict[str, Any]:
            return self._payload

    monkeypatch.setattr(mod.httpx, "get", lambda *args, **kwargs: _Resp(dataset))

    bundle = mod.run_fetch_activity_bundle(
        session=object(),  # type: ignore[arg-type]
        settings=SimpleNamespace(
            vector_use_mock_connectors=True,
            vector_mock_connector_base_url="http://mock-connectors:9183",
        ),
        tenant_id=tenant_id,
        window_days=30,
        as_of=fixed_end,
    )
    assert sorted(bundle.connectors.keys()) == ["calls", "github", "linear", "notion", "slack"]
    assert bundle.connectors["slack"].status == "ok"
    assert bundle.connectors["slack"].payload["sampled_channel_messages"]
    assert bundle.connectors["github"].payload["sampled_pull_requests"][0]["number"] == 42
    assert bundle.connectors["linear"].payload["sampled_issues"][0]["identifier"] == "NEX-42"
    assert bundle.connectors["notion"].payload["sampled_pages"][0]["id"] == "page-1"
    assert bundle.connectors["calls"].payload["sampled_events"][0]["id"] == "call-1"
