"""P04-15 — org identity verification slice, G-P04-VER-01, admin HTTP."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.identity.org_verification_metadata import ORG_IDENTITY_VERIFICATION_ENGINE_SCHEMA_VERSION
from vector.domains.cortex.identity.verification import (
    PHASE04_NORMATIVE_NUMBERED_GATE_IDS,
    phase04_identity_gate_slice,
    run_org_identity_verification,
    verify_gp04_ver01_phase04_catalog_coherence_static,
)


def test_phase04_normative_numbered_registry() -> None:
    assert len(PHASE04_NORMATIVE_NUMBERED_GATE_IDS) == 26
    assert len(set(PHASE04_NORMATIVE_NUMBERED_GATE_IDS)) == 26
    assert PHASE04_NORMATIVE_NUMBERED_GATE_IDS[0] == "G-P04-01"
    assert PHASE04_NORMATIVE_NUMBERED_GATE_IDS[-1] == "G-P04-26"


def test_gp04_ver01_static_passes() -> None:
    st = verify_gp04_ver01_phase04_catalog_coherence_static()
    assert st["id"] == "G-P04-VER-01"
    assert st["passed"] is True


def test_org_slice_is_phase04_prefix_only(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p415-{uuid.uuid4().hex[:8]}@example.com", full_name="P415")
    tenant = Tenant(
        company_name="P415 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p415-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    full = run_canonical_verification(db_session, tenant_id=tenant.id, materialization_sample_limit=5, persist=False)
    p04 = phase04_identity_gate_slice(list(full["gates"]))
    assert len(p04) < len(full["gates"])
    assert all(str(g.get("id") or "").startswith("G-P04") for g in p04)
    org = run_org_identity_verification(db_session, tenant_id=tenant.id, materialization_sample_limit=5, persist=False)
    assert len(org["gates"]) == len(p04)
    assert org["org_identity_verification_engine_schema_version"] == ORG_IDENTITY_VERIFICATION_ENGINE_SCHEMA_VERSION


@pytest.mark.integration
def test_admin_org_identity_verification_persist(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p415a-{uuid.uuid4().hex[:8]}@example.com", full_name="P415a")
    tenant = Tenant(
        company_name="P415a Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p415a-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    r = client.post(
        f"/admin/tenants/{tenant.id}/cortex/identity/verification/run",
        auth=("admin", "integration-admin-password"),
        json={"persist": True, "materialization_sample_limit": 10},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["org_identity_verification_engine_schema_version"] == ORG_IDENTITY_VERIFICATION_ENGINE_SCHEMA_VERSION
    assert body["persisted_run_id"] is not None
    gids = {g["id"] for g in body["gates"]}
    assert "G-P04-VER-01" in gids
    assert "G-P03-01" not in gids

    listed = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/verification/runs?limit=5",
        auth=("admin", "integration-admin-password"),
    )
    assert listed.status_code == 200
    lst = listed.json()
    assert lst["runs"]
    assert lst["runs"][0]["id"] == body["persisted_run_id"]
