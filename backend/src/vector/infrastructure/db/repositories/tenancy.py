"""Tenant, user, membership, identity queries."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.infrastructure.db.models.identity import UserIdentity
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User


def get_tenant_by_slug(session: Session, slug: str) -> Tenant | None:
    return session.scalar(select(Tenant).where(Tenant.slug == slug))


def get_identity_by_provider_subject(
    session: Session,
    provider: str,
    subject: str,
) -> UserIdentity | None:
    stmt = select(UserIdentity).where(
        UserIdentity.provider == provider,
        UserIdentity.provider_subject == subject,
    )
    return session.scalar(stmt)


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email))


def get_user_by_id(session: Session, user_id: uuid.UUID) -> User | None:
    return session.scalar(select(User).where(User.id == user_id))


def get_membership_for_user_tenant(
    session: Session,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> TenantMembership | None:
    stmt = select(TenantMembership).where(
        TenantMembership.user_id == user_id,
        TenantMembership.tenant_id == tenant_id,
    )
    return session.scalar(stmt)


def list_memberships_for_user(session: Session, user_id: uuid.UUID) -> list[TenantMembership]:
    stmt = (
        select(TenantMembership)
        .where(TenantMembership.user_id == user_id)
        .order_by(TenantMembership.created_at.asc())
    )
    return list(session.scalars(stmt).all())


def get_tenant_by_id(session: Session, tenant_id: uuid.UUID) -> Tenant | None:
    return session.scalar(select(Tenant).where(Tenant.id == tenant_id))


def get_first_user_for_tenant(session: Session, tenant_id: uuid.UUID) -> User | None:
    stmt = (
        select(TenantMembership)
        .where(TenantMembership.tenant_id == tenant_id)
        .order_by(TenantMembership.created_at.asc())
        .limit(1)
    )
    m = session.scalar(stmt)
    if m is None:
        return None
    return get_user_by_id(session, m.user_id)


def list_all_tenants(session: Session, *, limit: int = 500) -> list[Tenant]:
    stmt = select(Tenant).order_by(Tenant.created_at.desc()).limit(limit)
    return list(session.scalars(stmt).all())


def list_connected_connector_providers(session: Session, tenant_id: uuid.UUID) -> list[str]:
    """Provider keys from active tenant_connections (e.g. github, linear)."""
    stmt = (
        select(TenantConnection.provider)
        .where(
            TenantConnection.tenant_id == tenant_id,
            TenantConnection.status == "active",
        )
        .order_by(TenantConnection.created_at.asc())
    )
    return list(session.scalars(stmt).all())
