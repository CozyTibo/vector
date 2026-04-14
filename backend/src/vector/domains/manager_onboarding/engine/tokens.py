"""Deterministic Slack mrkdwn extraction from user text (overrides LLM patch in the same turn)."""

from __future__ import annotations

import re
from typing import Any

from vector.domains.manager_onboarding.engine.requirements import (
    REQ_CHANNELS,
    REQ_PEER_HANDLES,
    REQ_REPORTS_WHO,
    REQ_TEAM_MEMBERS,
)

_USER_MENTION = re.compile(r"<@([UuWw][A-Za-z0-9]{8,})>")
_CHANNEL_MENTION = re.compile(r"<#([CG][A-Z0-9]{8,})(?:\|[^>]+)?>")
_SUBTEAM_MENTION = re.compile(r"(<!subteam\^[S][A-Z0-9]+(?:\|[^>]+)?>)")


def collect_user_ids_from_blocks(blocks: Any) -> list[str]:
    """
    Walk Block Kit payload and collect ``user_id`` from rich-text user elements.

    Modern Slack clients often send @mentions only here; ``event.text`` may lack ``<@U…>``.
    """
    out: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "user" and isinstance(node.get("user_id"), str):
                uid = node["user_id"].strip().upper()
                if uid.startswith(("U", "W")) and len(uid) >= 9:
                    out.append(uid)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    if isinstance(blocks, list):
        walk(blocks)
    return list(dict.fromkeys(out))


def augment_slack_message_text_with_block_users(text: str, blocks: Any) -> str:
    """Append synthetic ``<@USER_ID>`` tokens so downstream mrkdwn extraction sees mentions."""
    ids = collect_user_ids_from_blocks(blocks)
    if not ids:
        return text if isinstance(text, str) else ""
    synthetic = "".join(f"<@{u}>" for u in ids)
    t = (text or "").strip() if isinstance(text, str) else ""
    if t:
        return f"{t} {synthetic}".strip()
    return synthetic


def extract_slack_mrkdwn_entities(text: str) -> dict[str, list[str]]:
    """
    Parse Slack-rendered tokens from raw message text.

    Returns deduped lists preserving first-seen order.
    """
    s = text or ""
    user_ids = list(dict.fromkeys(_USER_MENTION.findall(s)))
    channel_ids = list(dict.fromkeys(_CHANNEL_MENTION.findall(s)))
    subteams = list(dict.fromkeys(m.group(1) for m in _SUBTEAM_MENTION.finditer(s)))
    return {
        "user_ids": [u.upper() for u in user_ids],
        "channel_ids": [c.upper() for c in channel_ids],
        "subteam_tokens": subteams,
    }


def _union_list_field(out: dict[str, Any], key: str, additions: list[str]) -> None:
    cur = out.get(key)
    if cur is None:
        cur = []
    elif not isinstance(cur, list):
        cur = []
    seen = {str(x).strip() for x in cur if x is not None}
    merged = list(cur)
    for a in additions:
        t = (a or "").strip()
        if t and t not in seen:
            seen.add(t)
            merged.append(t)
    out[key] = merged


def merge_deterministic_entities_into_patch(
    raw_patch: dict[str, Any] | None,
    user_text: str,
    *,
    primary_req_id: str | None,
) -> dict[str, Any]:
    """
    Union Slack mrkdwn ids into the LLM ``patch`` before validation.

    Extracted entities always appear in the merged patch lists so validation / Slack APIs
    resolve them even when the model omits or mis-copies them.
    """
    out: dict[str, Any] = dict(raw_patch or {})
    ext = extract_slack_mrkdwn_entities(user_text)
    user_bits = [*ext["user_ids"], *ext["subteam_tokens"]]
    chans = ext["channel_ids"]

    if not user_bits and not chans:
        return out

    primary_to_user_key: dict[str, str] = {
        REQ_PEER_HANDLES: "peer_slack_user_ids",
        REQ_TEAM_MEMBERS: "team_member_slack_ids",
        REQ_REPORTS_WHO: "reports_to_slack_ids",
    }

    user_keys: set[str] = set()
    for k in ("peer_slack_user_ids", "team_member_slack_ids", "reports_to_slack_ids"):
        if k in out:
            user_keys.add(k)
    pk = primary_to_user_key.get(primary_req_id or "")
    if pk and user_bits:
        user_keys.add(pk)
    for k in user_keys:
        _union_list_field(out, k, user_bits)

    if chans:
        chan_keys: set[str] = set()
        if "observed_channel_ids" in out:
            chan_keys.add("observed_channel_ids")
        if primary_req_id == REQ_CHANNELS:
            chan_keys.add("observed_channel_ids")
        for k in chan_keys:
            _union_list_field(out, k, chans)

    return out
