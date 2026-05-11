"""Persistence for Calls (Gemini/Google) OAuth ↔ tenant links."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.cortex.connectors.provider_keys import CONNECTION_PROVIDER_CALLS
from vector.infrastructure.db.models.calls_connection_detail import CallsConnectionDetail
from vector.infrastructure.db.models.tenant_connection import TenantConnection


@dataclass(frozen=True)
class CallsTenantLink:
    connection: TenantConnection
    detail: CallsConnectionDetail

    @property
    def tenant_id(self) -> uuid.UUID:
        return self.connection.tenant_id


def get_calls_connection_for_tenant(session: Session, tenant_id: uuid.UUID) -> CallsTenantLink | None:
    stmt = (
        select(TenantConnection, CallsConnectionDetail)
        .outerjoin(CallsConnectionDetail, CallsConnectionDetail.connection_id == TenantConnection.id)
        .where(
            TenantConnection.tenant_id == tenant_id,
            TenantConnection.provider == CONNECTION_PROVIDER_CALLS,
        )
    )
    row = session.execute(stmt).one_or_none()
    if row is None:
        return None
    conn, detail = row
    if detail is None:
        return None
    return CallsTenantLink(connection=conn, detail=detail)


def upsert_calls_oauth_connection(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    connected_by_user_id: uuid.UUID,
    access_token: str,
    refresh_token: str | None,
    token_expires_at: datetime | None,
    provider_user_id: str | None,
    provider_email: str | None,
    connected_at: datetime | None,
) -> CallsTenantLink:
    link = get_calls_connection_for_tenant(session, tenant_id)
    if link is None:
        connection = TenantConnection(
            tenant_id=tenant_id,
            provider=CONNECTION_PROVIDER_CALLS,
            status="active",
            connected_by_user_id=connected_by_user_id,
            display_name=provider_email,
        )
        session.add(connection)
        session.flush()
        detail = CallsConnectionDetail(
            connection_id=connection.id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
            connected_at=connected_at,
        )
        session.add(detail)
        session.flush()
        return CallsTenantLink(connection=connection, detail=detail)

    c = link.connection
    d = link.detail
    c.connected_by_user_id = connected_by_user_id
    c.display_name = provider_email
    d.access_token = access_token
    d.refresh_token = refresh_token
    d.token_expires_at = token_expires_at
    d.provider_user_id = provider_user_id
    d.provider_email = provider_email
    d.connected_at = connected_at
    session.flush()
    return CallsTenantLink(connection=c, detail=d)


def delete_calls_connection_for_tenant(session: Session, tenant_id: uuid.UUID) -> bool:
    link = get_calls_connection_for_tenant(session, tenant_id)
    if link is None:
        return False
    session.delete(link.connection)
    session.flush()
    return True
