"""Persistence for Slack OAuth ↔ tenant links."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.provider_keys import CONNECTION_PROVIDER_SLACK
from vector.infrastructure.db.models.slack_connection_detail import SlackConnectionDetail
from vector.infrastructure.db.models.tenant_connection import TenantConnection


@dataclass(frozen=True)
class SlackTenantLink:
    connection: TenantConnection
    detail: SlackConnectionDetail

    @property
    def tenant_id(self) -> uuid.UUID:
        return self.connection.tenant_id


def get_slack_connection_by_team_id(session: Session, team_id: str) -> SlackTenantLink | None:
    tid = team_id.strip()
    if not tid:
        return None
    stmt = (
        select(TenantConnection, SlackConnectionDetail)
        .outerjoin(
            SlackConnectionDetail,
            SlackConnectionDetail.connection_id == TenantConnection.id,
        )
        .where(
            TenantConnection.provider == CONNECTION_PROVIDER_SLACK,
            SlackConnectionDetail.team_id == tid,
        )
    )
    row = session.execute(stmt).one_or_none()
    if row is None:
        return None
    conn, detail = row
    if detail is None:
        return None
    return SlackTenantLink(connection=conn, detail=detail)


def get_slack_connection_for_tenant(
    session: Session,
    tenant_id: uuid.UUID,
) -> SlackTenantLink | None:
    stmt = (
        select(TenantConnection, SlackConnectionDetail)
        .outerjoin(
            SlackConnectionDetail,
            SlackConnectionDetail.connection_id == TenantConnection.id,
        )
        .where(
            TenantConnection.tenant_id == tenant_id,
            TenantConnection.provider == CONNECTION_PROVIDER_SLACK,
        )
    )
    row = session.execute(stmt).one_or_none()
    if row is None:
        return None
    conn, detail = row
    if detail is None:
        return None
    return SlackTenantLink(connection=conn, detail=detail)


def upsert_slack_oauth_connection(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connected_by_user_id: uuid.UUID,
    bot_access_token: str,
    team_id: str,
    team_name: str | None,
    scope: str | None,
) -> SlackTenantLink:
    link = get_slack_connection_for_tenant(session, tenant_id)
    if link is None:
        connection = TenantConnection(
            tenant_id=tenant_id,
            provider=CONNECTION_PROVIDER_SLACK,
            status="active",
            connected_by_user_id=connected_by_user_id,
            display_name=team_name,
        )
        session.add(connection)
        session.flush()
        detail = SlackConnectionDetail(
            connection_id=connection.id,
            bot_access_token=bot_access_token,
            team_id=team_id,
            team_name=team_name,
            scope=scope,
        )
        session.add(detail)
        session.flush()
        return SlackTenantLink(connection=connection, detail=detail)

    c = link.connection
    d = link.detail
    c.connected_by_user_id = connected_by_user_id
    c.display_name = team_name
    d.bot_access_token = bot_access_token
    d.team_id = team_id
    d.team_name = team_name
    d.scope = scope
    session.flush()
    return SlackTenantLink(connection=c, detail=d)


def delete_slack_connection_for_tenant(session: Session, tenant_id: uuid.UUID) -> bool:
    link = get_slack_connection_for_tenant(session, tenant_id)
    if link is None:
        return False
    session.delete(link.connection)
    session.flush()
    return True
