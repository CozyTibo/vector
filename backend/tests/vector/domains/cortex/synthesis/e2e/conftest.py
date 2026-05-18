"""Shared fixtures for Phase 08 synthesis E2E tests."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session


@pytest.fixture
def synthesis_e2e_tenant_id(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8e2e-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 E2E")
    tenant = Tenant(
        company_name="P8 E2E Tenant",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8e2e-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


@pytest.fixture
def synthesis_e2e_bundle_id(db_session: Session, synthesis_e2e_tenant_id: uuid.UUID) -> str | None:
    from vector.domains.cortex.canonical.transform_runtime import resolve_default_bundle_id_for_stub_transform

    return resolve_default_bundle_id_for_stub_transform(db_session, synthesis_e2e_tenant_id)
