"""Phase 06 Step 34 — admin reasoning tenant verification slice + readiness economics."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.reasoning.reasoning_readiness_economics import (
    REASONING_READINESS_ECONOMICS_CONTRACT_V1,
)

pytestmark = pytest.mark.integration


def _tenant_with_owner(db_session: Session) -> uuid.UUID:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p634-{uuid.uuid4().hex[:10]}@example.com", full_name="P634 User")
    tenant = Tenant(
        company_name="P634 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p634-{uuid.uuid4().hex[:8]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    return tenant.id


def test_admin_cortex_reasoning_tenant_verification_slice_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/reasoning/tenant-verification-slice",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(tid)
    assert body["verification_run_id"] is None
    assert body["org_graph_reasoning_slice_schema_version"] >= 1
    assert isinstance(body["golden_corpus_case_count"], int)

    r2 = client.get(
        f"/admin/tenants/{tid}/cortex/reasoning/tenant-verification-slice?verification_run_id=vr-1",
        auth=("admin", "integration-admin-password"),
    )
    assert r2.status_code == 200
    assert r2.json()["verification_run_id"] == "vr-1"


def test_admin_cortex_reasoning_readiness_economics_ok_and_bad_profile(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    tid = _tenant_with_owner(db_session)
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tid}/cortex/reasoning/readiness-economics",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == str(tid)
    contract = REASONING_READINESS_ECONOMICS_CONTRACT_V1
    assert body["reasoning_readiness_economics_contract"] == contract
    assert body["economics_violations"] == []

    rh = client.get(
        f"/admin/tenants/{tid}/cortex/reasoning/readiness-economics?probe_profile=hostile",
        auth=("admin", "integration-admin-password"),
    )
    assert rh.status_code == 200
    assert rh.json()["economics_violations"] == ["REASONING_ECO_GOLDEN_CASE_BUDGET"]

    bad = client.get(
        f"/admin/tenants/{tid}/cortex/reasoning/readiness-economics?probe_profile=nope",
        auth=("admin", "integration-admin-password"),
    )
    assert bad.status_code == 400
