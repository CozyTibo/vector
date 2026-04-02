"""Slack OAuth v2 token exchange."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from vector.domains.connectors.slack.errors import SlackOAuthError
from vector.settings import Settings


@dataclass(frozen=True)
class SlackOAuthV2Access:
    access_token: str
    team_id: str
    team_name: str | None
    scope: str | None


def slack_redirect_uri(settings: Settings) -> str:
    uri = settings.slack_callback_url.strip()
    if uri:
        return uri.rstrip("/")
    return f"{settings.github_api_public_base_url.rstrip('/')}/slack/callback"


def exchange_slack_authorization_code(settings: Settings, code: str) -> SlackOAuthV2Access:
    cid = settings.slack_client_id.strip()
    secret = settings.slack_client_secret.strip()
    if not cid or not secret:
        raise SlackOAuthError("slack OAuth not configured")
    redirect = slack_redirect_uri(settings)
    body = {
        "code": code,
        "client_id": cid,
        "client_secret": secret,
        "redirect_uri": redirect,
    }
    try:
        r = httpx.post(
            "https://slack.com/api/oauth.v2.access",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30.0,
        )
    except httpx.HTTPError as e:
        raise SlackOAuthError(f"slack token http error: {e}") from e
    if r.status_code >= 400:
        raise SlackOAuthError(f"slack token error: {r.status_code} {r.text[:500]}")
    payload: dict[str, Any] = r.json()
    if not payload.get("ok"):
        err = payload.get("error")
        raise SlackOAuthError(f"slack oauth.v2.access failed: {err!r}")
    access = payload.get("access_token")
    if not isinstance(access, str):
        raise SlackOAuthError("slack token response missing access_token")
    team = payload.get("team")
    team_id: str | None = None
    team_name: str | None = None
    if isinstance(team, dict):
        tid = team.get("id")
        if isinstance(tid, str):
            team_id = tid
        tname = team.get("name")
        if isinstance(tname, str):
            team_name = tname
    if not team_id:
        raise SlackOAuthError("slack token response missing team.id")
    scope_raw = payload.get("scope")
    scope = scope_raw if isinstance(scope_raw, str) else None
    return SlackOAuthV2Access(
        access_token=access,
        team_id=team_id,
        team_name=team_name,
        scope=scope,
    )
