"""Notion connector registration: status + disconnect (no HTTP)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from vector.contracts.connectors import NotionConnectorDetails, NotionConnectorStatusItem
from vector.domains.cortex.connectors.notion.oauth_flow import notion_connector_configured
from vector.domains.cortex.connectors.provider_keys import CONNECTION_PROVIDER_NOTION
from vector.domains.cortex.connectors.runtime import ConnectorRuntime
from vector.infrastructure.db.repositories import notion_connection as notion_repo
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
    return NotionConnectorStatusItem(
        display_name=_NOTION_LABEL,
        connector_configured=True,
        connected=True,
        details=NotionConnectorDetails(
            connection_id=cid,
            workspace_id=link.detail.workspace_id,
            workspace_name=link.detail.workspace_name,
            last_sync_at=None,
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
