"""Admin HTTP — Phase 08.5 Step 30 operational cockpit (**G-P085-CP-01**)."""

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
        email=f"p85cp-{uuid.uuid4().hex[:10]}@example.com",
        full_name="P085 CP",
    )
    tenant = Tenant(
        company_name="P085CP",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p85cp-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_catalog_cockpit_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/cockpit",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["primary_gate_id"] == "G-P085-CP-01"
    assert body["surfaces_total"] == 19
    assert int(body["surfaces_wired_count"]) >= 12


def test_admin_catalog_cockpit_gate_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/cockpit-gate",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["gate_id"] == "G-P085-CP-01"
    assert r.json()["passed"] is True


def test_admin_tenant_cockpit_aggregate_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["gate_id"] == "G-P085-CP-01"
    assert body["surfaces_wired_count"] == 19
    assert "command_center" in body
    assert "timeline" in body


def test_admin_tenant_cockpit_command_center_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit/command-center",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "operational_command_center"
    assert "overview_badges" in body
    assert "next_required_step" in body


def test_admin_tenant_cockpit_timeline_and_heatmap_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r_tl = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit/timeline",
        auth=("admin", "integration-admin-password"),
    )
    assert r_tl.status_code == 200
    assert r_tl.json()["surface_kind"] == "pipeline_progression_timeline"

    r_hm = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit/heatmap",
        auth=("admin", "integration-admin-password"),
    )
    assert r_hm.status_code == 200
    assert r_hm.json()["surface_kind"] == "substrate_heatmap"

    r_dt = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/cockpit/density-trends",
        auth=("admin", "integration-admin-password"),
    )
    assert r_dt.status_code == 200
    assert r_dt.json()["surface_kind"] == "density_trend_charts"
