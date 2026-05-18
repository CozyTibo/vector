"""Phase 08 Step 22 — admin synthesis control plane HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.synthesis_control_plane import GP08_CP01_GATE_ID_V1

pytestmark = pytest.mark.integration


def _tenant_with_owner(db: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8admcp22-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Adm CP22")
    tenant = Tenant(
        company_name="P8ADMCP22",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8admcp22-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_synthesis_control_plane_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/control-plane",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(tenant_id)
    assert body["gate_id"] == GP08_CP01_GATE_ID_V1
    assert body["surfaces_total"] == 16
    assert len(body["surface_checklist"]) == 16
    assert body["synthesis_control_plane_contract"] == "synthesis_control_plane_v1"
    assert "degradation_posture_summary" in body
    assert "coverage_summary" in body


def test_admin_synthesis_control_plane_tenant_not_found(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        f"/admin/tenants/{uuid.uuid4()}/cortex/synthesis/control-plane",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 404
