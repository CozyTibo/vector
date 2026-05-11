"""Slack ingestion API pagination helpers (Phase 01 Step 8)."""

from __future__ import annotations

from typing import Any

from vector.domains.cortex.connectors.slack import ingestion_api


def test_iter_conversations_history_pages_uses_next_cursor(monkeypatch: Any) -> None:
    calls: list[dict[str, Any]] = []
    payloads = [
        {
            "ok": True,
            "messages": [{"ts": "1715000000.000100"}],
            "response_metadata": {"next_cursor": "c1"},
            "has_more": True,
        },
        {
            "ok": True,
            "messages": [{"ts": "1715000001.000100"}],
            "response_metadata": {"next_cursor": ""},
            "has_more": False,
        },
    ]

    def _fake_post(
        token: str,
        method: str,
        *,
        json_body: dict[str, Any],
        api_base: str | None = None,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        del api_base, timeout
        assert token == "xoxb-test"
        assert method == "conversations.history"
        calls.append(dict(json_body))
        return payloads.pop(0)

    monkeypatch.setattr(ingestion_api, "slack_web_api_post", _fake_post)
    pages = list(
        ingestion_api.iter_conversations_history_pages(
            "xoxb-test",
            channel="C123",
            limit=200,
            max_pages=5,
            oldest="1714000000.000000",
        )
    )

    assert len(pages) == 2
    assert calls[0]["channel"] == "C123"
    assert calls[0]["oldest"] == "1714000000.000000"
    assert "cursor" not in calls[0]
    assert calls[1]["cursor"] == "c1"


def test_iter_conversations_replies_pages_passes_thread_context(monkeypatch: Any) -> None:
    calls: list[dict[str, Any]] = []
    payloads = [
        {
            "ok": True,
            "messages": [{"ts": "1715000002.000100"}],
            "response_metadata": {"next_cursor": "r1"},
            "has_more": True,
        },
        {
            "ok": True,
            "messages": [{"ts": "1715000003.000100"}],
            "response_metadata": {"next_cursor": ""},
            "has_more": False,
        },
    ]

    def _fake_post(
        token: str,
        method: str,
        *,
        json_body: dict[str, Any],
        api_base: str | None = None,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        del api_base, timeout
        assert token == "xoxb-test"
        assert method == "conversations.replies"
        calls.append(dict(json_body))
        return payloads.pop(0)

    monkeypatch.setattr(ingestion_api, "slack_web_api_post", _fake_post)
    pages = list(
        ingestion_api.iter_conversations_replies_pages(
            "xoxb-test",
            channel="C123",
            thread_ts="1715000000.000100",
            limit=200,
            max_pages=4,
        )
    )

    assert len(pages) == 2
    assert calls[0]["channel"] == "C123"
    assert calls[0]["ts"] == "1715000000.000100"
    assert "cursor" not in calls[0]
    assert calls[1]["cursor"] == "r1"
