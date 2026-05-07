"""Persistence for Notion OAuth ↔ tenant links."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.provider_keys import CONNECTION_PROVIDER_NOTION
from vector.infrastructure.db.models.notion_connection_detail import NotionConnectionDetail
from vector.infrastructure.db.models.tenant_connection import TenantConnection


@dataclass(frozen=True)
class NotionTenantLink:
    connection: TenantConnection
    detail: NotionConnectionDetail

    @property
    def tenant_id(self) -> uuid.UUID:
        return self.connection.tenant_id


def get_notion_connection_for_tenant(session: Session, tenant_id: uuid.UUID) -> NotionTenantLink | None:
    stmt = (
        select(TenantConnection, NotionConnectionDetail)
        .outerjoin(NotionConnectionDetail, NotionConnectionDetail.connection_id == TenantConnection.id)
        .where(
            TenantConnection.tenant_id == tenant_id,
            TenantConnection.provider == CONNECTION_PROVIDER_NOTION,
        )
    )
    row = session.execute(stmt).one_or_none()
    if row is None:
        return None
    conn, detail = row
    if detail is None:
        return None
    return NotionTenantLink(connection=conn, detail=detail)


def upsert_notion_oauth_connection(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connected_by_user_id: uuid.UUID,
    access_token: str,
    token_type: str | None,
    workspace_id: str | None,
    workspace_name: str | None,
    workspace_icon: str | None,
    owner_user_id: str | None,
    bot_id: str | None,
    connected_at: datetime | None,
) -> NotionTenantLink:
    link = get_notion_connection_for_tenant(session, tenant_id)
    if link is None:
        connection = TenantConnection(
            tenant_id=tenant_id,
            provider=CONNECTION_PROVIDER_NOTION,
            status="active",
            connected_by_user_id=connected_by_user_id,
            display_name=workspace_name,
        )
        session.add(connection)
        session.flush()
        detail = NotionConnectionDetail(
            connection_id=connection.id,
            access_token=access_token,
            token_type=token_type,
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            workspace_icon=workspace_icon,
            owner_user_id=owner_user_id,
            bot_id=bot_id,
            connected_at=connected_at,
        )
        session.add(detail)
        session.flush()
        return NotionTenantLink(connection=connection, detail=detail)

    c = link.connection
    d = link.detail
    c.connected_by_user_id = connected_by_user_id
    c.display_name = workspace_name
    d.access_token = access_token
    d.token_type = token_type
    d.workspace_id = workspace_id
    d.workspace_name = workspace_name
    d.workspace_icon = workspace_icon
    d.owner_user_id = owner_user_id
    d.bot_id = bot_id
    d.connected_at = connected_at
    session.flush()
    return NotionTenantLink(connection=c, detail=d)


def delete_notion_connection_for_tenant(session: Session, tenant_id: uuid.UUID) -> bool:
    link = get_notion_connection_for_tenant(session, tenant_id)
    if link is None:
        return False
    session.delete(link.connection)
    session.flush()
    return True
