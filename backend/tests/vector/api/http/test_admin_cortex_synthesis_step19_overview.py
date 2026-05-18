"""Phase 08 Step 19 — admin synthesis overview + coverage HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.synthesis.synthesis_completeness_projection import GP08_COMP01_GATE_ID_V1

pytestmark = pytest.mark.integration


def _tenant_with_owner(db: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p8admcomp19-{uuid.uuid4().hex[:10]}@example.com", full_name="P8 Adm Comp19")
    tenant = Tenant(
        company_name="P8ADMCOMP19",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p8admcomp19-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_tenant_synthesis_overview_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/overview",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stage_id"] == "synthesis"
    assert body["surface_kind"] == "runtime_backed"
    assert body["synthesis_completeness_runtime_schema_version"] >= 1
    assert "coverage_percent" in body
    assert body["stage_envelope"]["stage_id"] == "synthesis"


def test_admin_tenant_synthesis_coverage_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/synthesis/coverage",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stage_id"] == "synthesis"
    assert "eligible_scopes" in body
    assert "synthesized_scopes" in body
    assert GP08_COMP01_GATE_ID_V1.startswith("G-P08-COMP")
