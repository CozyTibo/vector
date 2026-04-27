"""Calls (Google) OAuth token exchange + profile lookup."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from vector.domains.connectors.calls.errors import CallsOAuthError
from vector.settings import Settings


@dataclass(frozen=True)
class CallsTokenResponse:
    access_token: str
    refresh_token: str | None
    expires_in: int | None


def calls_redirect_uri(settings: Settings) -> str:
    uri = settings.calls_redirect_uri.strip()
    if uri:
        return uri.rstrip("/")
    return f"{settings.github_api_public_base_url.rstrip('/')}/connectors/calls/callback"


def exchange_calls_authorization_code(settings: Settings, code: str) -> CallsTokenResponse:
    cid = settings.google_client_id.strip()
    secret = settings.google_client_secret.strip()
    if not cid or not secret:
        raise CallsOAuthError("calls OAuth not configured (GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET)")
    body = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": calls_redirect_uri(settings),
        "client_id": cid,
        "client_secret": secret,
    }
    try:
        r = httpx.post(settings.calls_google_oauth_token_url(), data=body, timeout=30.0)
    except httpx.HTTPError as e:
        raise CallsOAuthError(f"calls token http error: {e}") from e
    if r.status_code >= 400:
        raise CallsOAuthError(f"calls token error: {r.status_code} {r.text[:500]}")
    payload: dict[str, Any] = r.json()
    access = payload.get("access_token")
    if not isinstance(access, str):
        raise CallsOAuthError("calls token response missing access_token")
    refresh = payload.get("refresh_token")
    expires_in = payload.get("expires_in")
    return CallsTokenResponse(
        access_token=access,
        refresh_token=refresh if isinstance(refresh, str) else None,
        expires_in=expires_in if isinstance(expires_in, int) else None,
    )


def calls_token_expires_at(expires_in: int | None) -> datetime | None:
    if not isinstance(expires_in, int) or expires_in <= 0:
        return None
    return datetime.now(UTC) + timedelta(seconds=expires_in)


def fetch_calls_google_profile(access_token: str) -> tuple[str | None, str | None]:
    try:
        r = httpx.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )
    except httpx.HTTPError as e:
        raise CallsOAuthError(f"calls profile http error: {e}") from e
    if r.status_code >= 400:
        raise CallsOAuthError(f"calls profile error: {r.status_code} {r.text[:500]}")
    payload: dict[str, Any] = r.json()
    sid = payload.get("sub")
    email = payload.get("email")
    return (sid if isinstance(sid, str) else None, email if isinstance(email, str) else None)
