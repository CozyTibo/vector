"""Phase 03 Step 17 — stabilization / economics proof pass."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_stabilization_proof import (
    STABILIZATION_PROOF_SCHEMA_VERSION,
    build_stabilization_proof_report,
    verify_phase03_step17_stabilization_proof_contract,
)
from vector.infrastructure.db.models.membership import TenantMembership
from vector.infrastructure.db.models.tenant import Tenant
from vector.infrastructure.db.models.user import User


def test_stabilization_proof_contract_rejects_empty() -> None:
    vr = verify_phase03_step17_stabilization_proof_contract(report={})
    assert vr["passed"] is False


def test_stabilization_proof_schema_version() -> None:
    assert STABILIZATION_PROOF_SCHEMA_VERSION >= 1


@pytest.mark.integration
def test_build_stabilization_proof_smoke(db_session: Session) -> None:
    user = User(email=f"p317-{uuid.uuid4().hex[:8]}@example.com", full_name="P317 User")
    tenant = Tenant(
        company_name="P317 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p317-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    report = build_stabilization_proof_report(db_session, tenant.id)
    vr = verify_phase03_step17_stabilization_proof_contract(report=report)
    assert vr["passed"] is True
    assert report["stabilization_proof_schema_version"] == STABILIZATION_PROOF_SCHEMA_VERSION
    assert "substrate_scale" in report
    assert "replay_economics" in report


@pytest.mark.integration
def test_persist_stabilization_proof_run(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    user = User(email=f"p317b-{uuid.uuid4().hex[:8]}@example.com", full_name="P317b User")
    tenant = Tenant(
        company_name="P317b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p317b-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    r = client.post(
        f"/admin/tenants/{tenant.id}/cortex/canonical/stabilization-proof/run",
        auth=("admin", "integration-admin-password"),
        json={"persist": True},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["persisted_run_id"] is not None

    listed = client.get(
        f"/admin/tenants/{tenant.id}/cortex/canonical/stabilization-proof/runs?limit=5",
        auth=("admin", "integration-admin-password"),
    )
    assert listed.status_code == 200
    lst = listed.json()
    assert lst["runs"]
    assert lst["runs"][0]["id"] == body["persisted_run_id"]
