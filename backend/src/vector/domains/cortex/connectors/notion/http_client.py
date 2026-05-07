"""Notion OAuth token exchange + minimal API probe helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from vector.domains.cortex.connectors.notion.errors import NotionOAuthError
from vector.settings import Settings


@dataclass(frozen=True)
class NotionTokenResponse:
    access_token: str
    token_type: str | None
    workspace_id: str | None
    workspace_name: str | None
    workspace_icon: str | None
    owner_user_id: str | None
    bot_id: str | None


def notion_redirect_uri(settings: Settings) -> str:
    uri = settings.notion_redirect_uri.strip()
    if uri:
        return uri.rstrip("/")
    return f"{settings.github_api_public_base_url.rstrip('/')}/connectors/notion/callback"


def exchange_notion_authorization_code(settings: Settings, code: str) -> NotionTokenResponse:
    cid = settings.notion_client_id.strip()
    secret = settings.notion_client_secret.strip()
    if not cid or not secret:
        raise NotionOAuthError("notion OAuth not configured")
    redirect = notion_redirect_uri(settings)
    try:
        r = httpx.post(
            settings.notion_oauth_token_url(),
            headers={"Content-Type": "application/json"},
            auth=(cid, secret),
            json={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect},
            timeout=30.0,
        )
    except httpx.HTTPError as e:
        raise NotionOAuthError(f"notion token http error: {e}") from e
    if r.status_code >= 400:
        raise NotionOAuthError(f"notion token error: {r.status_code} {r.text[:500]}")
    payload: dict[str, Any] = r.json()
    access = payload.get("access_token")
    if not isinstance(access, str):
        raise NotionOAuthError("notion token response missing access_token")
    owner = payload.get("owner")
    owner_user_id: str | None = None
    if isinstance(owner, dict):
        user = owner.get("user")
        if isinstance(user, dict):
            val = user.get("id")
            owner_user_id = val if isinstance(val, str) else None
    bot = payload.get("bot_id")
    return NotionTokenResponse(
        access_token=access,
        token_type=payload.get("token_type") if isinstance(payload.get("token_type"), str) else None,
        workspace_id=payload.get("workspace_id")
        if isinstance(payload.get("workspace_id"), str)
        else None,
        workspace_name=payload.get("workspace_name")
        if isinstance(payload.get("workspace_name"), str)
        else None,
        workspace_icon=payload.get("workspace_icon")
        if isinstance(payload.get("workspace_icon"), str)
        else None,
        owner_user_id=owner_user_id,
        bot_id=bot if isinstance(bot, str) else None,
    )
