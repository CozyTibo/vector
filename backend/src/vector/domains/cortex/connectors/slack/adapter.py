"""Slack connector registration: status + disconnect (no HTTP)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from vector.contracts.connectors import SlackConnectorDetails, SlackConnectorStatusItem
from vector.domains.cortex.connectors.provider_keys import CONNECTION_PROVIDER_SLACK
from vector.domains.cortex.connectors.runtime import ConnectorRuntime
from vector.domains.cortex.connectors.slack.oauth_flow import slack_connector_configured
from vector.infrastructure.db.repositories import slack_connection as slack_repo
from vector.settings import Settings

_SLACK_LABEL = "Slack"


def slack_status_item(
    session: Session,
    settings: Settings,
    tenant_id: uuid.UUID,
) -> SlackConnectorStatusItem:
    if not slack_connector_configured(settings):
        return SlackConnectorStatusItem(
            display_name=_SLACK_LABEL,
            connector_configured=False,
            connected=False,
            details=None,
        )
    link = slack_repo.get_slack_connection_for_tenant(session, tenant_id)
    if link is None:
        return SlackConnectorStatusItem(
            display_name=_SLACK_LABEL,
            connector_configured=True,
            connected=False,
            details=None,
        )
    d = link.detail
    cid = link.connection.id
    return SlackConnectorStatusItem(
        display_name=_SLACK_LABEL,
        connector_configured=True,
        connected=True,
        details=SlackConnectorDetails(
            connection_id=cid,
            team_id=d.team_id,
            team_name=d.team_name,
            last_sync_at=None,
        ),
    )


def slack_disconnect(session: Session, tenant_id: uuid.UUID) -> None:
    slack_repo.delete_slack_connection_for_tenant(session, tenant_id)


def slack_connector_runtime() -> ConnectorRuntime:
    return ConnectorRuntime(
        id=CONNECTION_PROVIDER_SLACK,
        display_name=_SLACK_LABEL,
        status_for_tenant=slack_status_item,
        disconnect_tenant=slack_disconnect,
    )
