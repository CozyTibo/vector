"""Admin HTTP — Phase 08.5 Step 35 Phase 09 readiness (**G-P085-READY-01**)."""

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
        email=f"p85p9-{uuid.uuid4().hex[:10]}@example.com",
        full_name="P085 P9",
    )
    tenant = Tenant(
        company_name="P085P9",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p85p9-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_catalog_phase09_readiness_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/phase09-readiness",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["primary_gate_id"] == "G-P085-READY-01"


def test_admin_catalog_phase09_readiness_gate_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/phase09-readiness-gate",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["passed"] is True


def test_admin_soak_signoff_and_checklist(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r_sign = client.post(
        "/admin/catalog/cortex/operational-runtime/phase09-readiness/soak-signoff",
        auth=("admin", "integration-admin-password"),
    )
    assert r_sign.status_code == 200
    assert r_sign.json()["signoff_kind"] == "soak_7d_ops"
    r_chk = client.get(
        "/admin/catalog/cortex/operational-runtime/phase09-readiness/checklist",
        auth=("admin", "integration-admin-password"),
    )
    assert r_chk.status_code == 200
    assert r_chk.json()["readiness_passed"] is True


def test_admin_tenant_golden_profile(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/phase09-readiness/golden-profile",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["gate_id"] == "G-P085-READY-01"
