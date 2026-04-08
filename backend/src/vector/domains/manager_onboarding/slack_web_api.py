"""Minimal Slack Web API client (httpx)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger(__name__)

SLACK_API = "https://slack.com/api"


def _post(token: str, method: str, json_body: dict[str, Any]) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    with httpx.Client(timeout=30.0) as client:
        r = client.post(f"{SLACK_API}/{method}", headers=headers, json=json_body)
        r.raise_for_status()
        data = r.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"slack {method}: invalid json")
    return data


def chat_post_message(
    token: str,
    *,
    channel: str,
    text: str,
    blocks: list[dict[str, Any]] | None = None,
    thread_ts: str | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {"channel": channel, "text": text}
    if blocks is not None:
        body["blocks"] = blocks
    if thread_ts:
        body["thread_ts"] = thread_ts
    data = _post(token, "chat.postMessage", body)
    if not data.get("ok"):
        err = data.get("error", "unknown")
        raise RuntimeError(f"chat.postMessage failed: {err}")
    return data


def reactions_add(
    token: str,
    *,
    channel: str,
    timestamp: str,
    name: str,
) -> dict[str, Any]:
    data = _post(
        token,
        "reactions.add",
        {"channel": channel, "timestamp": timestamp, "name": name},
    )
    if not data.get("ok"):
        err = data.get("error", "unknown")
        if err == "already_reacted":
            return data
        raise RuntimeError(f"reactions.add failed: {err}")
    return data


def conversations_info(token: str, *, channel: str) -> dict[str, Any]:
    data = _post(token, "conversations.info", {"channel": channel})
    if not data.get("ok"):
        err = data.get("error", "unknown")
        raise RuntimeError(f"conversations.info failed: {err}")
    return data


def conversations_join(token: str, *, channel: str) -> dict[str, Any]:
    data = _post(token, "conversations.join", {"channel": channel})
    if not data.get("ok"):
        err = data.get("error", "unknown")
        return {"ok": False, "error": err}
    return data


def users_info(token: str, *, user: str) -> dict[str, Any]:
    data = _post(token, "users.info", {"user": user})
    if not data.get("ok"):
        err = data.get("error", "unknown")
        raise RuntimeError(f"users.info failed: {err}")
    return data
