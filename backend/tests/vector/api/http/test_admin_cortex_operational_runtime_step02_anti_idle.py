"""Admin HTTP — Phase 08.5 Step 02 anti-idle gate routes."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.operational_runtime.fake_green_prohibition import GP085_ANTI_IDLE01_GATE_ID_V1

pytestmark = pytest.mark.integration


def _tenant_with_owner(db: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p85antidle-{uuid.uuid4().hex[:10]}@example.com", full_name="P85 Anti Idle")
    tenant = Tenant(
        company_name="P85ANTIDLE",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p85antidle-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_catalog_anti_idle_gate(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    resp = client.get(
        "/admin/catalog/cortex/operational-runtime/anti-idle-gate",
        auth=("admin", "integration-admin-password"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["gate_id"] == GP085_ANTI_IDLE01_GATE_ID_V1
    assert body["passed"] is True


def test_admin_tenant_anti_idle_verification_not_found(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    resp = client.get(
        f"/admin/tenants/{uuid.uuid4()}/cortex/operational-runtime/anti-idle-verification",
        auth=("admin", "integration-admin-password"),
    )
    assert resp.status_code == 404


def test_admin_tenant_anti_idle_verification_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    resp = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/anti-idle-verification",
        auth=("admin", "integration-admin-password"),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["gate_id"] == GP085_ANTI_IDLE01_GATE_ID_V1
    assert "passed" in body
    assert body["tenant_id"] == str(tenant_id)
