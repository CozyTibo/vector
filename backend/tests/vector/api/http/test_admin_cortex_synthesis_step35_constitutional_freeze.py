"""Phase 08 Step 35 — admin constitutional freeze HTTP."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.synthesis_constitutional_freeze import (
    GP08_FREEZE01_GATE_ID_V1,
    P08_FINAL_FREEZE_BUNDLE_ID_V1,
)

pytestmark = pytest.mark.integration


def _tenant(db: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8adm35-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Adm 35")
    tenant = Tenant(
        company_name="P8ADM35",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8adm35-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_constitutional_freeze_catalog(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/constitutional-freeze",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["gate_id"] == GP08_FREEZE01_GATE_ID_V1
    assert body["constitutional_freeze_bundle"] == P08_FINAL_FREEZE_BUNDLE_ID_V1
    assert body["signoff_passed"] is True
    assert body["freeze_banner"]["status"] == "Frozen (implementation)"


def test_admin_program_catalog_has_freeze_banner(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/synthesis/program",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["freeze_banner"]["bundle_id"] == P08_FINAL_FREEZE_BUNDLE_ID_V1


def test_admin_tenant_constitutional_freeze_signoff(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant(db_session)
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/constitutional-freeze/signoff",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["constitutional_freeze_passed"] is True
