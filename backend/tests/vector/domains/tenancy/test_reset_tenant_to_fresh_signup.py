"""Reset tenant to fresh signup (integration)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.onboarding.constants import STEP_CHAT_PROFILE, STATUS_IN_PROGRESS
from vector.domains.tenancy.reset_tenant_to_fresh_signup import reset_tenant_to_fresh_signup
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.onboarding_state import OnboardingState
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.tenant_connection import TenantConnection
from vector.infrastructure.db.models.user import User
from vector.infrastructure.db.repositories import onboarding as onboarding_repo


@pytest.mark.integration
def test_reset_tenant_keeps_tenant_and_membership_resets_onboarding(db_session: Session) -> None:
    user = User(email=f"rst-{uuid.uuid4().hex}@example.com", full_name="Rst User")
    tenant = Tenant(
        company_name="ResetCo",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"rst-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
        slack_vector_paused=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.add(
        TenantConnection(
            tenant_id=tenant.id,
            provider="slack",
            status="active",
            connected_by_user_id=user.id,
        ),
    )
    ob = OnboardingState(
        tenant_id=tenant.id,
        status="completed",
        current_step="DONE",
        answers_json={"x": 1},
        version=3,
    )
    db_session.add(ob)
    db_session.commit()

    tid = tenant.id

    out = reset_tenant_to_fresh_signup(db_session, tenant_id=tid)
    db_session.commit()

    t2 = db_session.scalar(select(Tenant).where(Tenant.id == tid))
    assert t2 is not None
    assert t2.company_name == "ResetCo"
    assert t2.workspace_access_enabled is False
    assert t2.slack_vector_paused is False
    assert t2.status == "active"

    assert db_session.scalar(select(TenantConnection).where(TenantConnection.tenant_id == tid)) is None
    assert out["deleted_tenant_connections"] == 1

    ob2 = onboarding_repo.get_onboarding_for_tenant(db_session, tid)
    assert ob2 is not None
    assert ob2.status == STATUS_IN_PROGRESS
    assert ob2.current_step == STEP_CHAT_PROFILE
    assert ob2.answers_json == {}

    m = db_session.scalar(select(TenantMembership).where(TenantMembership.tenant_id == tid))
    assert m is not None
    assert m.user_id == user.id
