"""dev_force_complete_website_onboarding_for_tenant (integration)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.onboarding.constants import STATUS_COMPLETED, STEP_THANK_YOU
from vector.domains.onboarding.onboarding_commands import dev_force_complete_website_onboarding_for_tenant
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.onboarding_state import OnboardingState
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


@pytest.mark.integration
def test_dev_force_marks_onboarding_completed(db_session: Session) -> None:
    user = User(email=f"dev-skip-{uuid.uuid4().hex}@example.com", full_name="Skip User")
    tenant = Tenant(
        company_name="SkipCo",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"skip-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.add(
        OnboardingState(
            tenant_id=tenant.id,
            status="in_progress",
            current_step="CHAT_PROFILE",
            answers_json={},
            version=1,
        ),
    )
    db_session.commit()

    out = dev_force_complete_website_onboarding_for_tenant(db_session, tenant_id=tenant.id)
    db_session.commit()

    assert out.status == STATUS_COMPLETED
    assert out.current_step == STEP_THANK_YOU
    row = db_session.scalar(select(OnboardingState).where(OnboardingState.tenant_id == tenant.id))
    assert row is not None
    assert row.status == STATUS_COMPLETED
    assert row.current_step == STEP_THANK_YOU
