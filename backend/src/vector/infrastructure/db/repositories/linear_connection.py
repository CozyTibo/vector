"""Persistence for Linear OAuth ↔ tenant links."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.connectors.provider_keys import CONNECTION_PROVIDER_LINEAR
from vector.infrastructure.db.models.linear_connection_detail import LinearConnectionDetail
from vector.infrastructure.db.models.tenant_connection import TenantConnection


@dataclass(frozen=True)
class LinearTenantLink:
    connection: TenantConnection
    detail: LinearConnectionDetail

    @property
    def tenant_id(self) -> uuid.UUID:
        return self.connection.tenant_id


def get_linear_connection_for_tenant(
    session: Session,
    tenant_id: uuid.UUID,
) -> LinearTenantLink | None:
    stmt = (
        select(TenantConnection, LinearConnectionDetail)
        .outerjoin(
            LinearConnectionDetail,
            LinearConnectionDetail.connection_id == TenantConnection.id,
        )
        .where(
            TenantConnection.tenant_id == tenant_id,
            TenantConnection.provider == CONNECTION_PROVIDER_LINEAR,
        )
    )
    row = session.execute(stmt).one_or_none()
    if row is None:
        return None
    conn, detail = row
    if detail is None:
        return None
    return LinearTenantLink(connection=conn, detail=detail)


def upsert_linear_oauth_connection(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connected_by_user_id: uuid.UUID,
    access_token: str,
    refresh_token: str | None,
    token_expires_at: datetime | None,
    organization_id: str | None,
    organization_name: str | None,
) -> LinearTenantLink:
    link = get_linear_connection_for_tenant(session, tenant_id)
    if link is None:
        connection = TenantConnection(
            tenant_id=tenant_id,
            provider=CONNECTION_PROVIDER_LINEAR,
            status="active",
            connected_by_user_id=connected_by_user_id,
        )
        session.add(connection)
        session.flush()
        detail = LinearConnectionDetail(
            connection_id=connection.id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            linear_organization_id=organization_id,
            linear_organization_name=organization_name,
        )
        session.add(detail)
        session.flush()
        return LinearTenantLink(connection=connection, detail=detail)

    c = link.connection
    d = link.detail
    c.connected_by_user_id = connected_by_user_id
    d.access_token = access_token
    d.refresh_token = refresh_token
    d.token_expires_at = token_expires_at
    d.linear_organization_id = organization_id
    d.linear_organization_name = organization_name
    session.flush()
    return LinearTenantLink(connection=c, detail=d)


def delete_linear_connection_for_tenant(session: Session, tenant_id: uuid.UUID) -> bool:
    link = get_linear_connection_for_tenant(session, tenant_id)
    if link is None:
        return False
    session.delete(link.connection)
    session.flush()
    return True
