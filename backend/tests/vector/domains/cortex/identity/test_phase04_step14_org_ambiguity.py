"""P04-14 — org ambiguity records, G-P04-AMB-01 / G-P04-12, admin HTTP."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from vector.domains.cortex.canonical.canonical_verification_engine import run_canonical_verification
from vector.domains.cortex.identity.org_ambiguity import (
    ORG_AMBIGUITY_SCHEMA_VERSION,
    OrgAmbiguityError,
    append_org_ambiguity_record,
    list_org_ambiguity_records,
    list_org_ambiguity_records_invalid_entity_refs,
    verify_gp04_amb01_org_ambiguity_integrity_static,
)
from vector.domains.cortex.identity.org_entities import upsert_org_entity


def test_gp04_amb01_static_passes() -> None:
    st = verify_gp04_amb01_org_ambiguity_integrity_static()
    assert st["passed"] is True


def test_append_requires_two_entities(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p414-{uuid.uuid4().hex[:8]}@example.com", full_name="P414")
    tenant = Tenant(
        company_name="P414 Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p414-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    a = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"a": 1},
        metadata_json={},
    )
    db_session.flush()
    with pytest.raises(OrgAmbiguityError, match="at least two"):
        append_org_ambiguity_record(
            db_session,
            tenant_id=tenant.id,
            org_ambiguity_class="multiple_persona_unresolved",
            subject_key="sk-1",
            involved_org_entity_ids=[a.id],
        )


def test_append_and_list(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p414b-{uuid.uuid4().hex[:8]}@example.com", full_name="P414b")
    tenant = Tenant(
        company_name="P414b Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p414b-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    a = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"a": 2},
        metadata_json={},
    )
    b = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"b": 2},
        metadata_json={},
    )
    db_session.flush()
    row = append_org_ambiguity_record(
        db_session,
        tenant_id=tenant.id,
        org_ambiguity_class="handle_collision_unresolved",
        subject_key="collision:demo:v1",
        involved_org_entity_ids=[a.id, b.id],
        evidence_json={"note": "test"},
    )
    db_session.commit()
    assert row.org_ambiguity_class == "handle_collision_unresolved"
    bad = list_org_ambiguity_records_invalid_entity_refs(db_session, tenant_id=tenant.id)
    assert bad == []


def test_append_open_merges_duplicate_subject_key(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p414m-{uuid.uuid4().hex[:8]}@example.com", full_name="P414m")
    tenant = Tenant(
        company_name="P414m Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p414m-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    a = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"a": 3},
        metadata_json={},
    )
    b = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"b": 3},
        metadata_json={},
    )
    c = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="human_actor",
        identity_material={"c": 3},
        metadata_json={},
    )
    db_session.flush()
    sk = "fixture_cohort:merge:test:v1"
    r1 = append_org_ambiguity_record(
        db_session,
        tenant_id=tenant.id,
        org_ambiguity_class="handle_collision_unresolved",
        subject_key=sk,
        involved_org_entity_ids=[a.id, b.id],
        evidence_json={"wave": 1},
    )
    r2 = append_org_ambiguity_record(
        db_session,
        tenant_id=tenant.id,
        org_ambiguity_class="handle_collision_unresolved",
        subject_key=sk,
        involved_org_entity_ids=[b.id, c.id],
        evidence_json={"wave": 2},
    )
    db_session.commit()
    assert r1.id == r2.id
    open_rows = list_org_ambiguity_records(db_session, tenant_id=tenant.id, limit=20, status="open")
    assert len([x for x in open_rows if x.subject_key == sk]) == 1
    merged = append_org_ambiguity_record(
        db_session,
        tenant_id=tenant.id,
        org_ambiguity_class="handle_collision_unresolved",
        subject_key=sk,
        involved_org_entity_ids=[a.id, b.id, c.id],
        evidence_json={},
    )
    db_session.refresh(merged)
    assert set(uuid.UUID(x) for x in merged.involved_org_entity_ids) == {a.id, b.id, c.id}
    assert merged.evidence_json.get("wave") == 2


@pytest.mark.integration
def test_admin_org_ambiguities_http(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
    db_session: Session,
) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "integration-admin-password")
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p414h-{uuid.uuid4().hex[:8]}@example.com", full_name="P414h")
    tenant = Tenant(
        company_name="P414h Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p414h-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.flush()
    e1 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="team",
        identity_material={"t": 1},
        metadata_json={},
    )
    e2 = upsert_org_entity(
        db_session,
        tenant_id=tenant.id,
        entity_kind="team",
        identity_material={"t": 2},
        metadata_json={},
    )
    db_session.commit()

    post = client.post(
        f"/admin/tenants/{tenant.id}/cortex/identity/org-ambiguities",
        auth=("admin", "integration-admin-password"),
        json={
            "org_ambiguity_class": "cross_bundle_persona_gap",
            "subject_key": "gap:admin:test",
            "involved_org_entity_ids": [str(e1.id), str(e2.id)],
            "status": "open",
            "evidence_json": {},
        },
    )
    assert post.status_code == 200
    body = post.json()
    assert body["org_ambiguity_schema_version"] == ORG_AMBIGUITY_SCHEMA_VERSION
    rid = uuid.UUID(body["record"]["id"])

    lst = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/org-ambiguities",
        auth=("admin", "integration-admin-password"),
    )
    assert lst.status_code == 200
    assert any(uuid.UUID(x["id"]) == rid for x in lst.json()["records"])

    det = client.get(
        f"/admin/tenants/{tenant.id}/cortex/identity/org-ambiguities/{rid}",
        auth=("admin", "integration-admin-password"),
    )
    assert det.status_code == 200
    assert det.json()["record"]["subject_key"] == "gap:admin:test"


def test_verification_includes_org_ambiguity_gates(db_session: Session) -> None:
    from vector.infrastructure.db.models.membership import TenantMembership
    from vector.infrastructure.db.models.tenant import Tenant
    from vector.infrastructure.db.models.user import User

    user = User(email=f"p414v-{uuid.uuid4().hex[:8]}@example.com", full_name="P414v")
    tenant = Tenant(
        company_name="P414v Co",
        primary_email=user.email,
        email_domain="example.com",
        slug=f"p414v-{uuid.uuid4().hex[:10]}",
        status="active",
        workspace_access_enabled=True,
    )
    db_session.add_all([user, tenant])
    db_session.flush()
    db_session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="owner"))
    db_session.commit()
    out = run_canonical_verification(db_session, tenant_id=tenant.id, persist=False)
    ids = {g["id"] for g in out["gates"]}
    assert "G-P04-AMB-01" in ids
    assert "G-P04-12" in ids
    g12 = next(g for g in out["gates"] if g["id"] == "G-P04-12")
    assert g12["severity"] == "warn_only"
    assert g12["passed"] is True
