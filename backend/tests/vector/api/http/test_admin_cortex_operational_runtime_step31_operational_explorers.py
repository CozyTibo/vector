"""Admin HTTP — Phase 08.5 Step 31 dedicated explorers (**G-P085-CP-02**)."""

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

    user = User(
        email=f"p85ex-{uuid.uuid4().hex[:10]}@example.com",
        full_name="P085 EX",
    )
    tenant = Tenant(
        company_name="P085EX",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p85ex-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_catalog_explorers_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/explorers",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["primary_gate_id"] == "G-P085-CP-02"
    assert body["explorers_total"] == 10
    assert body["explorers_wired_count"] == 10


def test_admin_catalog_explorers_gate_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/explorers-gate",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["gate_id"] == "G-P085-CP-02"
    assert r.json()["passed"] is True


def test_admin_tenant_explorers_index_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["gate_id"] == "G-P085-CP-02"
    assert body["explorers_total"] == 10
    assert len(body["explorers"]) == 10


def test_admin_tenant_explorer_detail_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers/synthesis_eligibility",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["explorer_id"] == "synthesis_eligibility"
    assert body["surface_kind"] == "operational_explorer"
    assert "columns" in body


def test_admin_tenant_explorer_not_found(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/explorers/unknown_explorer",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 404
    assert r.json()["error"] == "explorer_not_found"
