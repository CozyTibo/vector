"""Fetch Slack workspace member roster for onboarding @-mention UI (users.list)."""

from __future__ import annotations

from typing import Any

import httpx


def list_slack_workspace_members(bot_token: str) -> list[dict[str, Any]]:
    """
    Return a trimmed member list for autocomplete: id, display label, optional avatar URL.

    Excludes Slack bots and deleted users. Raises on repeated API errors.
    """
    out: list[dict[str, Any]] = []
    cursor: str | None = None
    headers = {
        "Authorization": f"Bearer {bot_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    for _ in range(50):
        params: dict[str, str | int] = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        r = httpx.get(
            "https://slack.com/api/users.list",
            headers=headers,
            params=params,
            timeout=30.0,
        )
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            err = data.get("error", "unknown")
            raise RuntimeError(f"slack users.list failed: {err}")
        members = data.get("members")
        if not isinstance(members, list):
            break
        for m in members:
            if not isinstance(m, dict):
                continue
            if m.get("deleted") or m.get("is_bot"):
                continue
            uid = m.get("id")
            if not isinstance(uid, str):
                continue
            prof = m.get("profile")
            if not isinstance(prof, dict):
                prof = {}
            disp = prof.get("display_name_normalized") or prof.get("display_name")
            real = prof.get("real_name")
            legacy = m.get("name")
            label = disp or real or legacy or uid
            if isinstance(label, str):
                label = label.strip() or uid
            else:
                label = uid
            image = prof.get("image_48") or prof.get("image_72")
            slack_name = m.get("name")
            username = (
                slack_name.strip()
                if isinstance(slack_name, str) and slack_name.strip()
                else uid
            )
            email_raw = prof.get("email")
            email_norm: str | None = None
            if isinstance(email_raw, str):
                e = email_raw.strip().lower()
                if e:
                    email_norm = e
            out.append(
                {
                    "id": uid,
                    "label": label,
                    "username": username,
                    "email": email_norm,
                    "image_48": image if isinstance(image, str) else None,
                }
            )
        next_c = data.get("response_metadata")
        cursor = None
        if isinstance(next_c, dict):
            c = next_c.get("next_cursor")
            if isinstance(c, str) and c.strip():
                cursor = c
        if not cursor:
            break
    out.sort(key=lambda x: str(x.get("label", "")).lower())
    return out
