"""Phase 08 Step 28 — admin synthesis evaluation HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


def _tenant_with_owner(db: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8admeval-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Admin Eval")
    tenant = Tenant(
        company_name="P8ADMEVAL",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8admeval-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_catalog_synthesis_evaluation(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/evaluation",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "verification_probe"
    assert "G-P08-EVAL-01" in body["gate_ids"]
    assert body["static_gate_samples"]["G-P08-EVAL-01"]["passed"] is True


def test_admin_tenant_synthesis_evaluation(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/evaluation",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["evaluation_passed"] is True
    assert body["surface_kind"] == "verification_probe"
    assert body["tenant"]["tenant_id"] == str(tenant_id)


def test_admin_tenant_synthesis_evaluation_tenant_not_found(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        f"/admin/tenants/{uuid.uuid4()}/cortex/synthesis/evaluation",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 404
