"""Admin HTTP — Phase 08.5 Step 23 retrieval completeness propagation."""

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
        email=f"p85retprop-{uuid.uuid4().hex[:10]}@example.com",
        full_name="P085 Ret Prop",
    )
    tenant = Tenant(
        company_name="P085RETPROP",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p85retprop-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db.add_all([user, tenant])
    db.flush()
    db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db.flush()
    return tenant.id


def test_admin_catalog_retrieval_completeness_propagation_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/retrieval-completeness-propagation",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["primary_gate_id"] == "G-P085-RET-PROP-01"
    assert body["propagation_entrypoint"] == "propagate_retrieval_completeness_stage_v1"


def test_admin_catalog_retrieval_completeness_propagation_gate_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    r = client.get(
        "/admin/catalog/cortex/operational-runtime/retrieval-completeness-propagation-gate",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    assert r.json()["passed"] is True


def test_admin_tenant_retrieval_completeness_propagation_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tenant_id = _tenant_with_owner(db_session)
    db_session.commit()
    r = client.get(
        f"/admin/tenants/{tenant_id}/cortex/operational-runtime/retrieval-completeness-propagation",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stage_id"] == "retrieval"
    assert body["total_objects"] == body["metrics"]["eligible_artifact_count"]
    assert "retrieval_completeness_propagation" in body["metrics"]
