"""P04-21 — identity readiness economics probes + G-P04-ECO-01 + admin HTTP."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.identity.readiness_economics import (
    IDENTITY_READINESS_ECONOMICS_CONTRACT,
    build_identity_readiness_economics,
    verify_gp04_eco01_identity_readiness_economics,
)


def test_readiness_economics_empty_tenant(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p421-{uuid.uuid4().hex[:8]}@example.com", full_name="P421")
    tenant = Tenant(
        company_name="P421 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p421-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    eco = build_identity_readiness_economics(db_session, tenant_id=tenant.id)
    assert eco["schema_version"] == IDENTITY_READINESS_ECONOMICS_CONTRACT
    assert eco["overall_posture"] == "ok"
    assert eco["warnings"] == []
    assert eco["counts"]["org_entities_active"] == 0
    assert eco["storage_estimate_bytes"] == 0

    g = verify_gp04_eco01_identity_readiness_economics(db_session, tenant_id=tenant.id)
    assert g["id"] == "G-P04-ECO-01"
    assert g["severity"] == "warn_only"
    assert g["passed"] is True


def test_canonical_verification_includes_gp04_eco01(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p421b-{uuid.uuid4().hex[:8]}@example.com", full_name="P421b")
    tenant = Tenant(
        company_name="P421b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p421b-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    full = run_canonical_verification(db_session, tenant_id=tenant.id, materialization_sample_limit=3, persist=False)
    gate = next(x for x in full["gates"] if x["id"] == "G-P04-ECO-01")
    assert gate["severity"] == "warn_only"
    assert gate["passed"] is True


@pytest.mark.integration
def test_admin_identity_readiness_economics_ok(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p421c-{uuid.uuid4().hex[:8]}@example.com", full_name="P421c")
    tenant = Tenant(
        company_name="P421c Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p421c-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    r = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/readiness-economics",
        auth=("admin", "integration-admin-password"),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["schema_version"] == IDENTITY_READINESS_ECONOMICS_CONTRACT
    assert body["tenant_id"] == str(tenant.id)
    assert body["overall_posture"] == "ok"
    assert body["counts"]["org_entities_active"] == 0
