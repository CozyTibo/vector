"""P04-03 — org entity (org handle) registry: determinism, DB upsert, admin read surface."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.identity.org_entities import (
    ORG_ENTITY_RUNTIME_SCHEMA_VERSION,
    deterministic_org_entity_id,
    identity_key_fingerprint,
    upsert_org_entity,
    verify_org_entity_determinism_static,
)


def test_verify_org_entity_determinism_static_passes() -> None:
    gate = verify_org_entity_determinism_static()
    assert gate["id"] == "G-P04-ORG-01"
    assert gate["passed"] is True


def test_identity_key_fingerprint_stable_key_order() -> None:
    a = identity_key_fingerprint({"z": 1, "a": 2})
    b = identity_key_fingerprint({"a": 2, "z": 1})
    assert a == b


def test_deterministic_org_entity_id_stable() -> None:
    tid = uuid.uuid4()
    fp = identity_key_fingerprint({"k": "v"})
    x = deterministic_org_entity_id(tenant_id=tid, entity_kind="team", fingerprint=fp)
    y = deterministic_org_entity_id(tenant_id=tid, entity_kind="team", fingerprint=fp)
    assert x == y
    z = deterministic_org_entity_id(
        tenant_id=tid,
        entity_kind="team",
        fingerprint=identity_key_fingerprint({"k": "w"}),
    )
    assert x != z


@pytest.mark.integration
def test_upsert_list_get_round_trip(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p403-{uuid.uuid4().hex[:8]}@example.com", full_name="P403")
    tenant = Tenant(
        company_name="P403 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p403-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()

    material = {"external_ref": "acct-1", "provider": "slack"}
    row = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material=material,
        metadata_json={"display": "Ada"},
    )
    db_session.commit()
    assert row.tenant_id == tenant.id
    assert row.entity_kind == "human_actor"
    assert row.identity_key_fingerprint == identity_key_fingerprint(material)
    assert row.id == deterministic_org_entity_id(
        tenant_id=tenant.id,
        entity_kind="human_actor",
        fingerprint=row.identity_key_fingerprint,
    )

    row2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material=material,
        metadata_json={"display": "Ada II"},
    )
    db_session.commit()
    assert row2.id == row.id
    assert row2.metadata_json["display"] == "Ada II"

    from vector.domains.cortex.identity.org_entities import get_org_entity, list_org_entities

    listed = list_org_entities(db_session, tenant_id=tenant.id, limit=10)
    assert any(r.id == row.id for r in listed)
    got = get_org_entity(db_session, tenant_id=tenant.id, org_entity_id=row.id)
    assert got is not None
    assert got.lifecycle_state == "active"


@pytest.mark.integration
def test_admin_org_entities_list_and_detail(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p403a-{uuid.uuid4().hex[:8]}@example.com", full_name="P403a")
    tenant = Tenant(
        company_name="P403a Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p403a-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    row = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="workspace",
        identity_material={"slug": "ws-1"},
        metadata_json={},
    )
    db_session.commit()
    eid = row.id

    lst = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/entities",
        auth=("admin", "integration-admin-password"),
    )
    assert lst.status_code == 200
    body = lst.json()
    assert body["org_entity_runtime_schema_version"] == ORG_ENTITY_RUNTIME_SCHEMA_VERSION
    assert body["tenant_id"] == str(tenant.id)
    assert any(x["id"] == str(eid) for x in body["entities"])

    det = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/entities/{eid}",
        auth=("admin", "integration-admin-password"),
    )
    assert det.status_code == 200
    one = det.json()
    assert one["id"] == str(eid)
    assert one["entity_kind"] == "workspace"

    missing = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/entities/{uuid.uuid4()}",
        auth=("admin", "integration-admin-password"),
    )
    assert missing.status_code == 404


@pytest.mark.integration
def test_canonical_verification_includes_gp04_org01_gate(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p403b-{uuid.uuid4().hex[:8]}@example.com", full_name="P403b")
    tenant = Tenant(
        company_name="P403b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p403b-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()

    out = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    ids = [g["id"] for g in out["gates"]]
    assert "G-P04-ORG-01" in ids
    gate = next(g for g in out["gates"] if g["id"] == "G-P04-ORG-01")
    assert gate["passed"] is True
