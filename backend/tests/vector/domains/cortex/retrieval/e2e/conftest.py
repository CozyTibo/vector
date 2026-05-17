"""Shared fixtures for retrieval E2E tests."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session


@pytest.fixture
def e2e_tenant_id(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"e2e-{uuid.uuid4().hex[:10]}@example.com", full_name="E2E Retrieval")
    tenant = Tenant(
        company_name="E2E Retrieval Tenant",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"e2e-ret-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id
