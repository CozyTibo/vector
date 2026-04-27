"""Start Notion OAuth URL + complete authorization callback."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import urlencode

from sqlalchemy.orm import Session

from vector.domains.connectors.notion.errors import (
    NotionConnectorNotConfiguredError,
    NotionInstallStateMembershipError,
)
from vector.domains.connectors.notion.http_client import (
    NotionTokenResponse,
    exchange_notion_authorization_code,
    notion_redirect_uri,
)
from vector.domains.connectors.notion.install_state import (
    NotionOAuthStateClaims,
    create_notion_oauth_state_token,
    parse_notion_oauth_state_token,
)
from vector.infrastructure.db.repositories import notion_connection as notion_repo
from vector.infrastructure.db.repositories import tenancy as tenancy_repo
from vector.settings import Settings


def notion_connector_configured(settings: Settings) -> bool:
    return bool(settings.notion_client_id.strip() and settings.notion_client_secret.strip())


def start_notion_oauth_url(
    settings: Settings,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    return_to: str | None = None,
) -> str:
    if not notion_connector_configured(settings):
        raise NotionConnectorNotConfiguredError("notion OAuth is not configured")
    state = create_notion_oauth_state_token(settings, tenant_id, user_id, return_to=return_to)
    params = {
        "owner": "user",
        "client_id": settings.notion_client_id.strip(),
        "redirect_uri": notion_redirect_uri(settings),
        "response_type": "code",
        "state": state,
    }
    return f"{settings.notion_oauth_authorize_url()}?{urlencode(params)}"


def complete_notion_oauth(
    session: Session,
    settings: Settings,
    *,
    code: str,
    state: str,
    exchange_code: Callable[[Settings, str], NotionTokenResponse] | None = None,
) -> tuple[notion_repo.NotionTenantLink, str | None]:
    if not notion_connector_configured(settings):
        raise NotionConnectorNotConfiguredError("notion OAuth is not configured")
    claims: NotionOAuthStateClaims = parse_notion_oauth_state_token(settings, state)
    redirect_after = claims.return_to
    if tenancy_repo.get_membership_for_user_tenant(session, claims.user_id, claims.tenant_id) is None:
        raise NotionInstallStateMembershipError()
    ex = exchange_code or exchange_notion_authorization_code
    tok = ex(settings, code)
    link = notion_repo.upsert_notion_oauth_connection(
        session,
        tenant_id=claims.tenant_id,
        connected_by_user_id=claims.user_id,
        access_token=tok.access_token,
        token_type=tok.token_type,
        workspace_id=tok.workspace_id,
        workspace_name=tok.workspace_name,
        workspace_icon=tok.workspace_icon,
        owner_user_id=tok.owner_user_id,
        bot_id=tok.bot_id,
        connected_at=datetime.now(UTC),
    )
    return link, redirect_after
