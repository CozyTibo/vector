"""Slack Web API calls for Phase 01 organizational exhaust (users, channels, messages)."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any

import httpx

from vector.domains.cortex.connectors.slack.errors import SlackWebApiError

_logger = logging.getLogger("app")

SLACK_API = "https://slack.com/api"


def slack_web_api_post(
    token: str,
    method: str,
    *,
    json_body: dict[str, Any],
    api_base: str | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """POST https://slack.com/api/{method} with Bearer token; honors Retry-After on 429."""
    base = (api_base or SLACK_API).rstrip("/")
    url = f"{base}/{method}"
    for attempt in range(8):
        try:
            r = httpx.post(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json=json_body,
                timeout=timeout,
            )
        except httpx.RequestError as e:
            raise SlackWebApiError(f"slack {method} transport error: {e}") from e
        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After")
            try:
                wait_s = float(retry_after) if retry_after else 2.0
            except ValueError:
                wait_s = 2.0
            wait_s = min(max(wait_s, 0.5), 60.0)
            _logger.warning(
                "slack rate limited",
                extra={"method": method, "wait_s": wait_s, "attempt": attempt},
            )
            time.sleep(wait_s)
            continue
        try:
            data = r.json()
        except ValueError as e:
            raise SlackWebApiError(f"slack {method} invalid json (http {r.status_code})") from e
        if not isinstance(data, dict):
            raise SlackWebApiError(f"slack {method} response not object")
        return data
    raise SlackWebApiError(f"slack {method} exhausted retries after rate limits")


def iter_users_list_pages(
    token: str,
    *,
    api_base: str | None = None,
    limit: int = 200,
    max_pages: int,
) -> Iterator[list[dict[str, Any]]]:
    cursor: str | None = None
    for _ in range(max_pages):
        body: dict[str, Any] = {"limit": min(limit, 200)}
        if cursor:
            body["cursor"] = cursor
        data = slack_web_api_post(token, "users.list", json_body=body, api_base=api_base)
        if not data.get("ok"):
            raise SlackWebApiError(str(data.get("error", "users.list_failed")))
        raw = data.get("members")
        members = [x for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []
        yield members
        meta = data.get("response_metadata")
        next_c = None
        if isinstance(meta, dict):
            nc = meta.get("next_cursor")
            if isinstance(nc, str) and nc.strip():
                next_c = nc.strip()
        if not next_c:
            break
        cursor = next_c


def iter_conversations_list_pages(
    token: str,
    *,
    api_base: str | None = None,
    types: str = "public_channel,private_channel",
    limit: int = 200,
    max_pages: int,
) -> Iterator[list[dict[str, Any]]]:
    cursor: str | None = None
    for _ in range(max_pages):
        body: dict[str, Any] = {
            "types": types,
            "exclude_archived": True,
            "limit": min(limit, 200),
        }
        if cursor:
            body["cursor"] = cursor
        data = slack_web_api_post(token, "conversations.list", json_body=body, api_base=api_base)
        if not data.get("ok"):
            raise SlackWebApiError(str(data.get("error", "conversations.list_failed")))
        raw = data.get("channels")
        chans = [x for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []
        yield chans
        meta = data.get("response_metadata")
        next_c = None
        if isinstance(meta, dict):
            nc = meta.get("next_cursor")
            if isinstance(nc, str) and nc.strip():
                next_c = nc.strip()
        if not next_c:
            break
        cursor = next_c


def conversations_history(
    token: str,
    *,
    api_base: str | None = None,
    channel: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Single conversations.history page (latest messages)."""
    data = slack_web_api_post(
        token,
        "conversations.history",
        json_body={"channel": channel, "limit": min(limit, 1000)},
        api_base=api_base,
    )
    if not data.get("ok"):
        raise SlackWebApiError(str(data.get("error", "conversations.history_failed")))
    raw = data.get("messages")
    return [x for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []


def _next_cursor(data: dict[str, Any]) -> str | None:
    meta = data.get("response_metadata")
    if not isinstance(meta, dict):
        return None
    nc = meta.get("next_cursor")
    if not isinstance(nc, str) or not nc.strip():
        return None
    return nc.strip()


def conversations_history_page(
    token: str,
    *,
    api_base: str | None = None,
    channel: str,
    limit: int,
    cursor: str | None = None,
    oldest: str | None = None,
    latest: str | None = None,
    inclusive: bool = False,
) -> dict[str, Any]:
    body: dict[str, Any] = {"channel": channel, "limit": min(limit, 1000)}
    if cursor:
        body["cursor"] = cursor
    if oldest:
        body["oldest"] = oldest
    if latest:
        body["latest"] = latest
    if inclusive:
        body["inclusive"] = True
    data = slack_web_api_post(token, "conversations.history", json_body=body, api_base=api_base)
    if not data.get("ok"):
        raise SlackWebApiError(str(data.get("error", "conversations.history_failed")))
    raw = data.get("messages")
    messages = [x for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []
    return {
        "messages": messages,
        "next_cursor": _next_cursor(data),
        "has_more": bool(data.get("has_more")),
    }


def iter_conversations_history_pages(
    token: str,
    *,
    api_base: str | None = None,
    channel: str,
    limit: int,
    max_pages: int,
    cursor: str | None = None,
    oldest: str | None = None,
    latest: str | None = None,
    inclusive: bool = False,
) -> Iterator[dict[str, Any]]:
    cur = cursor
    for _ in range(max_pages):
        page = conversations_history_page(
            token,
            api_base=api_base,
            channel=channel,
            limit=limit,
            cursor=cur,
            oldest=oldest,
            latest=latest,
            inclusive=inclusive,
        )
        yield page
        nxt = page.get("next_cursor")
        if not isinstance(nxt, str) or not nxt:
            break
        cur = nxt


def conversations_replies_page(
    token: str,
    *,
    api_base: str | None = None,
    channel: str,
    thread_ts: str,
    limit: int,
    cursor: str | None = None,
    oldest: str | None = None,
    latest: str | None = None,
    inclusive: bool = False,
) -> dict[str, Any]:
    body: dict[str, Any] = {"channel": channel, "ts": thread_ts, "limit": min(limit, 1000)}
    if cursor:
        body["cursor"] = cursor
    if oldest:
        body["oldest"] = oldest
    if latest:
        body["latest"] = latest
    if inclusive:
        body["inclusive"] = True
    data = slack_web_api_post(token, "conversations.replies", json_body=body, api_base=api_base)
    if not data.get("ok"):
        raise SlackWebApiError(str(data.get("error", "conversations.replies_failed")))
    raw = data.get("messages")
    messages = [x for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []
    return {
        "messages": messages,
        "next_cursor": _next_cursor(data),
        "has_more": bool(data.get("has_more")),
    }


def iter_conversations_replies_pages(
    token: str,
    *,
    api_base: str | None = None,
    channel: str,
    thread_ts: str,
    limit: int,
    max_pages: int,
    cursor: str | None = None,
    oldest: str | None = None,
    latest: str | None = None,
    inclusive: bool = False,
) -> Iterator[dict[str, Any]]:
    cur = cursor
    for _ in range(max_pages):
        page = conversations_replies_page(
            token,
            api_base=api_base,
            channel=channel,
            thread_ts=thread_ts,
            limit=limit,
            cursor=cur,
            oldest=oldest,
            latest=latest,
            inclusive=inclusive,
        )
        yield page
        nxt = page.get("next_cursor")
        if not isinstance(nxt, str) or not nxt:
            break
        cur = nxt
