"""Orchestrate OAuth redirect and callback (no HTTP)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from vector.domains.identity_access.errors import InvalidOAuthStateError, OAuthNotConfiguredError
from vector.domains.identity_access.services import google_oauth
from vector.domains.identity_access.services.oauth_state import (
    OAuthStatePayload,
    code_challenge_s256,
    create_oauth_state,
    parse_oauth_cookie,
    serialize_oauth_cookie,
)
from vector.domains.identity_access.services.provisioning import provision_google_profile
from vector.domains.identity_access.services.session_jwt import issue_session_token
from vector.settings import Settings


@dataclass(frozen=True)
class GoogleOAuthStart:
    redirect_url: str
    oauth_cookie_value: str


def start_google_oauth(settings: Settings) -> GoogleOAuthStart:
    if not settings.google_client_id or not settings.google_client_secret:
        raise OAuthNotConfiguredError("Google OAuth is not configured")
    payload = create_oauth_state(settings)
    challenge = code_challenge_s256(payload.code_verifier)
    url = google_oauth.google_authorize_url(
        settings,
        state=payload.state,
        code_challenge=challenge,
    )
    cookie = serialize_oauth_cookie(settings, payload)
    return GoogleOAuthStart(redirect_url=url, oauth_cookie_value=cookie)


def _default_google_exchange(
    settings: Settings,
    code: str,
    verifier: str,
) -> google_oauth.GoogleProfile:
    return google_oauth.exchange_code_for_profile(settings, code=code, code_verifier=verifier)


def complete_google_oauth(
    session: Session,
    settings: Settings,
    *,
    code: str,
    state: str,
    oauth_cookie_raw: str | None,
    exchange_profile: Callable[[Settings, str, str], google_oauth.GoogleProfile] | None = None,
) -> str:
    """
    Validate state, exchange code, provision user/tenant, return session JWT.
    """
    if not oauth_cookie_raw:
        raise InvalidOAuthStateError("missing oauth cookie")
    parsed: OAuthStatePayload = parse_oauth_cookie(settings, oauth_cookie_raw)
    if parsed.state != state:
        raise InvalidOAuthStateError("state mismatch")
    exch = exchange_profile or _default_google_exchange
    profile = exch(settings, code, parsed.code_verifier)
    user, tenant, _membership = provision_google_profile(
        session,
        subject=profile.subject,
        email=profile.email,
        full_name=profile.full_name,
    )
    return issue_session_token(settings, user.id, tenant.id)
