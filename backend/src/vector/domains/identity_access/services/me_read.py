"""Load /me aggregate from session claims."""

from __future__ import annotations

from sqlalchemy.orm import Session

from vector.contracts.me import MeResponse
from vector.domains.identity_access.errors import NoMembershipError
from vector.domains.identity_access.services.session_jwt import SessionClaims
from vector.domains.onboarding.constants import STATUS_COMPLETED
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.repositories import onboarding as onboarding_repo
from vector.infrastructure.db.repositories import tenancy as tenancy_repo
from vector.settings import get_settings


def assert_membership(session: Session, claims: SessionClaims) -> TenantMembership:
    membership = tenancy_repo.get_membership_for_user_tenant(
        session,
        claims.user_id,
        claims.tenant_id,
    )
    if membership is None:
        raise NoMembershipError("no membership for session tenant")
    return membership


def build_me_response(session: Session, claims: SessionClaims) -> MeResponse:
    membership = assert_membership(session, claims)
    user = tenancy_repo.get_user_by_id(session, claims.user_id)
    tenant = tenancy_repo.get_tenant_by_id(session, claims.tenant_id)
    if user is None or tenant is None:
        raise NoMembershipError("stale session")
    ob = onboarding_repo.get_onboarding_for_tenant(session, tenant.id)
    onboarding_completed = ob is not None and ob.status == STATUS_COMPLETED
    connected = tenancy_repo.list_connected_connector_providers(session, tenant.id)
    settings = get_settings()
    env = settings.env.strip().lower()
    use_mock = env == "development" and settings.vector_use_mock_connectors
    return MeResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=tenant.id,
        company_name=tenant.company_name,
        tenant_slug=tenant.slug,
        role=membership.role,
        onboarding_completed=onboarding_completed,
        connected_connectors=connected,
        use_mock_connectors=use_mock,
    )
