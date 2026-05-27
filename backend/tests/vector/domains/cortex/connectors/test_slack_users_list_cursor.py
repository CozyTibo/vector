"""Slack users.list cursor pagination helper."""

from __future__ import annotations

from unittest.mock import patch

from vector.domains.cortex.connectors.slack.ingestion_api import iter_users_list_pages


def test_iter_users_list_pages_resumes_cursor() -> None:
    calls: list[dict] = []

    def _fake_post(_token: str, method: str, *, json_body: dict, api_base: str | None = None) -> dict:
        del _token, api_base
        assert method == "users.list"
        calls.append(dict(json_body))
        if len(calls) == 1:
            return {
                "ok": True,
                "members": [{"id": "U1"}],
                "response_metadata": {"next_cursor": "cur-2"},
            }
        return {"ok": True, "members": [{"id": "U2"}], "response_metadata": {}}

    with patch(
        "vector.domains.cortex.connectors.slack.ingestion_api.slack_web_api_post",
        side_effect=_fake_post,
    ):
        out = list(iter_users_list_pages("x", max_pages=5, start_cursor="cur-1"))
    assert len(out) == 2
    assert calls[0].get("cursor") == "cur-1"
    assert calls[1].get("cursor") == "cur-2"
    assert out[0][1] == "cur-2"
    assert out[1][1] is None
    assert out[0][0][0]["id"] == "U1"
