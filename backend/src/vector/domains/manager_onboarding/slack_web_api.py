"""Minimal Slack Web API client (httpx)."""

from __future__ import annotations

import logging
from collections.abc import Iterator
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
    """
    Slack accepts JSON or form bodies; form-encoded avoids rare ``invalid_arguments``
    responses some workspaces return for JSON POSTs on this method.
    """
    ch = (channel or "").strip().upper()
    if not ch:
        raise ValueError("channel is required")
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(timeout=30.0) as client:
        r = client.post(f"{SLACK_API}/conversations.info", headers=headers, data={"channel": ch})
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        raise RuntimeError("slack conversations.info: invalid json")
    if not data.get("ok"):
        err = data.get("error", "unknown")
        raise RuntimeError(f"conversations.info failed: {err}")
    return data


def conversations_join(token: str, *, channel: str) -> dict[str, Any]:
    ch = (channel or "").strip().upper()
    if not ch:
        return {"ok": False, "error": "channel_required"}
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(timeout=30.0) as client:
        r = client.post(f"{SLACK_API}/conversations.join", headers=headers, data={"channel": ch})
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict):
        return {"ok": False, "error": "invalid_json"}
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


def iter_users_list(token: str) -> Iterator[dict[str, Any]]:
    """Yield workspace member dicts from paginated ``users.list`` (needs ``users:read``)."""
    cursor: str | None = None
    while True:
        body: dict[str, Any] = {"limit": 200}
        if cursor:
            body["cursor"] = cursor
        data = _post(token, "users.list", body)
        if not data.get("ok"):
            err = data.get("error", "unknown")
            raise RuntimeError(f"users.list failed: {err}")
        members = data.get("members")
        if isinstance(members, list):
            for m in members:
                if isinstance(m, dict):
                    yield m
        meta = data.get("response_metadata")
        cursor = None
        if isinstance(meta, dict):
            nc = meta.get("next_cursor")
            if isinstance(nc, str) and nc.strip():
                cursor = nc.strip()
        if not cursor:
            break


def conversations_list_public_private(token: str) -> list[dict[str, Any]]:
    """
    Paginated ``conversations.list`` for public + private channels the token can see.
    Each item is a channel dict with at least ``id`` and ``name``.
    """
    out: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        body: dict[str, Any] = {"types": "public_channel,private_channel", "limit": 200}
        if cursor:
            body["cursor"] = cursor
        data = _post(token, "conversations.list", body)
        if not data.get("ok"):
            err = data.get("error", "unknown")
            raise RuntimeError(f"conversations.list failed: {err}")
        chans = data.get("channels")
        if isinstance(chans, list):
            for ch in chans:
                if isinstance(ch, dict) and ch.get("id") and ch.get("name"):
                    out.append(ch)
        meta = data.get("response_metadata")
        cursor = None
        if isinstance(meta, dict):
            nc = meta.get("next_cursor")
            if isinstance(nc, str) and nc.strip():
                cursor = nc.strip()
        if not cursor:
            break
    return out
