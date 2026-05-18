"""Phase 08 Step 07 — admin synthesis legality matrix HTTP surface."""

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

    user = User(email=f"p8admleg-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Admin Leg")
    tenant = Tenant(
        company_name="P8ADMLEG",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8admleg-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_get_synthesis_legality_matrix_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/legality-matrix",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "doctrine_catalog"
    assert body["gp08_legality_gate_id"] == "G-P08-LEG-01"
    assert len(body["predicates"]) == 7
    assert "synthesis_replay_safe" in body["synthesis_jobs_by_legality"]
