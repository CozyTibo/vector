"""Calls connector registration: status + disconnect (no HTTP)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from vector.contracts.connectors import CallsConnectorDetails, CallsConnectorStatusItem
from vector.domains.connectors.calls.oauth_flow import calls_connector_configured
from vector.domains.connectors.provider_keys import CONNECTION_PROVIDER_CALLS
from vector.domains.connectors.runtime import ConnectorRuntime
from vector.infrastructure.db.repositories import calls_connection as calls_repo
from vector.infrastructure.db.repositories.projection_debug_queries import (
    last_raw_fetched_at_for_connection,
)
from vector.settings import Settings

_CALLS_LABEL = "Calls"


def calls_status_item(
    session: Session,
    settings: Settings,
    tenant_id: uuid.UUID,
) -> CallsConnectorStatusItem:
    if not calls_connector_configured(settings):
        return CallsConnectorStatusItem(
            display_name=_CALLS_LABEL,
            connector_configured=False,
            connected=False,
            details=None,
        )
    link = calls_repo.get_calls_connection_for_tenant(session, tenant_id)
    if link is None:
        return CallsConnectorStatusItem(
            display_name=_CALLS_LABEL,
            connector_configured=True,
            connected=False,
            details=None,
        )
    cid = link.connection.id
    last_sync = last_raw_fetched_at_for_connection(session, cid)
    return CallsConnectorStatusItem(
        display_name=_CALLS_LABEL,
        connector_configured=True,
        connected=True,
        details=CallsConnectorDetails(
            connection_id=cid,
            provider_email=link.detail.provider_email,
            last_sync_at=last_sync,
        ),
    )


def calls_disconnect(session: Session, tenant_id: uuid.UUID) -> None:
    calls_repo.delete_calls_connection_for_tenant(session, tenant_id)


def calls_connector_runtime() -> ConnectorRuntime:
    return ConnectorRuntime(
        id=CONNECTION_PROVIDER_CALLS,
        display_name=_CALLS_LABEL,
        status_for_tenant=calls_status_item,
        disconnect_tenant=calls_disconnect,
    )
