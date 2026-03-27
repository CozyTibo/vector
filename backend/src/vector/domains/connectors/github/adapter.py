"""GitHub connector registration: status + disconnect (no HTTP)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from vector.contracts.connectors import GithubConnectorDetails, GithubConnectorStatusItem
from vector.domains.connectors.github.install_flow import github_connector_configured
from vector.domains.connectors.provider_keys import CONNECTION_PROVIDER_GITHUB
from vector.domains.connectors.runtime import ConnectorRuntime
from vector.infrastructure.db.repositories import github_connection as gh_repo
from vector.infrastructure.db.repositories.projection_debug_queries import (
    last_raw_fetched_at_for_connection,
)
from vector.settings import Settings

_GITHUB_LABEL = "GitHub"


def github_status_item(
    session: Session,
    settings: Settings,
    tenant_id: uuid.UUID,
) -> GithubConnectorStatusItem:
    if not github_connector_configured(settings):
        return GithubConnectorStatusItem(
            display_name=_GITHUB_LABEL,
            connector_configured=False,
            connected=False,
            details=None,
        )
    link = gh_repo.get_github_connection_for_tenant(session, tenant_id)
    if link is None:
        return GithubConnectorStatusItem(
            display_name=_GITHUB_LABEL,
            connector_configured=True,
            connected=False,
            details=None,
        )
    cid = link.connection.id
    last_sync = last_raw_fetched_at_for_connection(session, cid)
    return GithubConnectorStatusItem(
        display_name=_GITHUB_LABEL,
        connector_configured=True,
        connected=True,
        details=GithubConnectorDetails(
            connection_id=cid,
            installation_id=link.installation_id,
            account_login=link.account_login,
            account_type=link.account_type,
            last_sync_at=last_sync,
        ),
    )


def github_disconnect(session: Session, tenant_id: uuid.UUID) -> None:
    gh_repo.delete_github_connection_for_tenant(session, tenant_id)


def github_connector_runtime() -> ConnectorRuntime:
    return ConnectorRuntime(
        id=CONNECTION_PROVIDER_GITHUB,
        display_name=_GITHUB_LABEL,
        status_for_tenant=github_status_item,
        disconnect_tenant=github_disconnect,
    )
