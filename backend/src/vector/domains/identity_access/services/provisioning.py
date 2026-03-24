"""Create / link users, tenants, memberships from OAuth profile."""

from __future__ import annotations

from sqlalchemy.orm import Session

from vector.domains.identity_access.email_domain import email_domain_from_address
from vector.domains.identity_access.slug import unique_slug
from vector.infrastructure.db.models.identity import UserIdentity
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User
from vector.infrastructure.db.repositories import tenancy as tenancy_repo

GOOGLE = "google"


def provision_google_profile(
    session: Session,
    *,
    subject: str,
    email: str,
    full_name: str | None,
) -> tuple[User, Tenant, TenantMembership]:
    """
    Idempotent for same Google subject: returns existing membership context.

    New Google subject: creates user (or links by email), tenant, owner membership.
    """
    domain = email_domain_from_address(email)
    existing_identity = tenancy_repo.get_identity_by_provider_subject(session, GOOGLE, subject)
    if existing_identity is not None:
        linked_user = existing_identity.user
        assert linked_user is not None
        memberships = tenancy_repo.list_memberships_for_user(session, linked_user.id)
        if not memberships:
            tenant, membership = _create_tenant_with_owner(
                session,
                user=linked_user,
                email=email,
                domain=domain,
            )
            return linked_user, tenant, membership
        m0 = memberships[0]
        tenant_row = tenancy_repo.get_tenant_by_id(session, m0.tenant_id)
        if tenant_row is None:
            msg = "tenant missing for membership"
            raise RuntimeError(msg)
        return linked_user, tenant_row, m0

    row = tenancy_repo.get_user_by_email(session, email)
    if row is None:
        user = User(email=email, full_name=full_name)
        session.add(user)
        session.flush()
    else:
        user = row
    identity = UserIdentity(user_id=user.id, provider=GOOGLE, provider_subject=subject)
    session.add(identity)
    session.flush()

    memberships = tenancy_repo.list_memberships_for_user(session, user.id)
    if memberships:
        m0 = memberships[0]
        tenant_row = tenancy_repo.get_tenant_by_id(session, m0.tenant_id)
        if tenant_row is None:
            msg = "tenant missing for membership"
            raise RuntimeError(msg)
        return user, tenant_row, m0

    tenant, membership = _create_tenant_with_owner(session, user=user, email=email, domain=domain)
    return user, tenant, membership


def bootstrap_tenant_for_new_user(
    session: Session,
    *,
    user: User,
    email: str,
    company_name: str | None = None,
) -> tuple[Tenant, TenantMembership]:
    """First tenant + owner membership (email/password sign-up)."""
    domain = email_domain_from_address(email)
    return _create_tenant_with_owner(
        session,
        user=user,
        email=email,
        domain=domain,
        company_name=company_name,
    )


def _create_tenant_with_owner(
    session: Session,
    *,
    user: User,
    email: str,
    domain: str,
    company_name: str | None = None,
) -> tuple[Tenant, TenantMembership]:
    def _slug_taken(slug: str) -> Tenant | None:
        return tenancy_repo.get_tenant_by_slug(session, slug)

    slug = unique_slug(_slug_taken, domain)
    default_co = f"{user.full_name or email.split('@')[0]} ({domain})"
    company = company_name.strip() if company_name and company_name.strip() else default_co
    tenant = Tenant(
        company_name=company,
        primary_email=email,
        email_domain=domain,
        slug=slug,
        status="active",
    )
    session.add(tenant)
    session.flush()
    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=user.id,
        role="owner",
    )
    session.add(membership)
    session.flush()
    return tenant, membership
