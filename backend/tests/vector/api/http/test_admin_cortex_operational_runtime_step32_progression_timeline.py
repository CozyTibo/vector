"""Admin HTTP — Phase 08.5 Step 32 progression timeline + causal chains (**G-P085-CP-03**)."""

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
        email=f"p85tl-{uuid.uuid4().hex[:10]}@example.com",
        full_name="P085 TL",
    )
    tenant = Tenant(
        company_name="P085TL",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p85tl-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_catalog_progression_timeline_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/progression-timeline",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["primary_gate_id"] == "G-P085-CP-03"


def test_admin_catalog_progression_timeline_gate_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/progression-timeline-gate",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["gate_id"] == "G-P085-CP-03"
    assert r.json()["passed"] is True


def test_admin_tenant_progression_timeline_and_causal_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r_tl = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/progression-timeline",
        auth=("admin", "integration-admin-password"),
    )
    assert r_tl.status_code == 200
    body_tl = r_tl.json()
    assert body_tl["gate_id"] == "G-P085-CP-03"
    assert "ascii_timeline_line" in body_tl

    r_cc = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/causal-failure-chain",
        auth=("admin", "integration-admin-password"),
    )
    assert r_cc.status_code == 200
    assert r_cc.json()["surface_kind"] == "causal_failure_chain"


def test_admin_tenant_overview_integration_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/overview-integration",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["gate_id"] == "G-P085-CP-03"
    assert "overview_badges" in body
    assert len(body["stage_cards"]) == 5
    assert body["anti_fake_green_passed"] is True
