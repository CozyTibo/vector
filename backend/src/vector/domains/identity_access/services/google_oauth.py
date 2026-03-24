"""Google OAuth2 authorize URL + token exchange."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from vector.domains.identity_access.errors import GoogleOAuthError
from vector.settings import Settings


@dataclass(frozen=True)
class GoogleProfile:
    subject: str
    email: str
    full_name: str | None


def google_authorize_url(
    settings: Settings,
    *,
    state: str,
    code_challenge: str,
) -> str:
    if not settings.google_client_id or not settings.google_redirect_uri:
        msg = "google oauth not configured"
        raise GoogleOAuthError(msg)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def exchange_code_for_profile(
    settings: Settings,
    *,
    code: str,
    code_verifier: str,
) -> GoogleProfile:
    if not settings.google_client_secret:
        msg = "google oauth not configured"
        raise GoogleOAuthError(msg)
    body = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": code_verifier,
    }
    try:
        response = httpx.post(
            "https://oauth2.googleapis.com/token",
            data=body,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as e:
        raise GoogleOAuthError("token exchange failed") from e
    id_tok = data.get("id_token")
    if not id_tok or not isinstance(id_tok, str):
        raise GoogleOAuthError("missing id_token")
    try:
        info = id_token.verify_oauth2_token(  # type: ignore[no-untyped-call]
            id_tok,
            google_requests.Request(),
            settings.google_client_id,
        )
    except ValueError as e:
        raise GoogleOAuthError("invalid id_token") from e
    subject = str(info.get("sub", ""))
    email = str(info.get("email", ""))
    name = info.get("name")
    full_name = str(name) if name else None
    if not subject or not email:
        raise GoogleOAuthError("missing profile fields")
    return GoogleProfile(subject=subject, email=email.lower(), full_name=full_name)
