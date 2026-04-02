"""Outbound HTTP to GitHub (token exchange + installation API)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from vector.domains.connectors.github.app_jwt import create_github_app_jwt
from vector.domains.connectors.github.errors import GitHubApiError, GitHubUserOAuthError
from vector.settings import Settings

GITHUB_OAUTH_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"


@dataclass(frozen=True)
class GitHubUserTokenExchange:
    access_token: str
    refresh_token: str | None
    expires_in: int | None


def exchange_github_user_code(settings: Settings, code: str) -> GitHubUserTokenExchange:
    """OAuth: authorization code → user access token (GitHub App credentials)."""
    try:
        resp = httpx.post(
            GITHUB_OAUTH_ACCESS_TOKEN_URL,
            headers={
                "Accept": "application/json",
            },
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            timeout=30.0,
        )
    except httpx.RequestError as e:
        raise GitHubUserOAuthError(f"github token request failed: {e}") from e
    if resp.is_error:
        raise GitHubUserOAuthError(f"github token http {resp.status_code}") from None
    try:
        body = resp.json()
    except ValueError:
        raise GitHubUserOAuthError(
            f"github token response not json (http {resp.status_code})",
        ) from None
    err = body.get("error")
    if err:
        desc = body.get("error_description", err)
        raise GitHubUserOAuthError(str(desc))
    token = body.get("access_token")
    if not token or not isinstance(token, str):
        raise GitHubUserOAuthError("missing access_token in github response")
    refresh = body.get("refresh_token")
    expires_in = body.get("expires_in")
    exp_int = int(expires_in) if isinstance(expires_in, int) else None
    refresh_s = refresh if isinstance(refresh, str) else None
    return GitHubUserTokenExchange(
        access_token=token,
        refresh_token=refresh_s,
        expires_in=exp_int,
    )


def fetch_github_installation(
    settings: Settings,
    installation_id: int,
) -> dict[str, Any]:
    """GET /app/installations/{id} with app JWT."""
    app_jwt = create_github_app_jwt(settings)
    base = settings.github_rest_api_app_install_base_url()
    url = f"{base}/app/installations/{installation_id}"
    try:
        resp = httpx.get(
            url,
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
    except httpx.RequestError as e:
        raise GitHubApiError(f"github installation request failed: {e}") from e
    if resp.is_error:
        snippet = (resp.text or "").replace("\n", " ")[:400]
        raise GitHubApiError(
            f"github installation http {resp.status_code}"
            + (f" — {snippet}" if snippet else ""),
        ) from None
    try:
        data = resp.json()
    except ValueError:
        raise GitHubApiError(
            f"github installation response not json (http {resp.status_code})",
        ) from None
    if not isinstance(data, dict):
        raise GitHubApiError("invalid github installation json")
    return data


def create_github_installation_access_token(
    settings: Settings,
    installation_id: int,
) -> str:
    """POST /app/installations/{id}/access_tokens — returns short-lived installation token."""
    app_jwt = create_github_app_jwt(settings)
    base = settings.github_rest_api_base_url()
    url = f"{base}/app/installations/{installation_id}/access_tokens"
    try:
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
    except httpx.RequestError as e:
        raise GitHubApiError(f"github installation token request failed: {e}") from e
    if resp.is_error:
        snippet = (resp.text or "").replace("\n", " ")[:400]
        raise GitHubApiError(
            f"github installation token http {resp.status_code}"
            + (f" — {snippet}" if snippet else ""),
        ) from None
    try:
        data = resp.json()
    except ValueError:
        raise GitHubApiError(
            f"github installation token response not json (http {resp.status_code})",
        ) from None
    token = data.get("token")
    if not isinstance(token, str) or not token:
        raise GitHubApiError("github installation token missing token field")
    return token
