"""Phase 08 Step 25 — admin synthesis runtime legality matrix HTTP surface."""

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

    user = User(email=f"p8admrlm-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Admin RLM")
    tenant = Tenant(
        company_name="P8ADMRLM",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8admrlm-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_get_synthesis_runtime_legality_matrix_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/runtime-legality-matrix",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert body["gate_id"] == "G-P08-RLM-01"
    assert len(body["predicates"]) == 7
    assert len(body["forbidden_deployments"]) == 5
    assert "production_milestones" in body
    assert body["prod_syn01"]["matrix_row_id"] == "PROD-SYN-01"
    assert body["prod_syn01"]["passed"] is True


def test_admin_get_synthesis_runtime_legality_matrix_tenant_not_found(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = uuid.uuid4()
    r = client.get(
        f"/admin/tenants/{tid}/cortex/synthesis/runtime-legality-matrix",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 404
