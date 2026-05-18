"""Phase 08 Step 18 — admin synthesis degradation topology HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.synthesis_degradation import GP08_DEG02_GATE_ID_V1

pytestmark = pytest.mark.integration


def _tenant_with_owner(db: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8admdeg18-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Adm Deg18")
    tenant = Tenant(
        company_name="P8ADMDEG18",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8admdeg18-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_catalog_degradation_topology_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/degradation-topology",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["surface_kind"] == "synthesis_degradation_topology"
    assert GP08_DEG02_GATE_ID_V1 in body["gate_ids"]
    assert any(row["rd_code"] == "RD-REPLAY-TWIN" for row in body["rd_to_sd_propagation_matrix"])


def test_admin_tenant_degradation_topology_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/degradation-topology",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["tenant_id"] == str(tenant_id)
