"""Phase 08 Step 21 — admin synthesis health + observability HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.synthesis_observability import GP08_OBS01_GATE_ID_V1

pytestmark = pytest.mark.integration


def _tenant_with_owner(db: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8admobs21-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Adm Obs21")
    tenant = Tenant(
        company_name="P8ADMOBS21",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8admobs21-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_catalog_observability_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/observability",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["gate_id"] == GP08_OBS01_GATE_ID_V1
    assert "synthesis_job_duration_ms_p50" in body["metric_names"]


def test_admin_tenant_health_and_observability_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/health",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    health = r.json()
    assert health["tenant_id"] == str(tenant_id)
    assert "active_alerts" in health
    assert "metrics" in health

    r2 = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/observability",
        auth=("admin", "integration-admin-password"),
    )
    assert r2.status_code == 200
    obs = r2.json()
    assert obs["tenant_id"] == str(tenant_id)
    assert "health_strip" in obs

    r3 = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/overview",
        auth=("admin", "integration-admin-password"),
    )
    assert r3.status_code == 200
    assert "health_strip" in r3.json()
