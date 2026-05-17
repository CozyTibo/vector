"""Phase 07 Step 25 — admin retrieval tenant slice + readiness economics HTTP."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.retrieval.retrieval_readiness_economics import (
    RETRIEVAL_READINESS_ECONOMICS_CONTRACT_V1,
)
from vector.domains.cortex.retrieval.retrieval_tenant_verification_slice import (
    ORG_GRAPH_RETRIEVAL_VERIFICATION_SLICE_SCHEMA_VERSION,
)

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p7tveradm-{uuid.uuid4().hex[:10]}@example.com", full_name="P7 TVER Admin")
    tenant = Tenant(
        company_name="P7TVERADM",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p7tveradm-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_admin_retrieval_readiness_economics_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/retrieval/readiness-economics",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(tid)
    assert body["retrieval_readiness_economics_contract"] == RETRIEVAL_READINESS_ECONOMICS_CONTRACT_V1
    assert body["economics_violations"] == []

    hostile = client.get(
        f"/admin/tenants/{tid}/cortex/retrieval/readiness-economics?profile=hostile",
        auth=("admin", "integration-admin-password"),
    )
    assert hostile.status_code == 200
    assert hostile.json()["economics_violations"] == ["RETRIEVAL_ECO_GOLDEN_CASE_BUDGET"]


def test_admin_retrieval_tenant_verification_slice_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/retrieval/tenant-verification-slice",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert "retrieval_slice_hash" in body
    assert len(body["retrieval_slice_hash"]) == 64
    sl = body["slice"]
    assert sl["tenant_id"] == str(tid)
    assert sl["org_graph_retrieval_slice_schema_version"] == (
        ORG_GRAPH_RETRIEVAL_VERIFICATION_SLICE_SCHEMA_VERSION
    )
