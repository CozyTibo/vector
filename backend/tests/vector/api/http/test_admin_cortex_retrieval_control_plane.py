"""Phase 07 Step 23 — admin retrieval control plane HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.retrieval.retrieval_control_plane import GP07_CP01_GATE_ID_V1

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7cpadm-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 CP Admin")
    tenant = Tenant(
        company_name="P7CPADM",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7cpadm-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_admin_retrieval_control_plane_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/retrieval/control-plane",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(tid)
    assert body["gate_id"] == GP07_CP01_GATE_ID_V1
    assert body["surfaces_total"] == 16
    assert len(body["surface_checklist"]) == 16


def test_admin_retrieval_audit_trail_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/retrieval/audit",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(tid)
    assert "audit_rows" in body
