"""P04-22 — org identity certification pack + archive + G-P04-CLOSE-01 + admin HTTP."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.identity.org_identity_certification_pack import (
    ORG_IDENTITY_CERTIFICATION_PACK_SCHEMA_VERSION,
    build_org_identity_certification_pack,
    overall_org_identity_closure_passed,
    verify_phase04_org_identity_certification_pack_contract,
)


def test_org_certification_pack_contract_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p422-{uuid.uuid4().hex[:8]}@example.com", full_name="P422")
    tenant = Tenant(
        company_name="P422 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p422-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    pack = build_org_identity_certification_pack(db_session, tenant_id=tenant.id, materialization_sample_limit=3)
    assert pack["org_certification_pack_schema_version"] == ORG_IDENTITY_CERTIFICATION_PACK_SCHEMA_VERSION
    cr = verify_phase04_org_identity_certification_pack_contract(pack=pack)
    assert cr["passed"] is True
    assert overall_org_identity_closure_passed(pack) is True
    ids = {r["id"] for r in pack["closure_gate_matrix"]}
    assert ids == {"G-P04-CLOSE-MAP-01", "G-P04-CLOSE-MAP-02", "G-P04-CLOSE-01"}

    full = run_canonical_verification(db_session, tenant_id=tenant.id, materialization_sample_limit=3, persist=False)
    close = next(g for g in full["gates"] if g["id"] == "G-P04-CLOSE-01")
    assert close["severity"] == "hard_fail"
    assert close["passed"] is True


@pytest.mark.integration
def test_admin_org_identity_certification_pack_routes(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p422b-{uuid.uuid4().hex[:8]}@example.com", full_name="P422b")
    tenant = Tenant(
        company_name="P422b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p422b-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    snap = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/certification-pack",
        auth=("admin", "integration-admin-password"),
    )
    assert snap.status_code == 200
    body = snap.json()
    assert body["org_certification_pack_schema_version"] == ORG_IDENTITY_CERTIFICATION_PACK_SCHEMA_VERSION
    assert body["org_identity_certification_pack_contract"]["passed"] is True

    arch = client.post(
        f"/admin/tenants/{tenant.id}/cortex/identity/certification-pack/archive",
        auth=("admin", "integration-admin-password"),
        json={"materialization_sample_limit": 5},
    )
    assert arch.status_code == 200
    ar = arch.json()
    assert ar["passed"] is True
    assert ar["persisted"] is True
    assert ar["archive_id"] is not None

    lst = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/certification-pack/archives?limit=5",
        auth=("admin", "integration-admin-password"),
    )
    assert lst.status_code == 200
    rows = lst.json()["archives"]
    assert rows
    aid = rows[0]["id"]

    det = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/certification-pack/archives/{aid}",
        auth=("admin", "integration-admin-password"),
    )
    assert det.status_code == 200
    assert det.json()["pack"]["tenant_id"] == str(tenant.id)
