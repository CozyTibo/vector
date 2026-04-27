"""Notion connector registration: status + disconnect (no HTTP)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from vector.contracts.connectors import NotionConnectorDetails, NotionConnectorStatusItem
from vector.domains.connectors.notion.oauth_flow import notion_connector_configured
from vector.domains.connectors.provider_keys import CONNECTION_PROVIDER_NOTION
from vector.domains.connectors.runtime import ConnectorRuntime
from vector.infrastructure.db.repositories import notion_connection as notion_repo
from vector.infrastructure.db.repositories.projection_debug_queries import (
    last_raw_fetched_at_for_connection,
)
from vector.settings import Settings

_NOTION_LABEL = "Notion"


def notion_status_item(
    session: Session,
    settings: Settings,
    tenant_id: uuid.UUID,
) -> NotionConnectorStatusItem:
    if not notion_connector_configured(settings):
        return NotionConnectorStatusItem(
            display_name=_NOTION_LABEL,
            connector_configured=False,
            connected=False,
            details=None,
        )
    link = notion_repo.get_notion_connection_for_tenant(session, tenant_id)
    if link is None:
        return NotionConnectorStatusItem(
            display_name=_NOTION_LABEL,
            connector_configured=True,
            connected=False,
            details=None,
        )
    cid = link.connection.id
    last_sync = last_raw_fetched_at_for_connection(session, cid)
    return NotionConnectorStatusItem(
        display_name=_NOTION_LABEL,
        connector_configured=True,
        connected=True,
        details=NotionConnectorDetails(
            connection_id=cid,
            workspace_id=link.detail.workspace_id,
            workspace_name=link.detail.workspace_name,
            last_sync_at=last_sync,
        ),
    )


def notion_disconnect(session: Session, tenant_id: uuid.UUID) -> None:
    notion_repo.delete_notion_connection_for_tenant(session, tenant_id)


def notion_connector_runtime() -> ConnectorRuntime:
    return ConnectorRuntime(
        id=CONNECTION_PROVIDER_NOTION,
        display_name=_NOTION_LABEL,
        status_for_tenant=notion_status_item,
        disconnect_tenant=notion_disconnect,
    )
