"""Admin HTTP — Phase 08.5 Step 12 graph orphan continuity."""

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

    user = User(email=f"p85orphan-{uuid.uuid4().hex[:10]}@example.com", full_name="P085 Orphan")
    tenant = Tenant(
        company_name="P085ORPHAN",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p85orphan-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_catalog_graph_orphan_continuity_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/graph-orphan-continuity",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["primary_gate_id"] == "G-P085-ORPHAN-01"
    assert "orphan_awaiting_promotion" in body["orphan_class_ids"]


def test_admin_catalog_graph_orphan_continuity_gate_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/graph-orphan-continuity-gate",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["passed"] is True


def test_admin_tenant_graph_orphan_continuity_and_stitch_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/graph-orphan-continuity",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["gate_id"] == "G-P085-ORPHAN-01"

    r2 = client.post(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/graph-orphan-continuity/stitch",
        params={"dry_run": "true"},
        auth=("admin", "integration-admin-password"),
    )
    assert r2.status_code == 200
    assert r2.json()["dry_run"] is True
