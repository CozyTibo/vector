"""Unit tests for Slack onboarding handoff DM."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vector.domains.cortex.connectors.slack.onboarding_dm import send_slack_handoff_welcome_dm


def test_send_slack_handoff_welcome_dm_uses_postmessage_user_channel_when_ok() -> None:
    """Primary path: chat.postMessage with U… as channel (chat:write)."""
    resp_post = MagicMock()
    resp_post.json.return_value = {"ok": True, "channel": "D0ABC", "ts": "1.2"}
    resp_post.raise_for_status = MagicMock()

    instance = MagicMock()
    instance.post.return_value = resp_post

    with patch("vector.domains.cortex.connectors.slack.onboarding_dm.httpx.Client") as ClientCls:
        ClientCls.return_value.__enter__.return_value = instance
        ClientCls.return_value.__exit__.return_value = None
        send_slack_handoff_welcome_dm("xoxb-secret", "U0TEAMMEM")

    assert instance.post.call_count == 1
    assert instance.post.call_args.kwargs["json"] == {"channel": "U0TEAMMEM", "text": "Hi :wave:"}


def test_send_slack_handoff_welcome_dm_falls_back_to_conversations_open() -> None:
    resp_direct = MagicMock()
    resp_direct.json.return_value = {"ok": False, "error": "channel_not_found"}
    resp_direct.raise_for_status = MagicMock()
    resp_open = MagicMock()
    resp_open.json.return_value = {"ok": True, "channel": {"id": "D0DM123"}}
    resp_open.raise_for_status = MagicMock()
    resp_post2 = MagicMock()
    resp_post2.json.return_value = {"ok": True, "ts": "1.3"}
    resp_post2.raise_for_status = MagicMock()

    instance = MagicMock()
    instance.post.side_effect = [resp_direct, resp_open, resp_post2]

    with patch("vector.domains.cortex.connectors.slack.onboarding_dm.httpx.Client") as ClientCls:
        ClientCls.return_value.__enter__.return_value = instance
        ClientCls.return_value.__exit__.return_value = None
        send_slack_handoff_welcome_dm("xoxb-secret", "U0TEAMMEM")

    assert instance.post.call_count == 3
    assert instance.post.call_args_list[1].kwargs["json"] == {"users": "U0TEAMMEM"}
    assert instance.post.call_args_list[2].kwargs["json"] == {
        "channel": "D0DM123",
        "text": "Hi :wave:",
    }


def test_send_slack_handoff_welcome_dm_raises_when_both_paths_fail() -> None:
    resp_direct = MagicMock()
    resp_direct.json.return_value = {"ok": False, "error": "channel_not_found"}
    resp_direct.raise_for_status = MagicMock()
    resp_open = MagicMock()
    resp_open.json.return_value = {"ok": False, "error": "missing_scope"}
    resp_open.raise_for_status = MagicMock()

    instance = MagicMock()
    instance.post.side_effect = [resp_direct, resp_open]

    with patch("vector.domains.cortex.connectors.slack.onboarding_dm.httpx.Client") as ClientCls:
        ClientCls.return_value.__enter__.return_value = instance
        ClientCls.return_value.__exit__.return_value = None
        with pytest.raises(RuntimeError, match="conversations.open"):
            send_slack_handoff_welcome_dm("xoxb-secret", "U1")
