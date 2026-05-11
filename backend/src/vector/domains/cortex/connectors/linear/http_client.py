"""Linear OAuth token exchange + minimal GraphQL."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from vector.domains.cortex.connectors.linear.errors import LinearOAuthError
from vector.settings import Settings


@dataclass(frozen=True)
class LinearTokenResponse:
    access_token: str
    refresh_token: str | None
    expires_in: int | None


def linear_redirect_uri(settings: Settings) -> str:
    uri = settings.linear_redirect_uri.strip()
    if uri:
        return uri.rstrip("/")
    return f"{settings.github_api_public_base_url.rstrip('/')}/connectors/linear/callback"


def exchange_linear_authorization_code(settings: Settings, code: str) -> LinearTokenResponse:
    cid = settings.linear_client_id.strip()
    secret = settings.linear_client_secret.strip()
    if not cid or not secret:
        raise LinearOAuthError("linear OAuth not configured")
    redirect = linear_redirect_uri(settings)
    body = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect,
        "client_id": cid,
        "client_secret": secret,
    }
    try:
        r = httpx.post(
            settings.linear_oauth_token_url(),
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=30.0,
        )
    except httpx.HTTPError as e:
        raise LinearOAuthError(f"linear token http error: {e}") from e
    if r.status_code >= 400:
        raise LinearOAuthError(f"linear token error: {r.status_code} {r.text[:500]}")
    payload: dict[str, Any] = r.json()
    access = payload.get("access_token")
    if not isinstance(access, str):
        raise LinearOAuthError("linear token response missing access_token")
    refresh = payload.get("refresh_token")
    expires_in = payload.get("expires_in")
    return LinearTokenResponse(
        access_token=access,
        refresh_token=refresh if isinstance(refresh, str) else None,
        expires_in=expires_in if isinstance(expires_in, int) else None,
    )


def fetch_linear_viewer_org(settings: Settings, access_token: str) -> tuple[str | None, str | None]:
    query = """
    query ViewerOrg {
      viewer {
        organization {
          id
          name
        }
      }
    }
    """
    try:
        r = httpx.post(
            settings.linear_graphql_oauth_profile_url(),
            json={"query": query},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
    except httpx.HTTPError as e:
        raise LinearOAuthError(f"linear graphql http error: {e}") from e
    if r.status_code >= 400:
        raise LinearOAuthError(f"linear graphql error: {r.status_code} {r.text[:500]}")
    data: dict[str, Any] = r.json()
    if "errors" in data:
        errs = data.get("errors")
        raise LinearOAuthError(f"linear graphql errors: {errs}")
    viewer = data.get("data", {}).get("viewer") if isinstance(data.get("data"), dict) else None
    if not isinstance(viewer, dict):
        return None, None
    org = viewer.get("organization")
    if not isinstance(org, dict):
        return None, None
    oid = org.get("id")
    name = org.get("name")
    return (str(oid) if oid is not None else None, str(name) if name is not None else None)


def token_expires_at(expires_in: int | None) -> datetime | None:
    if expires_in is None:
        return None
    return datetime.now(tz=UTC) + timedelta(seconds=expires_in)
