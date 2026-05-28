"""Start Slack OAuth URL + complete authorization callback."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.provider_keys import CONNECTION_PROVIDER_SLACK
from vector.domains.cortex.connectors.slack.errors import (
    InvalidSlackOAuthStateError,
    SlackConnectorNotConfiguredError,
    SlackInstallStateMembershipError,
    SlackOAuthError,
    SlackWorkspaceConflictError,
)
from vector.domains.cortex.connectors.slack.http_client import (
    SlackOAuthV2Access,
    exchange_slack_authorization_code,
    slack_redirect_uri,
)
from vector.domains.cortex.connectors.slack.install_state import (
    create_slack_oauth_state_token,
    parse_slack_oauth_state_token,
)
from vector.infrastructure.db.models.slack_connection_detail import SlackConnectionDetail
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.repositories import slack_connection as slack_repo
from vector.infrastructure.db.repositories import tenancy as tenancy_repo
from vector.settings import Settings


def slack_connector_configured(settings: Settings) -> bool:
    return bool(settings.slack_client_id.strip() and settings.slack_client_secret.strip())


def slack_oauth_error_frontend_redirect_url(
    settings: Settings,
    state: str | None,
    error_token: str,
) -> str:
    """Build `…?slack_error=…` (or `&`) on the same path the user started OAuth from (e.g. /app/onboarding)."""
    front = settings.frontend_url.rstrip("/")
    base = f"{front}/"
    if state:
        try:
            claims = parse_slack_oauth_state_token(settings, state)
        except InvalidSlackOAuthStateError:
            pass
        else:
            if claims.return_to:
                base = f"{front}{claims.return_to}"
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}slack_error={error_token}"


def start_slack_oauth_url(
    settings: Settings,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    return_to: str | None = None,
) -> str:
    if not slack_connector_configured(settings):
        raise SlackConnectorNotConfiguredError("slack OAuth is not configured")
    state = create_slack_oauth_state_token(
        settings,
        tenant_id,
        user_id,
        return_to=return_to,
    )
    redirect_uri = slack_redirect_uri(settings)
    scopes = (
        settings.slack_bot_scopes.strip()
        or (
            "channels:read,channels:history,groups:read,groups:history,"
            "chat:write,users:read,users:read.email"
        )
    )
    params = {
        "client_id": settings.slack_client_id.strip(),
        "scope": scopes,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    return f"https://slack.com/oauth/v2/authorize?{urlencode(params)}"


def _other_tenant_for_slack_team(
    session: Session,
    team_id: str,
    *,
    except_tenant_id: uuid.UUID,
) -> uuid.UUID | None:
    stmt = (
        select(TenantConnection.tenant_id)
        .join(
            SlackConnectionDetail,
            SlackConnectionDetail.connection_id == TenantConnection.id,
        )
        .where(
            TenantConnection.provider == CONNECTION_PROVIDER_SLACK,
            SlackConnectionDetail.team_id == team_id,
            TenantConnection.tenant_id != except_tenant_id,
        )
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()


def complete_slack_oauth(
    session: Session,
    settings: Settings,
    *,
    code: str,
    state: str,
    exchange_code: Callable[[Settings, str], SlackOAuthV2Access] | None = None,
) -> tuple[slack_repo.SlackTenantLink, str | None]:
    if not slack_connector_configured(settings):
        raise SlackConnectorNotConfiguredError("slack OAuth is not configured")
    claims: SlackOAuthStateClaims = parse_slack_oauth_state_token(settings, state)
    redirect_after = claims.return_to
    if (
        tenancy_repo.get_membership_for_user_tenant(session, claims.user_id, claims.tenant_id)
        is None
    ):
        raise SlackInstallStateMembershipError()

    ex = exchange_code or exchange_slack_authorization_code
    tok = ex(settings, code)

    other = _other_tenant_for_slack_team(session, tok.team_id, except_tenant_id=claims.tenant_id)
    if other is not None:
        raise SlackWorkspaceConflictError()

    link = slack_repo.upsert_slack_oauth_connection(
        session,
        tenant_id=claims.tenant_id,
        connected_by_user_id=claims.user_id,
        bot_access_token=tok.access_token,
        team_id=tok.team_id,
        team_name=tok.team_name,
        scope=tok.scope,
    )
    return link, redirect_after
