"""Slack Web API-like mock routes for Cortex ingestion."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse


def _cursor_encode(idx: int) -> str:
    return f"cursor:{max(idx, 0)}"


def _cursor_decode(raw: Any) -> int:
    if not isinstance(raw, str) or not raw.startswith("cursor:"):
        return 0
    try:
        return max(0, int(raw.split(":", 1)[1]))
    except ValueError:
        return 0


def _enrich_slack_thread_parents(messages: list[dict[str, Any]]) -> None:
    """Derive parent thread metadata as Slack returns on `conversations.history` parents."""
    by_channel: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in messages:
        cid = m.get("channel")
        if isinstance(cid, str):
            by_channel[cid].append(m)
    for msgs in by_channel.values():
        for root in msgs:
            if isinstance(root.get("parent_ts"), str):
                continue
            rts = root.get("ts")
            if not isinstance(rts, str):
                continue
            reply_ts_list: list[str] = []
            for m in msgs:
                if m is root:
                    continue
                if str(m.get("ts")) == str(rts):
                    continue
                if m.get("parent_ts") == rts or m.get("thread_ts") == rts:
                    mt = m.get("ts")
                    if isinstance(mt, str):
                        reply_ts_list.append(mt)
            n = len(reply_ts_list)
            if n > 0:
                root["reply_count"] = n
                root["reply_users_count"] = n
                root["thread_ts"] = rts
                root["latest_reply"] = max(reply_ts_list)


def _slack_member_payload(*, user_id: str, email: str, team_id: str) -> dict[str, Any]:
    """Subset of Slack `users.list` member object fields ingestion stores as raw payload."""
    local = email.split("@")[0]
    display = local.replace(".", " ").replace("_", " ").title()
    short_name = local.split(".")[0].title() if "." in local else display
    return {
        "id": user_id,
        "team_id": team_id,
        "name": local.replace(".", "_"),
        "deleted": False,
        "color": "9f69e7",
        "real_name": display,
        "tz": "America/Los_Angeles",
        "tz_label": "Pacific Standard Time",
        "tz_offset": -28800,
        "is_bot": False,
        "is_app_user": False,
        "updated": 1735689600,
        "profile": {
            "real_name": display,
            "display_name": short_name,
            "email": email,
            "team": team_id,
        },
    }


def _normalize_events(slack_events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str], list[dict[str, Any]]]:
    users_by_id: dict[str, str] = {}
    channels_by_id: dict[str, dict[str, Any]] = {}
    messages: list[dict[str, Any]] = []
    team_id = "T00000000"
    for event in slack_events:
        wid = event.get("workspace_id")
        if isinstance(wid, str) and wid.startswith("T"):
            team_id = wid
        uid = event.get("user_id")
        email = event.get("user_email")
        if isinstance(uid, str) and uid and isinstance(email, str) and email:
            users_by_id.setdefault(uid, email)
        cid = event.get("channel_id")
        if isinstance(cid, str) and cid:
            ch_raw = event.get("channel")
            ch_label = ch_raw if isinstance(ch_raw, str) else f"channel-{cid[-4:]}"
            ch_name = ch_label.lstrip("#").replace(" ", "-")
            is_gen = ch_label.lower().endswith("general") or ch_name == "general"
            channels_by_id.setdefault(
                cid,
                {
                    "id": cid,
                    "name": ch_name,
                    "is_archived": False,
                    "is_member": True,
                    "is_channel": True,
                    "is_private": False,
                    "is_mpim": False,
                    "is_general": is_gen,
                },
            )
        ts = event.get("ts")
        if isinstance(ts, str) and ts:
            msg = {
                "type": "message",
                "channel": cid,
                "ts": ts,
                "text": event.get("text"),
                "user": uid,
                "thread_ts": event.get("thread_ts"),
                "parent_ts": event.get("parent_ts"),
                "reactions": event.get("reactions") if isinstance(event.get("reactions"), list) else [],
            }
            messages.append(msg)
    _enrich_slack_thread_parents(messages)
    messages.sort(key=lambda m: str(m.get("ts") or ""), reverse=True)
    members = [
        _slack_member_payload(user_id=uid, email=email, team_id=team_id)
        for uid, email in sorted(users_by_id.items())
    ]
    channels = list(sorted(channels_by_id.values(), key=lambda c: str(c.get("id"))))
    return members, {c["id"]: c["name"] for c in channels}, messages


def _page(items: list[dict[str, Any]], *, limit: int, cursor: int) -> tuple[list[dict[str, Any]], str]:
    size = min(max(limit, 1), 1000)
    chunk = items[cursor : cursor + size]
    next_cursor = _cursor_encode(cursor + len(chunk)) if cursor + len(chunk) < len(items) else ""
    return chunk, next_cursor


def build_slack_router(get_slack_events: Callable[[], list[dict[str, Any]]]) -> APIRouter:
    r = APIRouter(prefix="/slack/api")

    @r.post("/users.list")
    def users_list(body: dict[str, Any]) -> JSONResponse:
        members, _channels, _messages = _normalize_events(get_slack_events())
        cursor = _cursor_decode(body.get("cursor"))
        limit = int(body.get("limit", 200)) if isinstance(body.get("limit"), int) else 200
        chunk, next_cursor = _page(members, limit=limit, cursor=cursor)
        return JSONResponse({"ok": True, "members": chunk, "response_metadata": {"next_cursor": next_cursor}})

    @r.post("/conversations.list")
    def conversations_list(body: dict[str, Any]) -> JSONResponse:
        _members, channels_map, _messages = _normalize_events(get_slack_events())
        channels = [{"id": cid, "name": name, "is_archived": False, "is_member": True} for cid, name in channels_map.items()]
        channels.sort(key=lambda c: str(c.get("id")))
        cursor = _cursor_decode(body.get("cursor"))
        limit = int(body.get("limit", 200)) if isinstance(body.get("limit"), int) else 200
        chunk, next_cursor = _page(channels, limit=limit, cursor=cursor)
        return JSONResponse({"ok": True, "channels": chunk, "response_metadata": {"next_cursor": next_cursor}})

    @r.post("/conversations.history")
    def conversations_history(body: dict[str, Any]) -> JSONResponse:
        _members, _channels, messages = _normalize_events(get_slack_events())
        cid = body.get("channel")
        channel_messages = [
            m for m in messages if m.get("channel") == cid and not isinstance(m.get("parent_ts"), str)
        ]
        oldest = body.get("oldest")
        latest = body.get("latest")
        if isinstance(oldest, str) and oldest:
            channel_messages = [m for m in channel_messages if str(m.get("ts")) >= oldest]
        if isinstance(latest, str) and latest:
            channel_messages = [m for m in channel_messages if str(m.get("ts")) <= latest]
        cursor = _cursor_decode(body.get("cursor"))
        limit = int(body.get("limit", 200)) if isinstance(body.get("limit"), int) else 200
        chunk, next_cursor = _page(channel_messages, limit=limit, cursor=cursor)
        return JSONResponse(
            {
                "ok": True,
                "messages": chunk,
                "has_more": bool(next_cursor),
                "response_metadata": {"next_cursor": next_cursor},
            }
        )

    @r.post("/conversations.replies")
    def conversations_replies(body: dict[str, Any]) -> JSONResponse:
        _members, _channels, messages = _normalize_events(get_slack_events())
        cid = body.get("channel")
        thread_ts = body.get("ts")
        thread_messages = [
            m
            for m in messages
            if m.get("channel") == cid
            and (m.get("ts") == thread_ts or m.get("thread_ts") == thread_ts or m.get("parent_ts") == thread_ts)
        ]
        thread_messages.sort(key=lambda m: str(m.get("ts") or ""))
        cursor = _cursor_decode(body.get("cursor"))
        limit = int(body.get("limit", 200)) if isinstance(body.get("limit"), int) else 200
        chunk, next_cursor = _page(thread_messages, limit=limit, cursor=cursor)
        return JSONResponse(
            {
                "ok": True,
                "messages": chunk,
                "has_more": bool(next_cursor),
                "response_metadata": {"next_cursor": next_cursor},
            }
        )

    return r
