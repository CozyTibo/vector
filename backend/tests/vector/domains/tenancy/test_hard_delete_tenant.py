"""Hard tenant delete (integration)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from vector.domains.tenancy.hard_delete_tenant import hard_delete_tenant
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


@pytest.mark.integration
def test_hard_delete_tenant_removes_tenant_and_membership(db_session: Session) -> None:
    user = User(email=f"del-{uuid.uuid4().hex}@example.com", full_name="Del User")
    tenant = Tenant(
        company_name="WipeCo",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"wipe-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    tid = tenant.id
    uid = user.id

    stats = hard_delete_tenant(db_session, tenant_id=tid)
    db_session.commit()

    assert stats["deleted_tenant_id"] == str(tid)
    assert stats["deleted_company_name"] == "WipeCo"
    assert db_session.scalar(select(Tenant).where(Tenant.id == tid)) is None
    assert db_session.scalar(select(User).where(User.id == uid)) is not None
