"""Phase 07 Step 9 — admin retrieval addressing catalog HTTP surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.retrieval.retrieval_addressing import GP07_ADDR01_GATE_ID_V1

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7adr-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 ADR User")
    tenant = Tenant(
        company_name="P7ADR",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7adr-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_admin_cortex_retrieval_addressing_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/retrieval/addressing",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(tid)
    assert body["gate_id"] == GP07_ADDR01_GATE_ID_V1
    assert "resolution_order" in body
    assert "retrieval_addressing_resolve_failures_total" in body
