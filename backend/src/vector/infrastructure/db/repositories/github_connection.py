"""Persistence for GitHub ↔ tenant links (spine + GitHub details)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from vector.domains.connectors.provider_keys import CONNECTION_PROVIDER_GITHUB
from vector.infrastructure.db.models.github_connection_detail import GithubConnectionDetail
from vector.infrastructure.db.models.tenant_connection import TenantConnection


@dataclass(frozen=True)
class GithubTenantLink:
    """Joined view: one GitHub install for a tenant."""

    connection: TenantConnection
    detail: GithubConnectionDetail

    @property
    def tenant_id(self) -> uuid.UUID:
        return self.connection.tenant_id

    @property
    def installation_id(self) -> int:
        return self.detail.installation_id

    @property
    def account_login(self) -> str:
        return self.detail.account_login

    @property
    def account_type(self) -> str:
        return self.detail.account_type


def get_github_connection_for_tenant(
    session: Session,
    tenant_id: uuid.UUID,
) -> GithubTenantLink | None:
    stmt = (
        select(TenantConnection, GithubConnectionDetail)
        .outerjoin(
            GithubConnectionDetail,
            GithubConnectionDetail.connection_id == TenantConnection.id,
        )
        .where(
            TenantConnection.tenant_id == tenant_id,
            TenantConnection.provider == CONNECTION_PROVIDER_GITHUB,
        )
    )
    row = session.execute(stmt).one_or_none()
    if row is None:
        return None
    conn, detail = row
    if detail is None:
        return None
    return GithubTenantLink(connection=conn, detail=detail)


def get_github_connection_for_installation(
    session: Session,
    installation_id: int,
) -> GithubTenantLink | None:
    stmt = (
        select(GithubConnectionDetail)
        .where(GithubConnectionDetail.installation_id == installation_id)
        .options(selectinload(GithubConnectionDetail.connection))
    )
    detail = session.scalar(stmt)
    if detail is None:
        return None
    return GithubTenantLink(connection=detail.connection, detail=detail)


def upsert_github_connection(
    session: Session,
    *,
    tenant_id: uuid.UUID,
    installation_id: int,
    account_id: int,
    account_login: str,
    account_type: str,
    connected_by_user_id: uuid.UUID,
) -> GithubTenantLink:
    link = get_github_connection_for_tenant(session, tenant_id)
    if link is None:
        connection = TenantConnection(
            tenant_id=tenant_id,
            provider=CONNECTION_PROVIDER_GITHUB,
            status="active",
            connected_by_user_id=connected_by_user_id,
        )
        session.add(connection)
        session.flush()
        detail = GithubConnectionDetail(
            connection_id=connection.id,
            installation_id=installation_id,
            account_id=account_id,
            account_login=account_login,
            account_type=account_type,
        )
        session.add(detail)
        session.flush()
        return GithubTenantLink(connection=connection, detail=detail)

    c = link.connection
    d = link.detail
    c.connected_by_user_id = connected_by_user_id
    d.installation_id = installation_id
    d.account_id = account_id
    d.account_login = account_login
    d.account_type = account_type
    session.flush()
    return GithubTenantLink(connection=c, detail=d)


def delete_github_connection_for_tenant(
    session: Session,
    tenant_id: uuid.UUID,
) -> bool:
    """Remove the GitHub link for this tenant. Returns True if a row was deleted."""
    link = get_github_connection_for_tenant(session, tenant_id)
    if link is None:
        return False
    session.delete(link.connection)
    session.flush()
    return True
