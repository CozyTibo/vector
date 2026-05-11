"""Start Calls OAuth URL + complete authorization callback."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.calls.errors import (
    CallsConnectorNotConfiguredError,
    CallsInstallStateMembershipError,
)
from vector.domains.cortex.connectors.calls.http_client import (
    CallsTokenResponse,
    calls_redirect_uri,
    calls_token_expires_at,
    exchange_calls_authorization_code,
    fetch_calls_google_profile,
)
from vector.domains.cortex.connectors.calls.install_state import (
    CallsOAuthStateClaims,
    create_calls_oauth_state_token,
    parse_calls_oauth_state_token,
)
from vector.infrastructure.db.repositories import calls_connection as calls_repo
from vector.infrastructure.db.repositories import tenancy as tenancy_repo
from vector.settings import Settings


def calls_connector_configured(settings: Settings) -> bool:
    return bool(settings.google_client_id.strip() and settings.google_client_secret.strip())


def start_calls_oauth_url(
    settings: Settings,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    return_to: str | None = None,
) -> str:
    if not calls_connector_configured(settings):
        raise CallsConnectorNotConfiguredError("calls OAuth is not configured")
    state = create_calls_oauth_state_token(settings, tenant_id, user_id, return_to=return_to)
    params = {
        "client_id": settings.google_client_id.strip(),
        "redirect_uri": calls_redirect_uri(settings),
        "response_type": "code",
        "scope": "openid email profile https://www.googleapis.com/auth/calendar.readonly",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{settings.calls_google_oauth_authorize_url()}?{urlencode(params)}"


def complete_calls_oauth(
    session: Session,
    settings: Settings,
    *,
    code: str,
    state: str,
    exchange_code: Callable[[Settings, str], CallsTokenResponse] | None = None,
    fetch_profile: Callable[[str], tuple[str | None, str | None]] | None = None,
) -> tuple[calls_repo.CallsTenantLink, str | None]:
    if not calls_connector_configured(settings):
        raise CallsConnectorNotConfiguredError("calls OAuth is not configured")
    claims: CallsOAuthStateClaims = parse_calls_oauth_state_token(settings, state)
    redirect_after = claims.return_to
    if tenancy_repo.get_membership_for_user_tenant(session, claims.user_id, claims.tenant_id) is None:
        raise CallsInstallStateMembershipError()
    ex = exchange_code or exchange_calls_authorization_code
    prof = fetch_profile or fetch_calls_google_profile
    tok = ex(settings, code)
    provider_user_id, provider_email = prof(tok.access_token)
    link = calls_repo.upsert_calls_oauth_connection(
        session,
        tenant_id=claims.tenant_id,
        connected_by_user_id=claims.user_id,
        access_token=tok.access_token,
        refresh_token=tok.refresh_token,
        token_expires_at=calls_token_expires_at(tok.expires_in),
        provider_user_id=provider_user_id,
        provider_email=provider_email,
        connected_at=datetime.now(UTC),
    )
    return link, redirect_after
