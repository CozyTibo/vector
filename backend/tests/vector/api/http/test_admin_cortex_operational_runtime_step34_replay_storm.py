"""Admin HTTP — Phase 08.5 Step 34 replay storm (**G-P085-ECON-02**)."""

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
        email=f"p85rs-{uuid.uuid4().hex[:10]}@example.com",
        full_name="P085 RS",
    )
    tenant = Tenant(
        company_name="P085RS",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p85rs-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_catalog_replay_storm_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/replay-storm",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["primary_gate_id"] == "G-P085-ECON-02"


def test_admin_catalog_replay_storm_gate_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/replay-storm-gate",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["gate_id"] == "G-P085-ECON-02"
    assert r.json()["passed"] is True


def test_admin_tenant_replay_storm_card_and_ack(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r_card = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/replay-storm",
        auth=("admin", "integration-admin-password"),
    )
    assert r_card.status_code == 200
    assert r_card.json()["gate_id"] == "G-P085-ECON-02"

    r_ack = client.post(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/replay-storm/acknowledge",
        auth=("admin", "integration-admin-password"),
    )
    assert r_ack.status_code == 200
    assert r_ack.json()["operator_acknowledged_at"] is not None
