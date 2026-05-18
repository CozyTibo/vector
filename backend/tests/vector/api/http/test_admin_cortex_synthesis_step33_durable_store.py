"""Phase 08 Step 33 — admin synthesis durable store HTTP."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.synthesis_repository import GP08_STORE01_GATE_ID_V1

pytestmark = pytest.mark.integration


def _tenant_with_owner(db: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8adm33-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Adm 33")
    tenant = Tenant(
        company_name="P8ADM33",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8adm33-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_durable_store_catalog(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/durable-store",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["gate_id"] == GP08_STORE01_GATE_ID_V1


def test_admin_retention_dry_run_and_smoke(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.post(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/retention/apply",
        json={"dry_run": True},
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["dry_run"] is True

    r2 = client.post(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/durable-store/smoke",
        json={"iterations": 3},
        auth=("admin", "integration-admin-password"),
    )
    assert r2.status_code == 200
    assert r2.json().get("passed") is True
