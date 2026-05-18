"""Phase 08 Step 24 — admin synthesis tenant verification + economics HTTP."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.synthesis_tenant_verification import GP08_TVER01_GATE_ID_V1

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8adm24-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Adm24")
    tenant = Tenant(
        company_name="P8ADM24",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8adm24-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_admin_synthesis_tenant_verification_and_economics_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()
    auth = ("admin", "integration-admin-password")
    base = f"/admin/tenants/{tid}/cortex/synthesis"

    slice_r = client.get(f"{base}/tenant-verification-slice", auth=auth)
    assert slice_r.status_code == 200
    assert "synthesis_slice_hash" in slice_r.json()

    verify_r = client.get(f"{base}/tenant-verification", auth=auth)
    assert verify_r.status_code == 200
    body = verify_r.json()
    assert body["gate_id"] == GP08_TVER01_GATE_ID_V1
    assert "synthesis_substrate" in body

    eco_r = client.get(f"{base}/readiness-economics", auth=auth)
    assert eco_r.status_code == 200
    eco = eco_r.json()
    assert eco["synthesis_readiness_economics_contract"] == "synthesis_readiness_economics_v1"
    assert eco["economics_violations"] == []

    hostile = client.get(f"{base}/readiness-economics?profile=hostile", auth=auth)
    assert hostile.status_code == 200
    assert hostile.json()["economics_violations"] == ["SYNTHESIS_ECO_GOLDEN_CASE_BUDGET"]
