"""Fetch public Slack channels for onboarding (conversations.list)."""

from __future__ import annotations

from typing import Any

import httpx


def list_slack_workspace_public_channels(bot_token: str) -> list[dict[str, Any]]:
    """
    Return public channels the bot can see: ``id`` (C…), ``name`` (without leading #).

    Paginates ``conversations.list``; excludes archived. Requires ``channels:read`` (or broader) on the bot.
    """
    out: list[dict[str, Any]] = []
    cursor: str | None = None
    headers = {
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    for _ in range(50):
        params: dict[str, str | int] = {
            "types": "public_channel",
            "limit": 200,
            "exclude_archived": "true",
        }
        if cursor:
            params["cursor"] = cursor
        r = httpx.get(
            "https://slack.com/api/conversations.list",
            headers=headers,
            params=params,
            timeout=30.0,
        )
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            err = data.get("error", "unknown")
            raise RuntimeError(f"slack conversations.list failed: {err}")
        channels = data.get("channels")
        if not isinstance(channels, list):
            break
        for ch in channels:
            if not isinstance(ch, dict):
                continue
            cid = ch.get("id")
            name = ch.get("name")
            if not isinstance(cid, str) or not cid.strip():
                continue
            if not isinstance(name, str) or not name.strip():
                continue
            if ch.get("is_archived"):
                continue
            out.append({"id": cid.strip(), "name": name.strip().lstrip("#")})
        next_c = data.get("response_metadata")
        cursor = None
        if isinstance(next_c, dict):
            c = next_c.get("next_cursor")
            if isinstance(c, str) and c.strip():
                cursor = c
        if not cursor:
            break
    out.sort(key=lambda x: str(x.get("name", "")).lower())
    return out
