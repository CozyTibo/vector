"""Admin HTTP — Phase 08.5 Step 27 operational maturity (**G-P085-MAT-01**)."""

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
        email=f"p85mat-{uuid.uuid4().hex[:10]}@example.com",
        full_name="P085 MAT",
    )
    tenant = Tenant(
        company_name="P085MAT",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p85mat-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_catalog_operational_maturity_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/operational-maturity",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["primary_gate_id"] == "G-P085-MAT-01"
    assert body["evaluation_entrypoint"] == "evaluate_multidimensional_operational_maturity_v1"


def test_admin_catalog_operational_maturity_gate_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/operational-maturity-gate",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["gate_id"] == "G-P085-MAT-01"
    assert r.json()["passed"] is True


def test_admin_tenant_operational_maturity_card_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/operational-maturity",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["gate_id"] == "G-P085-MAT-01"
    assert body["surface_kind"] == "operational_maturity_card"
    assert "operational_confidence_score" in body


def test_admin_tenant_operational_maturity_evaluate_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/operational-maturity/evaluate",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["gate_id"] == "G-P085-MAT-01"
    assert "dimension_scores" in body
    assert "maturity_class" in body
