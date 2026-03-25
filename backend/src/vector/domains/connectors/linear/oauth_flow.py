"""Start Linear OAuth URL + complete authorization callback."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from vector.domains.connectors.linear.errors import (
    LinearConnectorNotConfiguredError,
    LinearInstallStateMembershipError,
)
from vector.domains.connectors.linear.http_client import (
    LinearTokenResponse,
    exchange_linear_authorization_code,
    fetch_linear_viewer_org,
    linear_redirect_uri,
    token_expires_at,
)
from vector.domains.connectors.linear.install_state import (
    LinearOAuthStateClaims,
    create_linear_oauth_state_token,
    parse_linear_oauth_state_token,
)
from vector.infrastructure.db.repositories import linear_connection as linear_repo
from vector.infrastructure.db.repositories import tenancy as tenancy_repo
from vector.settings import Settings


def linear_connector_configured(settings: Settings) -> bool:
    return bool(settings.linear_client_id.strip() and settings.linear_client_secret.strip())


def start_linear_oauth_url(settings: Settings, tenant_id: uuid.UUID, user_id: uuid.UUID) -> str:
    if not linear_connector_configured(settings):
        raise LinearConnectorNotConfiguredError("linear OAuth is not configured")
    state = create_linear_oauth_state_token(settings, tenant_id, user_id)
    redirect_uri = linear_redirect_uri(settings)
    params = {
        "response_type": "code",
        "client_id": settings.linear_client_id.strip(),
        "redirect_uri": redirect_uri,
        "scope": "read",
        "state": state,
    }
    return f"https://linear.app/oauth/authorize?{urlencode(params)}"


def complete_linear_oauth(
    session: Session,
    settings: Settings,
    *,
    code: str,
    state: str,
    exchange_code: Callable[[Settings, str], LinearTokenResponse] | None = None,
    fetch_org: Callable[[str], tuple[str | None, str | None]] | None = None,
) -> linear_repo.LinearTenantLink:
    if not linear_connector_configured(settings):
        raise LinearConnectorNotConfiguredError("linear OAuth is not configured")
    claims: LinearOAuthStateClaims = parse_linear_oauth_state_token(settings, state)
    if (
        tenancy_repo.get_membership_for_user_tenant(session, claims.user_id, claims.tenant_id)
        is None
    ):
        raise LinearInstallStateMembershipError()

    ex = exchange_code or exchange_linear_authorization_code
    org_fn = fetch_org or fetch_linear_viewer_org

    tok = ex(settings, code)
    expires_at = token_expires_at(tok.expires_in)

    org_id, org_name = org_fn(tok.access_token)

    return linear_repo.upsert_linear_oauth_connection(
        session,
        tenant_id=claims.tenant_id,
        connected_by_user_id=claims.user_id,
        access_token=tok.access_token,
        refresh_token=tok.refresh_token,
        token_expires_at=expires_at,
        organization_id=org_id,
        organization_name=org_name,
    )
