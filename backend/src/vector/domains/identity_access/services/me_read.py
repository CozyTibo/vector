"""Load /me aggregate from session claims."""

from __future__ import annotations

from sqlalchemy.orm import Session

from vector.contracts.me import MeResponse
from vector.domains.identity_access.errors import NoMembershipError
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.infrastructure.db.repositories import tenancy as tenancy_repo


def build_me_response(session: Session, claims: SessionClaims) -> MeResponse:
    membership = tenancy_repo.get_membership_for_user_tenant(
        session,
        claims.user_id,
        claims.tenant_id,
    )
    if membership is None:
        raise NoMembershipError("no membership for session tenant")
    user = tenancy_repo.get_user_by_id(session, claims.user_id)
    tenant = tenancy_repo.get_tenant_by_id(session, claims.tenant_id)
    if user is None or tenant is None:
        raise NoMembershipError("stale session")
    return MeResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=tenant.id,
        company_name=tenant.company_name,
        tenant_slug=tenant.slug,
        role=membership.role,
    )
