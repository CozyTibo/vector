"""Linear connector registration: status + disconnect (no HTTP)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from vector.contracts.connectors import LinearConnectorDetails, LinearConnectorStatusItem
from vector.domains.connectors.linear.oauth_flow import linear_connector_configured
from vector.domains.connectors.provider_keys import CONNECTION_PROVIDER_LINEAR
from vector.domains.connectors.runtime import ConnectorRuntime
from vector.infrastructure.db.repositories import linear_connection as linear_repo
from vector.settings import Settings

_LINEAR_LABEL = "Linear"


def linear_status_item(
    session: Session,
    settings: Settings,
    tenant_id: uuid.UUID,
) -> LinearConnectorStatusItem:
    if not linear_connector_configured(settings):
        return LinearConnectorStatusItem(
            display_name=_LINEAR_LABEL,
            connector_configured=False,
            connected=False,
            details=None,
        )
    link = linear_repo.get_linear_connection_for_tenant(session, tenant_id)
    if link is None:
        return LinearConnectorStatusItem(
            display_name=_LINEAR_LABEL,
            connector_configured=True,
            connected=False,
            details=None,
        )
    d = link.detail
    cid = link.connection.id
    return LinearConnectorStatusItem(
        display_name=_LINEAR_LABEL,
        connector_configured=True,
        connected=True,
        details=LinearConnectorDetails(
            connection_id=cid,
            organization_id=d.linear_organization_id,
            organization_name=d.linear_organization_name,
            last_sync_at=None,
        ),
    )


def linear_disconnect(session: Session, tenant_id: uuid.UUID) -> None:
    linear_repo.delete_linear_connection_for_tenant(session, tenant_id)


def linear_connector_runtime() -> ConnectorRuntime:
    return ConnectorRuntime(
        id=CONNECTION_PROVIDER_LINEAR,
        display_name=_LINEAR_LABEL,
        status_for_tenant=linear_status_item,
        disconnect_tenant=linear_disconnect,
    )
