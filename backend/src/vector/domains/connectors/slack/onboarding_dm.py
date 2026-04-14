"""One-off Slack DM during onboarding (e.g. handoff welcome before product access)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger("app")

SLACK_HANDOFF_WELCOME_DM_SENT_FOR_USER_KEY = "slack_handoff_welcome_dm_sent_for"

DEFAULT_HANDOFF_WELCOME_TEXT = "Hi :wave:"


def send_slack_handoff_welcome_dm(
    bot_token: str,
    slack_user_id: str,
    *,
    text: str = DEFAULT_HANDOFF_WELCOME_TEXT,
) -> None:
    """
    Send a short DM from the bot to a workspace member.

    Prefer ``chat.postMessage`` with the member's **user ID** (``U…``) as ``channel`` — Slack opens
    the bot↔user DM when needed and this typically works with **chat:write** only.

    Falls back to ``conversations.open`` (usually needs **im:write**) then post to the ``D…``
    channel if the first call fails.
    """
    uid = slack_user_id.strip()
    if not uid:
        raise ValueError("slack_user_id is empty")

    headers = {
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    with httpx.Client(timeout=30.0) as client:
        post_direct = client.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json={"channel": uid, "text": text},
        )
        post_direct.raise_for_status()
        direct_data: dict[str, Any] = post_direct.json()
        if direct_data.get("ok"):
            log.info(
                "Slack handoff welcome DM sent (chat.postMessage with user id as channel) slack_user=%s",
                uid,
            )
            return

        err_direct = str(direct_data.get("error", "unknown"))
        log.info(
            "Slack handoff welcome: postMessage(user channel) not ok (%s); trying conversations.open",
            err_direct,
        )

        open_r = client.post(
            "https://slack.com/api/conversations.open",
            headers=headers,
            json={"users": uid},
        )
        open_r.raise_for_status()
        open_data: dict[str, Any] = open_r.json()
        if not open_data.get("ok"):
            err = open_data.get("error", "unknown")
            raise RuntimeError(
                f"slack handoff DM failed: chat.postMessage error={err_direct!r}, "
                f"conversations.open error={err!r}"
            )
        ch = open_data.get("channel")
        if not isinstance(ch, dict):
            raise RuntimeError("slack conversations.open missing channel")
        channel_id = ch.get("id")
        if not isinstance(channel_id, str) or not channel_id.strip():
            raise RuntimeError("slack conversations.open missing channel id")

        post_r = client.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json={"channel": channel_id, "text": text},
        )
        post_r.raise_for_status()
        post_data: dict[str, Any] = post_r.json()
        if not post_data.get("ok"):
            err = post_data.get("error", "unknown")
            raise RuntimeError(
                f"slack handoff DM: conversations.open ok but chat.postMessage failed: {err!r}"
            )
        log.info(
            "Slack handoff welcome DM sent (conversations.open + postMessage) slack_user=%s channel=%s",
            uid,
            channel_id,
        )
